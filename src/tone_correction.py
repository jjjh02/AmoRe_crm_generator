#!/usr/bin/env python3
"""
Exaone 기반 CRM 톤 보정기

입력: Qwen이 생성한 마케팅 초안, 페르소나, 브랜드명, 발신목적(스테이지)
처리: CRM 분석 결과(RAG), FOMO 템플릿, 브랜드 스토리, CRM 목적 정의를 컨텍스트로 붙여
      Exaone 로컬 모델로 톤을 정제합니다.

예시:
  python3 src/tone_correction.py \\
    --draft_path outputs/qwen_draft.txt \\
    --persona 0 \\
    --brand 설화수 \\
    --stage_index 1 \\
    --out_path outputs/tone_corrected.json
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from functools import lru_cache
from typing import Dict, List, Any

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

# 내부 유틸
sys.path.insert(0, os.path.dirname(__file__))
from rag_utils import vectorize_texts, cosine  # noqa: E402


STAGE_ORDER = ['Acquisition', 'Activation', 'Retention', 'Revenue', 'Referral']
FOMO_STAGE_KEYS = {
    0: '1_Acquisition_초기진입_압박',
    1: '2_Activation_행동유도_압박',
    2: '3_Retention_이탈방지_압박',
    3: '4_Revenue_전환확정_압박',
    4: '5_Referral_공유확산_압박',
}

PERSONA_NAMES = [
    "Budget_Seeker",
    "Luxury_Lover",
    "Sensitive_Skin",
    "Trend_Follower",
    "Natural_Beauty",
]

# 페르소나 변형 (실제 샘플 기반)
PERSONA_VARIANTS = [
    "budget seeker", "budget_seeker",
    "luxury lover", "luxury_lover",
    "sensitive skin", "sensitive_skin",
    "trend follower", "trend_follower",
    "natural beauty", "natural_beauty",
    "user_name",
]

# 튀는 생활/마케팅 영어 (부분 차단)
ENGLISH_TRIGGERS = [
    "everyday",
    "daily",
    "routine",
    "versatile",
    "태평양제약",
    "astrocypercol",
    "essential",
    "ultimate",
    "available",
    "suggestion",
    "lightweight",
    "clinical-grade",
]

# 메타/대괄호 표현
META_TOKENS = [
    "[", "]", "{", "}", "(", ")"
    "[제목]", "[CTA]",
    "[감성적", "[행동", "[보고]"
]

@lru_cache(maxsize=None)
def load_json(path: str) -> Any:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def find_persona(personas: List[Dict[str, Any]], persona_input: str) -> Dict[str, Any]:
    try:
        idx = int(persona_input)
        return personas[idx]
    except Exception:
        for p in personas:
            if p.get('name', '').lower() == str(persona_input).lower():
                return p
    raise ValueError(f'페르소나를 찾을 수 없습니다: {persona_input}')


def select_stage_bucket(categorized: List[Dict[str, Any]], stage_index: int) -> Dict[str, Any]:
    for bucket in categorized:
        if bucket.get('stage_index') == stage_index:
            return bucket
    raise ValueError(f'CRM 스테이지 버킷을 찾을 수 없습니다: {stage_index}')


def rag_crm_snippets(bucket: Dict[str, Any], query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    items = bucket.get('items', [])
    docs = [f"{it.get('description','')} {it.get('extracted_text','')}".strip() for it in items]
    if not docs:
        return []

    vectors = vectorize_texts([query] + docs)
    q_vec, doc_vecs = vectors[0], vectors[1:]

    scored = []
    for doc_vec, item, text in zip(doc_vecs, items, docs):
        scored.append({
            'score': cosine(q_vec, doc_vec),
            'source_index': item.get('source_index'),
            'filename': item.get('filename'),
            'text': text[:800]
        })
    scored.sort(key=lambda x: x['score'], reverse=True)
    return scored[:top_k]


def summarize_persona(persona: Dict[str, Any]) -> str:
    bits = []
    for key in ['name', 'skin_type', 'value_focus', 'shopping_style', 'growth_point', 'traits']:
        val = persona.get(key)
        if val:
            if isinstance(val, list):
                val = ', '.join(val)
            bits.append(f"{key}: {val}")
    return ' | '.join(bits)


def format_fomo_examples(fomo_data: Dict[str, Any], stage_index: int, limit: int = 3) -> List[str]:
    key = FOMO_STAGE_KEYS.get(stage_index)
    if not key:
        return []
    stage_items = fomo_data.get('CRM_FOMO_Psychology_50', {}).get(key, [])
    examples = []
    for entry in stage_items[:limit]:
        examples.append(f"[{entry.get('style','')}] {entry.get('title','')} :: {entry.get('content','')}")
    return examples


def pick_brand_params(brand_params: Dict[str, Any], brand_name: str) -> Dict[str, Any]:
    if brand_name in brand_params:
        return brand_params[brand_name]
    # name_en fallback
    for b in brand_params.values():
        if str(b.get('name_en','')).lower() == brand_name.lower():
            return b
    return {}


def load_crm_goal_meta(crm_goals: Dict[str, Any], stage_index: int) -> Dict[str, Any]:
    stage_name = STAGE_ORDER[stage_index]
    return crm_goals.get(stage_name, {})


def build_exaone_prompt(
    qwen_draft: str,
    persona: Dict[str, Any],
    brand_params: Dict[str, Any],
    crm_goal: Dict[str, Any],
    stage_index: int,
    crm_snippets: List[Dict[str, Any]],
    style_examples: List[str] = [],
) -> List[Dict[str, str]]:
    stage_name = STAGE_ORDER[stage_index]
    stage_kr = crm_goal.get('stage_kr', '')
    objective = crm_goal.get('objective', '')
    target_state = crm_goal.get('target_state', '')
    allowed = ', '.join(crm_goal.get('allowed_context', []))
    forbidden = ', '.join(crm_goal.get('forbidden_context', []))
    cta_style = crm_goal.get('cta_style', '')

    brand_info_lines = []
    if isinstance(brand_params, dict):
        for key in (
            "emotion_level",
            "sentence_density",
            "tone_style",
            "certainty_level",
            "rhythm",
            "brand_presence",
            "cta_pressure",
        ):
            value = brand_params.get(key)
            if value:
                brand_info_lines.append(f"- {key}: {value}")
    brand_info = "\n".join(brand_info_lines) if brand_info_lines else "- (없음)"
    style_section = ""
    if style_examples:
        template_refs = '\n'.join([f"--- [참고 템플릿] ---\n{t}" for t in style_examples])
        style_section = (
            "[CRM 캠페인 스타일 참고]\n"
            "아래 사례는 문장 구조와 흐름만 참고합니다.\n"
            f"{template_refs}\n\n"
        )

    system_prompt = (
        "당신은 생성자가 아닌 편집기(editor)입니다.\n"
        "입력 초안의 의미를 유지한 채,\n"
        "어휘와 문장 리듬만 조정합니다."
    )
    user_prompt = (
        "다음 초안을 재작성하지 말고,\n"
        "의미를 바꾸지 않는 선에서 표현만 다듬으세요.\n\n"
        "[입력 초안]\n"
        f"{qwen_draft}\n\n"
        "[브랜드 정보]\n"
        f"{brand_info}\n\n"
        "[발신 목적]\n"
        f"스테이지: {stage_name} ({stage_kr})\n"
        f"허용 맥락: {allowed}\n"
        f"금지 맥락: {forbidden}\n"
        f"CTA 스타일: {cta_style}\n\n"
        f"{style_section}"
        "규칙:\n"
        "1) 입력 초안의 의미를 유지한 채,\n"
        "   브랜드 톤과 발신 목적에 맞게 어휘와 문장 리듬만 조정합니다.\n"
        "   (새로운 효과, 기능, 결과를 추가하지 않습니다.)\n\n"
        "2) CTA는 1줄을 반드시 포함하세요.\n\n"
        "3) 출력 형식은 아래 두 줄을 그대로 사용하세요.\n"
        "   레이블과 형식을 변경하지 마세요.\n\n"
        "4) 영어 사용은 금지하며, 한국어로만 작성하세요.\n"
        "[제목] 한 줄 요약 제목\n"
        "[본문] 페르소나 공감 + 브랜드 톤 반영 본문 (CTA 포함)"
    )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def get_device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"

def build_bad_words_ids(tokenizer, phrases):
    bad_words_ids = []
    for p in phrases:
        ids = tokenizer.encode(p, add_special_tokens=False)
        if len(ids) > 0:
            bad_words_ids.append(ids)
    return bad_words_ids

class ExaoneToneCorrector:
    """Exaone 로컬 모델을 통한 톤 보정."""
    _CACHE = {}
    CACHE_ENABLED = True

    def __init__(self, model_name: str = "LGAI-EXAONE/EXAONE-4.0-1.2B", use_cache: bool = True):
        self.device = get_device()
        self.model_name = model_name
        cache_key = (self.device, model_name)
        cache_allowed = use_cache and self.CACHE_ENABLED
        cached = self._CACHE.get(cache_key) if cache_allowed else None
        if cached:
            self.tokenizer = cached["tokenizer"]
            self.model = cached["model"]
            print(f"[Exaone] 캐시 로딩: {model_name}")
            return

        print(f"[Exaone] 디바이스: {self.device}")
        print(f"[Exaone] 모델 로딩 중: {model_name}...")

        self.tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)

        # bad_words 디코딩 레벨 제한
        self.bad_words_ids = []
        self.bad_words_ids += build_bad_words_ids(self.tokenizer, PERSONA_NAMES)
        self.bad_words_ids += build_bad_words_ids(self.tokenizer, PERSONA_VARIANTS)
        self.bad_words_ids += build_bad_words_ids(self.tokenizer, ENGLISH_TRIGGERS)
        self.bad_words_ids += build_bad_words_ids(self.tokenizer, META_TOKENS)


        dtype = torch.float16 if self.device == "cuda" else torch.float32
        kwargs = {"trust_remote_code": True, "torch_dtype": dtype}
        if self.device == "cuda":
            kwargs["device_map"] = "auto"

        self.model = AutoModelForCausalLM.from_pretrained(model_name, **kwargs)
        try:
            self.model.eval()
        except Exception:
            pass
        if cache_allowed:
            self._CACHE[cache_key] = {
                "tokenizer": self.tokenizer,
                "model": self.model,
            }
        print("[Exaone] 모델 로딩 완료")

    def generate(self, messages: List[Dict[str, str]], max_tokens: int = 512, temperature: float = 0.4):
        try:
            input_text = self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
            )
        except Exception:
            input_text = "\n".join([f"{m['role']}: {m['content']}" for m in messages])

        inputs = self.tokenizer(
            input_text,
            return_tensors="pt",
            truncation=True,
            max_length=3072
        ).to(self.device)

        with torch.inference_mode():
            output_ids = self.model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=temperature,
                top_p=0.9,
                do_sample=True,
                repetition_penalty=1.1,
                bad_words_ids=self.bad_words_ids,
                pad_token_id=self.tokenizer.eos_token_id
            )

        generated_ids = output_ids[0][inputs['input_ids'].shape[1]:]
        text = self.tokenizer.decode(generated_ids, skip_special_tokens=True)
        return text.strip()


    def generate_batch(self, messages_list, max_tokens: int = 512, temperature: float = 0.4):
        if not messages_list:
            return []

        input_texts = []
        for messages in messages_list:
            try:
                input_text = self.tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True
                )
            except Exception:
                input_text = "\n".join(
                    [f"{m['role']}: {m['content']}" for m in messages]
                )
            input_texts.append(input_text)

        inputs = self.tokenizer(
            input_texts,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=3072
        ).to(self.device)

        with torch.inference_mode():
            output_ids = self.model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=temperature,
                top_p=0.9,
                do_sample=True,
                repetition_penalty=1.1,
                pad_token_id=self.tokenizer.eos_token_id
            )

        input_lengths = inputs["attention_mask"].sum(dim=1).tolist()
        outputs = []
        for i, input_len in enumerate(input_lengths):
            generated_ids = output_ids[i][int(input_len):]
            text = self.tokenizer.decode(generated_ids, skip_special_tokens=True)
            outputs.append(text.strip())
        return outputs

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--draft_path', help='Qwen 마케팅 초안 파일 경로(txt 또는 json)', required=False)
    parser.add_argument('--draft_text', help='직접 입력하는 초안 텍스트', required=False)
    parser.add_argument('--persona', required=True, help='페르소나 인덱스(0~) 또는 이름')
    parser.add_argument('--brand', required=True, help='브랜드명 (brand_params.json 키)')
    parser.add_argument('--stage_index', type=int, required=True, help='발신 목적 인덱스 (0~4)')
    parser.add_argument('--top_k', type=int, default=5, help='CRM RAG Top-K')
    parser.add_argument('--model_name', default="LGAI-EXAONE/EXAONE-3.0-7.8B-Instruct", help='Exaone 로컬 모델 이름')
    parser.add_argument('--out_path', default=None, help='결과 저장 경로')
    args = parser.parse_args()

    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base, 'data')

    if args.draft_text:
        qwen_draft = args.draft_text
    elif args.draft_path:
        raw = load_json(args.draft_path) if args.draft_path.endswith('.json') else open(args.draft_path, encoding='utf-8').read()
        if isinstance(raw, dict):
            qwen_draft = raw.get('marketing_draft') or raw.get('body') or json.dumps(raw, ensure_ascii=False)
        else:
            qwen_draft = str(raw)
    else:
        raise ValueError('draft_text 또는 draft_path 중 하나는 필요합니다.')

    personas = load_json(os.path.join(data_dir, 'personas.json'))
    brand_params = load_json(os.path.join(data_dir, 'brand_params.json'))
    crm_goals = load_json(os.path.join(data_dir, 'crm_goals.json'))
    crm_categorized = load_json(os.path.join(data_dir, 'crm_analysis_results_categorized.json'))
    crm_categorized = load_json(os.path.join(data_dir, 'crm_analysis_results_categorized.json'))
    # fomo_data = load_json(os.path.join(data_dir, 'FOMO.json'))
    integrated_templates = load_json(os.path.join(data_dir, 'integrated_crm_templates.json'))
    fomo_data = integrated_templates.get('FOMO_Psychology_Style', {}).get('content', {})

    persona = find_persona(personas, args.persona)
    brand_params_item = pick_brand_params(brand_params, args.brand)
    crm_goal = load_crm_goal_meta(crm_goals, args.stage_index)
    bucket = select_stage_bucket(crm_categorized, args.stage_index)

    query = qwen_draft[:500]
    crm_snippets = rag_crm_snippets(bucket, query, top_k=args.top_k)
    fomo_examples = format_fomo_examples(fomo_data, args.stage_index, limit=3)

    messages = build_exaone_prompt(
        qwen_draft=qwen_draft,
        persona=persona,
        brand_params=brand_params_item,
        crm_goal=crm_goal,
        stage_index=args.stage_index,
        crm_snippets=crm_snippets,
    )

    generator = ExaoneToneCorrector(model_name=args.model_name)
    output_text = generator.generate(messages)

    # 결과 패키징
    out = {
        'persona': persona,
        'brand': args.brand,
        'stage_index': args.stage_index,
        'stage_name': STAGE_ORDER[args.stage_index],
        'qwen_draft': qwen_draft,
        'crm_rag': crm_snippets,
        'fomo_examples': fomo_examples,
        'tone_corrected_raw': output_text,
    }

    out_dir = os.path.join(base, 'outputs')
    os.makedirs(out_dir, exist_ok=True)
    out_path = args.out_path or os.path.join(
        out_dir,
        f"tone_corrected_{args.brand}_{STAGE_ORDER[args.stage_index]}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    )
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print('✓ 톤 보정 완료:', out_path)
    print('--- 미리보기 ---')
    print(output_text[:500])


if __name__ == '__main__':
    main()
