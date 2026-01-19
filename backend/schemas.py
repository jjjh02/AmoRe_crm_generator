"""
Pydantic Request/Response 스키마
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime
import uuid


# ========================
# Common Models
# ========================

class EventInfo(BaseModel):
    name: str = Field(..., description="이벤트명")
    detail: str = Field("", description="이벤트 상세 내용")


class DraftMessage(BaseModel):
    title: str = Field(..., description="메시지 제목")
    body: str = Field(..., description="메시지 본문")


class PersonaMessage(BaseModel):
    persona: str = Field(..., description="페르소나 ID (e.g., Luxury_Lover)")
    label: str = Field(..., description="페르소나 한글 라벨 (e.g., 프리미엄)")
    title: str = Field(..., description="메시지 제목")
    body: str = Field(..., description="메시지 본문")
    tone_keywords: List[str] = Field(default_factory=list, description="적용된 톤 키워드")


# ========================
# Step 1: Brief
# ========================

class Step1BriefRequest(BaseModel):
    brand_name: str = Field(..., description="브랜드명")
    product_name: str = Field(..., description="제품명 (부분 일치 검색)")
    stage_index: int = Field(..., ge=0, description="AARRR 스테이지 인덱스 (0-4 기본, 5+ 커스텀)")
    style_index: int = Field(0, ge=0, description="스타일 인덱스 (0-4 기본, 5+ 커스텀)")
    custom_stage_name: Optional[str] = Field(None, description="커스텀 스테이지명 (스테이지 인덱스가 5 이상일 때)")
    custom_style_name: Optional[str] = Field(None, description="커스텀 스타일명 (스타일 인덱스가 5 이상일 때)") 
    event: Optional[EventInfo] = Field(None, description="이벤트 정보 (선택)")


class BriefData(BaseModel):
    target_definition: List[str] = Field(default_factory=list)
    core_message: List[str] = Field(default_factory=list)
    usp: List[str] = Field(default_factory=list)
    cta_direction: str = ""


class Step1BriefResponse(BaseModel):
    success: bool = True
    data: Dict[str, Any] = Field(default_factory=dict)
    processing_time_ms: int = 0


class Step1RefineRequest(BaseModel):
    session_id: str = Field(..., description="세션 ID")
    current_brief: str = Field(..., description="현재 브리프 텍스트")
    feedback: str = Field(..., description="사용자 피드백")


# ========================
# Step 2: Draft
# ========================

class Step2DraftRequest(BaseModel):
    session_id: str = Field(..., description="세션 ID")
    brief_text: str = Field(..., description="확정된 브리프 텍스트")


class Step2DraftResponse(BaseModel):
    success: bool = True
    data: Dict[str, Any] = Field(default_factory=dict)
    processing_time_ms: int = 0


class Step2RefineRequest(BaseModel):
    session_id: str = Field(..., description="세션 ID")
    current_draft: DraftMessage = Field(..., description="현재 초안")
    feedback: str = Field(..., description="사용자 피드백")


# ========================
# Step 3: Tuning
# ========================

class Step3TuningRequest(BaseModel):
    session_id: str = Field(..., description="세션 ID")
    draft: DraftMessage = Field(..., description="확정된 초안")
    personas: List[str] = Field(
        default=["Luxury_Lover", "Budget_Seeker", "Sensitive_Skin", "Trend_Follower", "Natural_Beauty"],
        description="페르소나 ID 목록"
    )


class Step3TuningResponse(BaseModel):
    success: bool = True
    data: Dict[str, Any] = Field(default_factory=dict)
    processing_time_ms: int = 0


class Step3RefineRequest(BaseModel):
    session_id: str = Field(..., description="세션 ID")
    persona: str = Field(..., description="재생성할 페르소나 ID")
    current_message: DraftMessage = Field(..., description="현재 메시지")
    feedback: str = Field(..., description="사용자 피드백")


# ========================
# Error Response
# ========================

class ErrorResponse(BaseModel):
    success: bool = False
    error: Dict[str, str] = Field(default_factory=dict)
