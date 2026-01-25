#!/usr/bin/env python3
"""
CRM 메시지 출력 검증 GATE 로직

Exaone 출력이 최소 품질 기준을 충족하는지 검증하고,
통과하지 못하면 재생성을 트리거합니다.
"""

import re
from typing import Dict, List, Tuple, Optional


# 페르소나명 리스트 (tone_correction.py의 PERSONA_NAMES와 동기화 필요)
PERSONA_NAMES = [
    "오프라인파 스마트 쇼퍼",
    "백화점 기반 실속파 다구매자",
    "프리미엄 럭셔리 스마트 자산가",
    "자사몰 헤비 탐험가",
    "자사몰 올인(All-in) 로열 팬덤",
    "올인",
    "All-in",
    "실속형 온라인 타사 중심 쇼퍼",
    "오프라인 기반 고관여 럭셔리 유저",
    "온라인 중심 실속 효율 쇼퍼",
    "뉴커머스 럭셔리 쇼퍼",
    "하이엔드 뉴커머스 VVIP",
    "VVIP",
]

# 페르소나 ID
PERSONA_IDS = [
    "CL_01", "CL_02", "CL_03", "CL_04", "CL_05",
    "CL_06", "CL_07", "CL_08", "CL_09", "CL_10",
]

# 길이 제한 (글자 수 기준)
TITLE_MIN_LENGTH = 5
TITLE_MAX_LENGTH = 35
BODY_MIN_LENGTH = 40
BODY_MAX_LENGTH = 150

# 금지 단어 (추가 가능)
FORBIDDEN_WORDS = [
    "완벽 개선", "즉시 효과", "100% 보장", "치료",
    "즉각", "완벽", "보장", "100%",
]


def parse_crm_message(text: str) -> Optional[Dict[str, str]]:
    """
    CRM 메시지에서 [제목]과 [본문]을 파싱합니다.

    Returns:
        {"title": str, "body": str} 또는 None (파싱 실패 시)
    """
    # [제목], [본문] 패턴 찾기
    title_match = re.search(r'\[제목\]\s*\n?(.*?)(?=\[본문\]|$)', text, re.DOTALL)
    body_match = re.search(r'\[본문\]\s*\n?(.*?)$', text, re.DOTALL)

    # 둘 다 있는 경우
    if title_match and body_match:
        title = title_match.group(1).strip()
        body = body_match.group(1).strip()
        return {"title": title, "body": body}

    # [제목], [본문] 레이블이 없는 경우 - \n\n 으로 구분 시도
    parts = text.strip().split('\n\n', 1)
    if len(parts) == 2:
        return {"title": parts[0].strip(), "body": parts[1].strip()}

    # 단일 \n으로 구분 시도 (제목과 본문이 각각 한 줄인 경우)
    parts = text.strip().split('\n', 1)
    if len(parts) == 2:
        potential_title = parts[0].strip()
        potential_body = parts[1].strip()

        # 제목이 너무 길지 않은 경우만 유효
        if len(potential_title) <= TITLE_MAX_LENGTH:
            return {"title": potential_title, "body": potential_body}

    return None


def remove_markdown(text: str) -> str:
    """
    마크다운 문법을 제거합니다.
    """
    # 볼드 제거: **text** -> text
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)

    # 이탤릭 제거: *text* -> text
    text = re.sub(r'\*(.+?)\*', r'\1', text)

    # 언더스코어 볼드 제거: __text__ -> text
    text = re.sub(r'__(.+?)__', r'\1', text)

    # 언더스코어 이탤릭 제거: _text_ -> text
    text = re.sub(r'_(.+?)_', r'\1', text)

    # 링크 제거: [text](url) -> text
    text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)

    # 헤딩 제거: ### text -> text
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)

    # 코드 블록 제거: `code` -> code
    text = re.sub(r'`(.+?)`', r'\1', text)

    return text.strip()


def clean_crm_text(parsed: Dict[str, str]) -> Dict[str, str]:
    """
    파싱된 제목/본문에서 마크다운 및 불필요한 문법을 제거합니다.
    """
    title = remove_markdown(parsed["title"])
    body = remove_markdown(parsed["body"])

    # 추가 정제: 앞뒤 따옴표 제거
    title = title.strip('"\'""''')
    body = body.strip('"\'""''')

    return {"title": title, "body": body}


def check_persona_leakage(text: str, persona_name: str) -> Tuple[bool, List[str]]:
    """
    페르소나명이 출력에 포함되어 있는지 확인합니다.

    Returns:
        (has_leakage: bool, found_names: List[str])
    """
    found = []

    # 현재 페르소나명 체크
    if persona_name and persona_name in text:
        found.append(persona_name)

    # 전체 페르소나명 리스트 체크
    for name in PERSONA_NAMES:
        if name in text:
            found.append(name)

    # 페르소나 ID 체크
    for pid in PERSONA_IDS:
        if pid in text:
            found.append(pid)

    return len(found) > 0, found


def check_english_words(text: str, min_length: int = 4) -> Tuple[bool, List[str]]:
    """
    4자 이상의 영어 단어가 포함되어 있는지 확인합니다.

    Returns:
        (has_long_english: bool, found_words: List[str])
    """
    # 영어 단어 추출 (4자 이상)
    english_pattern = r'\b[A-Za-z]{' + str(min_length) + r',}\b'
    matches = re.findall(english_pattern, text)

    # CTA는 예외 처리
    allowed = {'CTA'}
    filtered = [w for w in matches if w not in allowed]

    return len(filtered) > 0, filtered


def check_format_validity(parsed: Optional[Dict[str, str]]) -> Tuple[bool, str]:
    """
    파싱된 제목/본문이 형식 요구사항을 충족하는지 확인합니다.

    Returns:
        (is_valid: bool, error_message: str)
    """
    if parsed is None:
        return False, "제목과 본문을 파싱할 수 없습니다"

    title = parsed["title"]
    body = parsed["body"]

    # 제목 길이 체크
    title_len = len(title)
    if title_len < TITLE_MIN_LENGTH:
        return False, f"제목이 너무 짧습니다 ({title_len}자 < {TITLE_MIN_LENGTH}자)"
    if title_len > TITLE_MAX_LENGTH:
        return False, f"제목이 너무 깁니다 ({title_len}자 > {TITLE_MAX_LENGTH}자)"

    # 본문 길이 체크
    body_len = len(body)
    if body_len < BODY_MIN_LENGTH:
        return False, f"본문이 너무 짧습니다 ({body_len}자 < {BODY_MIN_LENGTH}자)"
    if body_len > BODY_MAX_LENGTH:
        return False, f"본문이 너무 깁니다 ({body_len}자 > {BODY_MAX_LENGTH}자)"

    # 제목에 줄바꿈이 있는지 체크 (제목은 한 줄이어야 함)
    if '\n' in title:
        return False, "제목에 줄바꿈이 포함되어 있습니다"

    # 본문 줄 수 체크 (1~3줄)
    body_lines = [line.strip() for line in body.split('\n') if line.strip()]
    if len(body_lines) < 1:
        return False, "본문이 비어있습니다"
    if len(body_lines) > 4:
        return False, f"본문이 너무 많은 줄로 구성되어 있습니다 ({len(body_lines)}줄 > 4줄)"

    return True, ""


def check_forbidden_words(text: str) -> Tuple[bool, List[str]]:
    """
    금지 단어가 포함되어 있는지 확인합니다.

    Returns:
        (has_forbidden: bool, found_words: List[str])
    """
    found = [word for word in FORBIDDEN_WORDS if word in text]
    return len(found) > 0, found


def validate_crm_output(
    output: str,
    persona_name: str = "",
    enable_persona_check: bool = True,
    enable_english_check: bool = True,
    enable_format_check: bool = True,
    enable_forbidden_check: bool = True,
) -> Dict[str, any]:
    """
    CRM 메시지 출력을 검증합니다.

    Args:
        output: Exaone의 출력 텍스트
        persona_name: 현재 페르소나명
        enable_*_check: 각 검증 항목 활성화 여부

    Returns:
        {
            "passed": bool,
            "parsed": {"title": str, "body": str} or None,
            "cleaned": {"title": str, "body": str} or None,
            "errors": List[str],
            "warnings": List[str],
        }
    """
    errors = []
    warnings = []

    # 1. 파싱
    parsed = parse_crm_message(output)

    # 2. 형식 검증
    if enable_format_check:
        format_valid, format_error = check_format_validity(parsed)
        if not format_valid:
            errors.append(f"형식 오류: {format_error}")

    # 파싱 실패 시 조기 반환
    if parsed is None:
        return {
            "passed": False,
            "parsed": None,
            "cleaned": None,
            "errors": errors,
            "warnings": warnings,
        }

    # 3. 마크다운 제거
    cleaned = clean_crm_text(parsed)
    combined_text = f"{cleaned['title']}\n{cleaned['body']}"

    # 4. 페르소나명 누출 검증
    if enable_persona_check:
        has_leakage, found_names = check_persona_leakage(combined_text, persona_name)
        if has_leakage:
            errors.append(f"페르소나명 누출: {', '.join(set(found_names))}")

    # 5. 영어 단어 검증
    if enable_english_check:
        has_english, found_words = check_english_words(combined_text)
        if has_english:
            errors.append(f"4자 이상 영어 단어 사용: {', '.join(set(found_words))}")

    # 6. 금지 단어 검증
    if enable_forbidden_check:
        has_forbidden, found_words = check_forbidden_words(combined_text)
        if has_forbidden:
            errors.append(f"금지 단어 사용: {', '.join(set(found_words))}")

    # 7. 추가 검증: CTA 포함 여부 (경고)
    if 'CTA' not in output and not any(keyword in cleaned['body'] for keyword in ['확인', '지금', '바로', '클릭', '만나']):
        warnings.append("CTA 문구가 명확하지 않을 수 있습니다")

    passed = len(errors) == 0

    return {
        "passed": passed,
        "parsed": parsed,
        "cleaned": cleaned,
        "errors": errors,
        "warnings": warnings,
    }


def format_output(cleaned: Dict[str, str]) -> str:
    """
    검증을 통과한 메시지를 최종 형식으로 포맷팅합니다.
    """
    return f"[제목]\n{cleaned['title']}\n\n[본문]\n{cleaned['body']}"


def gate_with_retry(
    generator,
    messages: List[Dict[str, str]],
    persona_name: str = "",
    max_retries: int = 3,
    enable_persona_check: bool = True,
    enable_english_check: bool = True,
    enable_format_check: bool = True,
    enable_forbidden_check: bool = True,
    temperature: float = 0.4,
) -> Dict[str, any]:
    """
    GATE 검증을 통과할 때까지 재시도합니다.

    Returns:
        {
            "success": bool,
            "output": str (최종 출력),
            "formatted": str (포맷된 출력),
            "attempts": int,
            "validation_result": Dict,
            "raw_outputs": List[str] (각 시도의 원본 출력),
        }
    """
    raw_outputs = []

    for attempt in range(1, max_retries + 1):
        # Exaone 생성
        raw_output = generator.generate(messages, temperature=temperature)
        raw_outputs.append(raw_output)

        print(f"[GATE] Attempt {attempt}/{max_retries}")

        # 검증
        validation = validate_crm_output(
            raw_output,
            persona_name=persona_name,
            enable_persona_check=enable_persona_check,
            enable_english_check=enable_english_check,
            enable_format_check=enable_format_check,
            enable_forbidden_check=enable_forbidden_check,
        )

        # 검증 통과
        if validation["passed"]:
            formatted = format_output(validation["cleaned"])
            print(f"[GATE] ✓ 검증 통과 (시도: {attempt})")
            return {
                "success": True,
                "output": raw_output,
                "formatted": formatted,
                "title": validation["cleaned"]["title"],
                "body": validation["cleaned"]["body"],
                "attempts": attempt,
                "validation_result": validation,
                "raw_outputs": raw_outputs,
            }

        # 검증 실패
        print(f"[GATE] ✗ 검증 실패:")
        for error in validation["errors"]:
            print(f"  - {error}")

        if validation["warnings"]:
            print(f"[GATE] ⚠ 경고:")
            for warning in validation["warnings"]:
                print(f"  - {warning}")

        # 온도 약간 증가 (다양성 확보)
        temperature = min(temperature + 0.1, 0.9)

    # 최대 재시도 횟수 초과
    print(f"[GATE] ✗ 최대 재시도 횟수 초과 ({max_retries})")

    # 마지막 시도 결과 반환 (실패)
    last_validation = validate_crm_output(
        raw_outputs[-1],
        persona_name=persona_name,
        enable_persona_check=False,  # 실패 시 검증 완화
        enable_english_check=False,
        enable_format_check=True,
        enable_forbidden_check=False,
    )

    formatted = ""
    title = ""
    body = ""
    if last_validation["cleaned"]:
        formatted = format_output(last_validation["cleaned"])
        title = last_validation["cleaned"]["title"]
        body = last_validation["cleaned"]["body"]

    return {
        "success": False,
        "output": raw_outputs[-1],
        "formatted": formatted,
        "title": title,
        "body": body,
        "attempts": max_retries,
        "validation_result": last_validation,
        "raw_outputs": raw_outputs,
    }
