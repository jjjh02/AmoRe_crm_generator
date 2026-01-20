"""
프롬프트 템플릿 모듈
각 Step별 LLM 프롬프트 생성
"""

from typing import Dict, Any, List, Optional


def build_brief_prompt(
    brand_name: str,
    product_name: str,
    product_info: Dict[str, Any],
    stage_name: str,
    stage_kr: str,
    crm_goal: Dict[str, Any],
    brand_story: Dict[str, Any],
    event: Optional[Dict[str, str]] = None
) -> List[Dict[str, str]]:
    """Step 1: 브리프 생성 프롬프트"""
    
    # 제품 정보 추출
    price = product_info.get("price", "정보 없음")
    category = product_info.get("category", "")
    reviews_sample = product_info.get("reviews", [])[:3]
    reviews_text = "\n".join([f"- {r.get('text', '')[:100]}" for r in reviews_sample]) if reviews_sample else "리뷰 정보 없음"
    
    # 브랜드 톤
    tone_keywords = ", ".join(brand_story.get("tone_keywords", []))
    brand_story_text = brand_story.get("story", "")
    
    # CRM 목표
    objective = crm_goal.get("objective", "")
    target_state = crm_goal.get("target_state", "")
    
    # 이벤트 정보
    event_section = ""
    if event:
        event_section = f"""
[이벤트 정보]
이벤트명: {event.get('name', '')}
상세: {event.get('detail', '')}
"""
    
    user_prompt = f"""당신은 뷰티 브랜드 마케팅 전문가입니다. 아래 정보를 바탕으로 CRM 캠페인 브리프를 작성하세요.

[브랜드 정보]
브랜드: {brand_name}
브랜드 스토리: {brand_story_text}
톤 키워드: {tone_keywords}

[제품 정보]
제품명: {product_name}
카테고리: {category}
가격: {price}원

[고객 리뷰 발췌]
{reviews_text}
{event_section}
[CRM 발송 목적]
스테이지: {stage_name} ({stage_kr})
목표: {objective}
타겟 고객 상태: {target_state}

작성 규칙:
1. 반드시 아래 형식을 따르세요 (개조식으로 작성)
2. 각 항목은 2-4개의 핵심 포인트로 구성
3. 구체적이고 실행 가능한 내용으로 작성

출력 형식:
📋 마케팅 브리프

[타겟 정의]
• (타겟 고객층 정의)
• (니즈 및 고민)

[핵심 메시지]
• (제품의 핵심 가치 1)
• (제품의 핵심 가치 2)

[USP (차별화 포인트)]
• (경쟁사 대비 강점 1)
• (경쟁사 대비 강점 2)

[CTA 방향]
• (행동 유도 방향 및 톤)
"""

    return [
        {"role": "system", "content": "당신은 뷰티 브랜드의 CRM 마케팅 전문가입니다. 간결하고 핵심적인 개조식 브리프를 작성합니다."},
        {"role": "user", "content": user_prompt}
    ]


def build_brief_refine_prompt(
    current_brief: str,
    feedback: str
) -> List[Dict[str, str]]:
    """Step 1: 브리프 피드백 반영 재생성 프롬프트"""
    
    user_prompt = f"""아래 마케팅 브리프를 피드백에 맞게 수정하세요.

[현재 브리프]
{current_brief}

[사용자 피드백]
{feedback}

수정 규칙:
1. 피드백 내용을 정확히 반영
2. 기존 형식(개조식) 유지
3. 피드백에서 언급하지 않은 부분은 최대한 유지

출력: 수정된 전체 브리프 (형식 동일하게)
"""

    return [
        {"role": "system", "content": "당신은 뷰티 브랜드의 CRM 마케팅 전문가입니다. 피드백을 반영하여 브리프를 개선합니다."},
        {"role": "user", "content": user_prompt}
    ]


def build_draft_prompt(
    brief_text: str,
    brand_name: str,
    brand_story: Dict[str, Any]
) -> List[Dict[str, str]]:
    """Step 2: 초안 생성 프롬프트 (브랜드 톤 반영)"""
    
    tone_keywords = ", ".join(brand_story.get("tone_keywords", []))
    brand_story_text = brand_story.get("story", "")
    
    user_prompt = f"""당신은 {brand_name} 브랜드의 CRM 카피라이터입니다.
아래 브리프를 바탕으로 브랜드 톤에 맞는 CRM 메시지 초안을 작성하세요.

[마케팅 브리프]
{brief_text}

[브랜드 톤앤매너]
브랜드: {brand_name}
톤 키워드: {tone_keywords}
스토리: {brand_story_text}

작성 규칙:
1. 브리프의 핵심 메시지와 USP를 충실히 반영
2. 브랜드 톤 키워드에 맞는 어휘와 문체 사용
3. 제목은 30-50자로 임팩트 있게
4. 본문은 150-250자로 간결하게
5. CTA 방향에 맞는 행동 유도 문구 포함

출력 형식:
[제목]
(간결하고 임팩트 있는 헤드라인)

[본문]
(브랜드 톤 + 핵심 메시지 + CTA 포함)
"""

    return [
        {"role": "system", "content": f"당신은 {brand_name}의 CRM 카피라이터입니다. 브랜드 톤에 맞는 자연스러운 한국어 메시지를 작성합니다."},
        {"role": "user", "content": user_prompt}
    ]


def build_draft_refine_prompt(
    current_title: str,
    current_body: str,
    feedback: str
) -> List[Dict[str, str]]:
    """Step 2: 초안 피드백 반영 재생성 프롬프트"""
    
    user_prompt = f"""아래 CRM 메시지 초안을 피드백에 맞게 수정하세요.

[현재 초안]
[제목]
{current_title}

[본문]
{current_body}

[사용자 피드백]
{feedback}

수정 규칙:
1. 피드백 내용을 정확히 반영
2. 기존 형식 유지 ([제목], [본문])
3. 피드백에서 언급하지 않은 부분은 최대한 유지

출력:
[제목]
(수정된 제목)

[본문]
(수정된 본문)
"""

    return [
        {"role": "system", "content": "당신은 CRM 카피라이터입니다. 피드백을 반영하여 메시지를 개선합니다."},
        {"role": "user", "content": user_prompt}
    ]


def build_tuning_prompt(
    draft_title: str,
    draft_body: str,
    persona: Dict[str, Any],
    persona_label: str
) -> List[Dict[str, str]]:
    """Step 3: 페르소나별 튜닝 프롬프트"""
    
    traits = ", ".join(persona.get("traits", []))
    value_focus = persona.get("value_focus", "")
    pain_points = ", ".join(persona.get("pain_points", []))
    preferred_tone = persona.get("preferred_tone", "")
    
    user_prompt = f"""아래 CRM 메시지 초안을 특정 고객 성향에 맞게 튜닝하세요.

[초안 메시지]
제목: {draft_title}
본문: {draft_body}

[타겟 고객 성향]
특성: {traits}
가치 중시점: {value_focus}
주요 고민: {pain_points}
선호 톤: {preferred_tone}

⚠️ 절대 금지 사항 (어기면 실패):
1. 페르소나 이름, ID, 라벨을 절대 언급하지 마세요 (예: Luxury_Lover, 프리미엄, 가성비 등)
2. 연령대, 나이를 절대 언급하지 마세요 (예: 30~45세, 20대 등)
3. "민감성 피부", "트렌드 추구" 등 페르소나를 직접 지칭하지 마세요
4. 메시지 끝에 설명, 주석, 핵심 포인트 등을 절대 붙이지 마세요
5. "---" 구분선이나 부가 설명을 넣지 마세요
6. "제목", "본문", "[제목]", "[본문]" 같은 헤더/라벨 텍스트를 출력에 포함하지 마세요

작성 규칙:
1. 제목: 25-40자 (짧고 임팩트 있게)
2. 본문: 80-120자 (핵심만 간결하게)
3. "당신", "고객님" 등 일반적인 호칭만 사용
4. 페르소나의 가치/고민을 암시적으로만 반영 (직접 언급 금지)
5. 반드시 아래 JSON 형식만 출력하고, 그 외 텍스트는 출력하지 마세요

출력 형식 (이 JSON만 출력):
{{"title":"25-40자 제목","body":"80-120자 본문"}}
"""

    return [
        {"role": "system", "content": "당신은 CRM 카피라이터입니다. JSON만 출력하고 그 외 텍스트는 금지입니다. 페르소나 이름이나 연령대는 절대 언급하지 않습니다."},
        {"role": "user", "content": user_prompt}
    ]


def build_tuning_refine_prompt(
    current_title: str,
    current_body: str,
    persona_label: str,
    feedback: str
) -> List[Dict[str, str]]:
    """Step 3: 페르소나 메시지 피드백 반영 재생성 프롬프트"""
    
    user_prompt = f"""아래 {persona_label} 페르소나용 CRM 메시지를 피드백에 맞게 수정하세요.

[현재 메시지]
[제목]
{current_title}

[본문]
{current_body}

[사용자 피드백]
{feedback}

수정 규칙:
1. 피드백 내용을 정확히 반영
2. 기존 형식 유지
3. {persona_label} 페르소나 특성 유지

출력:
[제목]
(수정된 제목)

[본문]
(수정된 본문)
"""

    return [
        {"role": "system", "content": f"당신은 {persona_label} 고객층을 위한 CRM 카피라이터입니다."},
        {"role": "user", "content": user_prompt}
    ]
