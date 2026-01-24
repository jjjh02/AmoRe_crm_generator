import re
import math
from collections import Counter
import torch
from sentence_transformers import SentenceTransformer, util

# 전역 임베딩 모델 (한 번만 로드)
_embedder = None

def get_embedder():
    global _embedder
    if _embedder is None:
        print("Loading SentenceTransformer model (jhgan/ko-sroberta-multitask)...")
        _embedder = SentenceTransformer('jhgan/ko-sroberta-multitask')
    return _embedder


def tokenize(text):
    if not text:
        return []
    text = text.lower()
    text = re.sub(r"[^\w가-힣]+", ' ', text)
    toks = [t for t in text.split() if len(t) > 1]
    return toks


def vectorize_texts(texts):
    """SentenceTransformer를 사용한 의미 기반 벡터화"""
    if not texts:
        return []
    embedder = get_embedder()
    # 벡터를 numpy 배열로 반환 (cosine 함수에서 사용)
    vectors = embedder.encode(texts, convert_to_tensor=False)
    return vectors


def cosine(a, b):
    """SentenceTransformer 벡터를 위한 코사인 유사도"""
    if a is None or b is None:
        return 0.0
    import numpy as np
    a = np.array(a)
    b = np.array(b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


POSITIVE_KEYWORDS = [
    '좋', '만족', '추천', '재구매', '인생템', '효과', '흡수', '보습', '탄력', '광채', '진정', '재구매', '신뢰', '가볍', '리뉴얼'
]

HIGHLIGHT_KEYS = ['효과', '성분', '제형', '흡수', '보습', '재구매', '신뢰', '사용감', '탄력', '주름', '진정', '광채']


def is_positive_review(review):
    if not isinstance(review, dict):
        return False
    rating = review.get('rating')
    if rating:
        try:
            if int(rating) >= 4:
                return True
        except Exception:
            pass
    text = review.get('text','')
    for k in POSITIVE_KEYWORDS:
        if k in text:
            return True
    return False


def extract_candidate_texts(product):
    """제품의 설명 텍스트 추출"""
    texts = []

    # 제품 설명 추출
    description = product.get('description', '').strip()
    if description:
        # 문장 단위로 분리 (마침표, 쉼표 등으로 구분)
        sentences = re.split(r'[.,;]\s*', description)
        for sent in sentences:
            sent = sent.strip()
            if len(sent) > 10:  # 최소 길이 필터
                texts.append(sent)

    # 설명이 없거나 너무 짧으면 전체 설명을 하나의 텍스트로 추가
    if not texts:
        texts.append(description if description else product.get('name', ''))

    return texts


def extract_highlight_snippet(text):
    if not text:
        return ''
    sents = re.split(r'[\.\n]+', text)
    for s in sents:
        for k in HIGHLIGHT_KEYS:
            if k in s:
                return s.strip()
    t = text.strip()
    return (t[:200] + '...') if len(t) > 200 else t


def build_persona_query(persona):
    """새로운 persona 형식에 맞춰 쿼리 생성"""
    parts = []

    # 이름
    if persona.get('name'):
        parts.append('페르소나: ' + persona['name'])

    # 라이프스타일
    if persona.get('lifestyle'):
        parts.append('라이프스타일: ' + persona['lifestyle'])

    # 페인 포인트
    if persona.get('pain_point'):
        parts.append('페인 포인트: ' + persona['pain_point'])

    # 행동 특성 (behavioral_traits는 dict이므로 값들을 추출)
    behavioral_traits = persona.get('behavioral_traits', {})
    if behavioral_traits:
        traits_str = ', '.join([f"{v}" for v in behavioral_traits.values()])
        parts.append('행동 특성: ' + traits_str)

    query = ' | '.join(parts)
    return query
