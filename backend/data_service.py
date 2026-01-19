"""
데이터 로딩 서비스
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional

from .config import settings


class DataService:
    """JSON 데이터 로딩 및 캐싱"""
    
    _cache: Dict[str, Any] = {}
    
    @classmethod
    def _load_json(cls, filename: str) -> Any:
        """JSON 파일 로드 (캐싱)"""
        if filename in cls._cache:
            return cls._cache[filename]
        
        filepath = settings.DATA_DIR / filename
        if not filepath.exists():
            raise FileNotFoundError(f"Data file not found: {filepath}")
        
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        cls._cache[filename] = data
        return data
    
    @classmethod
    def get_personas(cls) -> List[Dict[str, Any]]:
        return cls._load_json("personas.json")
    
    @classmethod
    def get_products(cls) -> List[Dict[str, Any]]:
        return cls._load_json("products.json")
    
    @classmethod
    def get_brand_stories(cls) -> Dict[str, Any]:
        return cls._load_json("brand_stories.json")
    
    @classmethod
    def get_crm_goals(cls) -> Dict[str, Any]:
        return cls._load_json("crm_goals.json")
    
    @classmethod
    def get_campaign_events(cls) -> Dict[str, Any]:
        return cls._load_json("campaign_events.json")
    
    @classmethod
    def find_product(cls, brand: str, product_query: str) -> Optional[Dict[str, Any]]:
        """브랜드와 제품명으로 제품 검색 (부분 일치)"""
        products = cls.get_products()
        for p in products:
            if p.get("brand_name") == brand and product_query.lower() in p.get("name", "").lower():
                return p
        return None
    
    @classmethod
    def find_persona(cls, persona_input: str) -> Optional[Dict[str, Any]]:
        """페르소나 이름 또는 인덱스로 검색"""
        personas = cls.get_personas()
        
        # 인덱스로 검색
        if persona_input.isdigit():
            idx = int(persona_input)
            if 0 <= idx < len(personas):
                return personas[idx]
        
        # 이름으로 검색
        for p in personas:
            if p.get("name") == persona_input:
                return p
        
        return None
    
    @classmethod
    def get_brand_story(cls, brand_name: str) -> Dict[str, Any]:
        """브랜드 스토리 가져오기"""
        stories = cls.get_brand_stories()
        return stories.get(brand_name, {})
    
    @classmethod
    def get_crm_goal(cls, stage_index: int) -> Dict[str, Any]:
        """CRM 목표 가져오기"""
        goals = cls.get_crm_goals()
        stages = goals.get("stages", [])
        if 0 <= stage_index < len(stages):
            return stages[stage_index]
        return {}


STAGE_ORDER = ["Acquisition", "Activation", "Retention", "Revenue", "Referral"]
STAGE_KR = ["획득", "활성화", "유지", "수익화", "추천"]
STYLE_TYPES = [
    "Time_Urgency_Style",
    "Information_Universal_Style", 
    "FOMO_Psychology_Style",
    "Emotional_Style",
    "Seasonal_Style",
    "Mixed_Strategies"
]


# 페르소나 정보 매핑
PERSONA_INFO = {
    "Luxury_Lover": {"label": "프리미엄", "color": "#9065B0"},
    "Sensitive_Skin": {"label": "민감성", "color": "#0F7B6C"},
    "Budget_Seeker": {"label": "가성비", "color": "#D9730D"},
    "Trend_Follower": {"label": "트렌드", "color": "#E03E8E"},
    "Natural_Beauty": {"label": "자연주의", "color": "#2383E2"},
}
