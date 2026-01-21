"""
CRM Message Studio - FastAPI Backend
3단계 인터랙티브 파이프라인 API
"""

import time
import uuid
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .llm_provider import get_llm_manager, LLMProviderManager
from .data_service import DataService, STAGE_ORDER, STAGE_KR, PERSONA_INFO
from .schemas import (
    Step1BriefRequest, Step1RefineRequest,
    Step2DraftRequest, Step2RefineRequest,
    Step3TuningRequest, Step3RefineRequest,
    ErrorResponse, ModelConfig
)
from .prompts import (
    build_brief_prompt, build_brief_refine_prompt,
    build_draft_prompt, build_draft_refine_prompt,
    build_tuning_prompt, build_tuning_refine_prompt
)


# 세션 저장소 (메모리 기반, 프로덕션에서는 Redis 등 사용)
sessions: Dict[str, Dict[str, Any]] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작/종료 이벤트"""
    llm_manager = get_llm_manager()
    available = llm_manager.get_available_providers()
    
    print(f"🚀 CRM Message Studio API 시작")
    print(f"   Available Providers: {available}")
    print(f"   Default Provider: {settings.LLM_PROVIDER}")
    if "ollama" in available:
        print(f"   Ollama Model: {settings.OLLAMA_MODEL}")
    if "openrouter" in available:
        print(f"   OpenRouter Model: {settings.OPENROUTER_DEFAULT_MODEL}")
    yield
    print("👋 API 종료")


app = FastAPI(
    title="CRM Message Studio API",
    description="3단계 인터랙티브 CRM 메시지 생성 파이프라인",
    version="2.0.0",
    lifespan=lifespan
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발용, 프로덕션에서는 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# LLM Provider Manager
llm_manager = get_llm_manager()


def get_model_params(model_config: Optional[ModelConfig]) -> tuple:
    """ModelConfig에서 provider와 model 추출"""
    if model_config:
        return model_config.provider, model_config.model
    return None, None


# ===========================
# Health Check & Model Info
# ===========================

@app.get("/health")
async def health_check():
    """서버 상태 확인"""
    return {
        "status": "ok",
        "providers": llm_manager.get_available_providers(),
        "default_provider": settings.LLM_PROVIDER
    }


@app.get(f"{settings.API_PREFIX}/models")
async def get_available_models():
    """사용 가능한 LLM 모델 목록 조회"""
    available_providers = llm_manager.get_available_providers()
    
    result = {
        "providers": [],
        "default_provider": settings.LLM_PROVIDER
    }
    
    for provider_name in available_providers:
        models = settings.AVAILABLE_MODELS.get(provider_name, [])
        
        # 기본 모델 결정
        if provider_name == "ollama":
            default_model = settings.OLLAMA_MODEL
        elif provider_name == "openrouter":
            default_model = settings.OPENROUTER_DEFAULT_MODEL
        else:
            default_model = models[0]["id"] if models else None
        
        result["providers"].append({
            "id": provider_name,
            "name": provider_name.title(),
            "models": models,
            "default_model": default_model
        })
    
    return {
        "success": True,
        "data": result
    }


@app.get(f"{settings.API_PREFIX}/personas")
async def get_personas():
    """사용 가능한 페르소나 목록 조회"""
    personas_list = []
    for persona_id, info in PERSONA_INFO.items():
        personas_list.append({
            "id": persona_id,
            "label": info["label"],
            "color": info.get("color", "#333")
        })
    
    return {
        "success": True,
        "data": {
            "personas": personas_list
        }
    }


# ===========================
# Step 1: Brief
# ===========================

@app.post(f"{settings.API_PREFIX}/step1/brief")
async def create_brief(request: Step1BriefRequest):
    """Step 1: 마케팅 브리프 생성"""
    start_time = time.time()
    
    try:
        # 모델 설정 추출
        provider, model = get_model_params(request.model_config_input)
        
        # 제품 검색
        product = DataService.find_product(request.brand_name, request.product_name)
        if not product:
            raise HTTPException(status_code=404, detail=f"제품을 찾을 수 없습니다: {request.brand_name} - {request.product_name}")
        
        # 브랜드 스토리
        brand_story = DataService.get_brand_story(request.brand_name)
        
        # CRM 목표
        crm_goal = DataService.get_crm_goal(request.stage_index)
        
        # 스테이지 정보 (커스텀 스테이지 지원)
        if request.custom_stage_name:
            stage_name = "Custom"
            stage_kr = request.custom_stage_name
        elif 0 <= request.stage_index < len(STAGE_ORDER):
            stage_name = STAGE_ORDER[request.stage_index]
            stage_kr = STAGE_KR[request.stage_index]
        else:
            stage_name = "Custom"
            stage_kr = "커스텀"
        
        # 이벤트 정보
        event = None
        if request.event:
            event = {"name": request.event.name, "detail": request.event.detail}
        
        # 프롬프트 생성
        messages = build_brief_prompt(
            brand_name=request.brand_name,
            product_name=product.get("name", request.product_name),
            product_info=product,
            stage_name=stage_name,
            stage_kr=stage_kr,
            crm_goal=crm_goal,
            brand_story=brand_story,
            event=event
        )
        
        # LLM 호출 (모델 선택 지원)
        brief_text = await llm_manager.generate(
            messages=messages,
            provider=provider,
            model=model,
            max_tokens=1024,
            temperature=0.7
        )
        
        # 세션 생성
        session_id = f"sess_{uuid.uuid4().hex[:12]}"
        sessions[session_id] = {
            "brand_name": request.brand_name,
            "product": product,
            "brand_story": brand_story,
            "stage_index": request.stage_index,
            "stage_name": stage_name,
            "crm_goal": crm_goal,
            "event": event,
            "brief_text": brief_text
        }
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return {
            "success": True,
            "data": {
                "step": "brief",
                "session_id": session_id,
                "brief_text": brief_text,
                "brand_name": request.brand_name,
                "product_name": product.get("name"),
                "stage": stage_name,
                "stage_kr": stage_kr,
                "model_used": {
                    "provider": provider or settings.LLM_PROVIDER,
                    "model": model
                }
            },
            "processing_time_ms": processing_time
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put(f"{settings.API_PREFIX}/step1/brief/refine")
async def refine_brief(request: Step1RefineRequest):
    """Step 1: 브리프 피드백 반영 재생성"""
    start_time = time.time()
    
    try:
        # 모델 설정 추출
        provider, model = get_model_params(request.model_config_input)
        
        # 세션 확인
        session = sessions.get(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")
        
        # 프롬프트 생성
        messages = build_brief_refine_prompt(request.current_brief, request.feedback)
        
        # LLM 호출 (모델 선택 지원)
        brief_text = await llm_manager.generate(
            messages=messages,
            provider=provider,
            model=model,
            max_tokens=1024,
            temperature=0.7
        )
        
        # 세션 업데이트
        session["brief_text"] = brief_text
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return {
            "success": True,
            "data": {
                "step": "brief",
                "session_id": request.session_id,
                "brief_text": brief_text,
                "feedback_applied": request.feedback
            },
            "processing_time_ms": processing_time
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===========================
# Step 2: Draft
# ===========================

@app.post(f"{settings.API_PREFIX}/step2/draft")
async def create_draft(request: Step2DraftRequest):
    """Step 2: 브랜드 톤 반영 초안 생성"""
    start_time = time.time()
    
    try:
        # 모델 설정 추출
        provider, model = get_model_params(request.model_config_input)
        
        # 세션 확인
        session = sessions.get(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")
        
        brand_name = session["brand_name"]
        brand_story = session["brand_story"]
        
        # 프롬프트 생성
        messages = build_draft_prompt(
            brief_text=request.brief_text,
            brand_name=brand_name,
            brand_story=brand_story
        )
        
        # LLM 호출 (모델 선택 지원)
        draft_text = await llm_manager.generate(
            messages=messages,
            provider=provider,
            model=model,
            max_tokens=1024,
            temperature=0.7
        )
        
        # 제목/본문 파싱
        title, body = parse_title_body(draft_text)
        
        # 세션 업데이트
        session["draft_title"] = title
        session["draft_body"] = body
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return {
            "success": True,
            "data": {
                "step": "draft",
                "session_id": request.session_id,
                "title": title,
                "body": body,
                "raw_output": draft_text,
                "brand_name": brand_name,
                "brand_tone": brand_story.get("tone_keywords", []),
                "model_used": {
                    "provider": provider or settings.LLM_PROVIDER,
                    "model": model
                }
            },
            "processing_time_ms": processing_time
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put(f"{settings.API_PREFIX}/step2/draft/refine")
async def refine_draft(request: Step2RefineRequest):
    """Step 2: 초안 피드백 반영 재생성"""
    start_time = time.time()
    
    try:
        # 모델 설정 추출
        provider, model = get_model_params(request.model_config_input)
        
        # 세션 확인
        session = sessions.get(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")
        
        # 프롬프트 생성
        messages = build_draft_refine_prompt(
            current_title=request.current_draft.title,
            current_body=request.current_draft.body,
            feedback=request.feedback
        )
        
        # LLM 호출 (모델 선택 지원)
        draft_text = await llm_manager.generate(
            messages=messages,
            provider=provider,
            model=model,
            max_tokens=1024,
            temperature=0.7
        )
        
        # 제목/본문 파싱
        title, body = parse_title_body(draft_text)
        
        # 세션 업데이트
        session["draft_title"] = title
        session["draft_body"] = body
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return {
            "success": True,
            "data": {
                "step": "draft",
                "session_id": request.session_id,
                "title": title,
                "body": body,
                "feedback_applied": request.feedback
            },
            "processing_time_ms": processing_time
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===========================
# Step 3: Tuning
# ===========================

@app.post(f"{settings.API_PREFIX}/step3/tuning")
async def create_tuning(request: Step3TuningRequest):
    """Step 3: 페르소나별 메시지 생성 (선택한 페르소나만)"""
    start_time = time.time()
    
    try:
        # 모델 설정 추출
        provider, model = get_model_params(request.model_config_input)
        
        # 세션 확인
        session = sessions.get(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")
        
        messages_list = []
        
        # 선택된 페르소나만 처리
        for persona_id in request.personas:
            # 페르소나 정보 가져오기
            persona = DataService.find_persona(persona_id)
            if not persona:
                continue
            
            persona_info = PERSONA_INFO.get(persona_id, {"label": persona_id})
            
            # 프롬프트 생성
            messages = build_tuning_prompt(
                draft_title=request.draft.title,
                draft_body=request.draft.body,
                persona=persona,
                persona_label=persona_info["label"]
            )
            
            # LLM 호출 (모델 선택 지원)
            tuned_text = await llm_manager.generate(
                messages=messages,
                provider=provider,
                model=model,
                max_tokens=1024,
                temperature=0.7
            )
            
            # 제목/본문 파싱
            title, body = parse_title_body(tuned_text)
            
            messages_list.append({
                "persona": persona_id,
                "label": persona_info["label"],
                "color": persona_info.get("color", "#333"),
                "title": title,
                "body": body,
                "tone_keywords": persona.get("traits", [])[:3]
            })
        
        # 세션 업데이트
        session["tuned_messages"] = messages_list
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return {
            "success": True,
            "data": {
                "step": "tuning",
                "session_id": request.session_id,
                "messages": messages_list,
                "total_personas": len(messages_list),
                "model_used": {
                    "provider": provider or settings.LLM_PROVIDER,
                    "model": model
                }
            },
            "processing_time_ms": processing_time
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put(f"{settings.API_PREFIX}/step3/tuning/refine")
async def refine_tuning(request: Step3RefineRequest):
    """Step 3: 특정 페르소나 메시지 재생성"""
    start_time = time.time()
    
    try:
        # 모델 설정 추출
        provider, model = get_model_params(request.model_config_input)
        
        # 세션 확인
        session = sessions.get(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")
        
        persona_info = PERSONA_INFO.get(request.persona, {"label": request.persona})
        
        # 프롬프트 생성
        messages = build_tuning_refine_prompt(
            current_title=request.current_message.title,
            current_body=request.current_message.body,
            persona_label=persona_info["label"],
            feedback=request.feedback
        )
        
        # LLM 호출 (모델 선택 지원)
        tuned_text = await llm_manager.generate(
            messages=messages,
            provider=provider,
            model=model,
            max_tokens=1024,
            temperature=0.7
        )
        
        # 제목/본문 파싱
        title, body = parse_title_body(tuned_text)
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return {
            "success": True,
            "data": {
                "step": "tuning",
                "session_id": request.session_id,
                "persona": request.persona,
                "label": persona_info["label"],
                "title": title,
                "body": body,
                "feedback_applied": request.feedback
            },
            "processing_time_ms": processing_time
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===========================
# Helper Functions
# ===========================

def parse_title_body(text: str) -> tuple:
    """LLM 출력에서 [제목]과 [본문] 파싱 - 여러 패턴 지원"""
    import re
    
    # 1. 정규식 패턴들 (다양한 LLM 출력 형식 지원)
    patterns = [
        # [제목] / [본문] 형식
        r'\[제목\]\s*\n?(.*?)\n+\[본문\]\s*\n?(.*)',
        # **제목** / **본문** 형식
        r'\*\*제목\*\*[:\s]*\n?(.*?)\n+\*\*본문\*\*[:\s]*\n?(.*)',
        # 제목: / 본문: 형식
        r'제목[:\s]*\n?(.*?)\n+본문[:\s]*\n?(.*)',
        # Title: / Body: 형식
        r'[Tt]itle[:\s]*\n?(.*?)\n+[Bb]ody[:\s]*\n?(.*)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            title = match.group(1).strip()
            body = match.group(2).strip()
            # 불필요한 마크다운 제거
            title = re.sub(r'^[\*\#\-\s]+', '', title)
            body = re.sub(r'^[\*\#\-\s]+', '', body)
            # 끝에 불필요한 설명 제거 (--- 이후)
            body = re.split(r'\n---\n|\n\*\*', body)[0].strip()
            if title:
                return title, body
    
    # 2. 줄 단위 파싱 (fallback)
    title = ""
    body = ""
    lines = text.strip().split("\n")
    current_section = None
    
    for line in lines:
        line_stripped = line.strip()
        
        # 섹션 감지
        if "[제목]" in line_stripped or "제목:" in line_stripped:
            current_section = "title"
            content = re.sub(r'\[제목\]|제목[:\s]*', '', line_stripped).strip()
            if content:
                title = content
        elif "[본문]" in line_stripped or "본문:" in line_stripped:
            current_section = "body"
            content = re.sub(r'\[본문\]|본문[:\s]*', '', line_stripped).strip()
            if content:
                body = content
        elif line_stripped.startswith("---"):
            break  # 구분선 이후는 무시
        elif current_section == "title" and not title and line_stripped:
            title = line_stripped
        elif current_section == "body" and line_stripped:
            if body:
                body += "\n" + line_stripped
            else:
                body = line_stripped
    
    # 3. 최종 fallback: 첫 줄 = 제목, 나머지 = 본문
    if not title and not body:
        lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
        if lines:
            title = lines[0]
            body = "\n".join(lines[1:]) if len(lines) > 1 else ""
    
    return title, body


# ===========================
# Main Entry
# ===========================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
