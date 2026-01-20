"""
CRM Message Studio - FastAPI Backend
3단계 인터랙티브 파이프라인 API
"""

import sys
import argparse
from pathlib import Path
from threading import Lock

# 프로젝트 루트를 path에 추가하여 src 모듈 등을 찾을 수 있게 함
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import time
import uuid
from typing import Dict, Any, List, Union
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .config import settings
from .llm_provider import get_llm_provider
from .data_service import DataService, STAGE_ORDER, STAGE_KR, PERSONA_INFO
from .schemas import (
    Step1BriefRequest, Step1RefineRequest,
    Step2DraftRequest, Step2RefineRequest,
    Step3TuningRequest, Step3RefineRequest,
    ErrorResponse
)
from .prompts import (
    build_brief_prompt, build_brief_refine_prompt,
    build_draft_prompt, build_draft_refine_prompt,
    build_tuning_prompt, build_tuning_refine_prompt
)


# 세션 저장소 (메모리 기반, 프로덕션에서는 Redis 등 사용)
sessions: Dict[str, Dict[str, Any]] = {}

FRONTEND_DIR = ROOT_DIR / "frontend"
DATA_DIR = ROOT_DIR / "data"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작/종료 이벤트"""
    print(f"🚀 CRM Message Studio API 시작")
    print(f"   LLM Provider: {settings.LLM_PROVIDER}")
    print(f"   Ollama Host: {settings.OLLAMA_HOST}")
    print(f"   Ollama Model: {settings.OLLAMA_MODEL}")
    yield
    print("👋 API 종료")


app = FastAPI(
    title="CRM Message Studio API",
    description="3단계 인터랙티브 CRM 메시지 생성 파이프라인",
    version="1.0.0",
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

# LLM Provider는 요청마다 모델명에 맞춰 생성합니다.

class GenerateRequest(BaseModel):
    persona: Union[int, str]
    brand: str
    product: str
    stage_index: int
    style_index: int
    is_event: int = 0
    top_k: int = 3
    stage1_model: str = "Qwen/Qwen2.5-1.5B-Instruct"
    stage2_model: str = "LGAI-EXAONE/EXAONE-4.0-1.2B"
    disable_cache: bool = False
    n: int = 1


class BatchRequest(BaseModel):
    items: List[GenerateRequest]
    disable_cache: bool = False


_PIPELINE_LOCK = Lock()
_PIPELINE_CONTEXT = {}


def _get_context(stage1_model: str, stage2_model: str, disable_cache: bool):
    import run_qwen_exaone_pipeline as pipeline
    if disable_cache:
        if hasattr(pipeline, "_set_cache_enabled"):
            pipeline._set_cache_enabled(False)
        if hasattr(pipeline, "load_json") and hasattr(pipeline.load_json, "cache_clear"):
            pipeline.load_json.cache_clear()
        return {"data": None, "q_generator": None, "exa_generator": None}

    if hasattr(pipeline, "_set_cache_enabled"):
        pipeline._set_cache_enabled(True)

    key = (stage1_model, stage2_model)
    with _PIPELINE_LOCK:
        cached = _PIPELINE_CONTEXT.get(key)
        if cached:
            return cached
        base = Path(pipeline.__file__).resolve().parent.parent
        data = pipeline._load_data(str(base))
        from llm_utils import get_llm_generator
        gen1 = get_llm_generator(stage1_model)
        gen2 = get_llm_generator(stage2_model)
        cached = {"data": data, "gen1": gen1, "gen2": gen2}
        _PIPELINE_CONTEXT[key] = cached
        return cached


async def _run_pipeline(req: GenerateRequest):
    import run_qwen_exaone_pipeline as pipeline
    args = argparse.Namespace(
        persona=req.persona,
        brand=req.brand,
        product=req.product,
        stage_index=req.stage_index,
        style_index=req.style_index,
        is_event=req.is_event,
        top_k=req.top_k,
        stage1_model=req.stage1_model,
        stage2_model=req.stage2_model,
        out_path=None,
        batch_json=None,
        disable_cache=req.disable_cache,
    )
    ctx = _get_context(req.stage1_model, req.stage2_model, req.disable_cache)
    return await pipeline._run_pipeline(
        args,
        data=ctx.get("data"),
        gen1=ctx.get("gen1"),
        gen2=ctx.get("gen2"),
    )


# ===========================
# Health Check
# ===========================

@app.get("/health")
async def health_check():
    return {"status": "ok", "model": settings.OLLAMA_MODEL}

@app.post("/generate")
async def generate(req: GenerateRequest):
    try:
        if req.n <= 1:
            result = await _run_pipeline(req)
            return {"result": result}
        results = []
        for _ in range(req.n):
            results.append(await _run_pipeline(req))
        return {"results": results}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/generate_batch")
async def generate_batch(req: BatchRequest):
    try:
        results = []
        for item in req.items:
            if req.disable_cache:
                item.disable_cache = True
            results.append(await _run_pipeline(item))
        return {"results": results}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ===========================
# Step 1: Brief
# ===========================

@app.post(f"{settings.API_PREFIX}/step1/brief")
async def create_brief(request: Step1BriefRequest):
    """Step 1: 마케팅 브리프 생성"""
    start_time = time.time()
    
    try:
        # 제품 검색
        product = DataService.find_product(request.brand_name, request.product_name)
        if not product:
            raise HTTPException(status_code=404, detail=f"제품을 찾을 수 없습니다: {request.brand_name} - {request.product_name}")
        
        # 브랜드 스토리
        brand_story = DataService.get_brand_story(request.brand_name)
        
        # CRM 목표
        crm_goal = DataService.get_crm_goal(request.stage_index)
        
        # 스테이지 정보
        stage_name = STAGE_ORDER[request.stage_index] if 0 <= request.stage_index < len(STAGE_ORDER) else "Acquisition"
        stage_kr = STAGE_KR[request.stage_index] if 0 <= request.stage_index < len(STAGE_KR) else "획득"
        
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
        
        # LLM 호출
        llm = get_llm_provider(request.model_name)
        brief_text = await llm.generate(messages, max_tokens=1024, temperature=0.7)
        
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
            "brief_text": brief_text,
            "model_name": request.model_name
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
                "stage_kr": stage_kr
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
        # 세션 확인
        session = sessions.get(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")
        
        # 프롬프트 생성
        messages = build_brief_refine_prompt(request.current_brief, request.feedback)
        
        # LLM 호출
        model_name = session.get("model_name")
        llm = get_llm_provider(model_name)
        brief_text = await llm.generate(messages, max_tokens=1024, temperature=0.7)
        
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
        
        # LLM 호출
        llm = get_llm_provider(request.model_name)
        draft_text = await llm.generate(messages, max_tokens=1024, temperature=0.7)
        
        # 제목/본문 파싱
        title, body = parse_title_body(draft_text)
        
        # 세션 업데이트
        session["draft_title"] = title
        session["draft_body"] = body
        session["model_name"] = request.model_name
        
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
                "brand_tone": brand_story.get("tone_keywords", [])
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
        
        # LLM 호출
        model_name = session.get("model_name")
        llm = get_llm_provider(model_name)
        draft_text = await llm.generate(messages, max_tokens=1024, temperature=0.7)
        
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
    """Step 3: 페르소나별 메시지 생성"""
    start_time = time.time()
    
    try:
        # 세션 확인
        session = sessions.get(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")
        
        messages_list = []
        
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
            
            # LLM 호출
            llm = get_llm_provider(request.model_name)
            tuned_text = await llm.generate(messages, max_tokens=1024, temperature=0.7)
            
            # 제목/본문 파싱
            title, body = parse_title_body(tuned_text)
            if not body:
                body = request.draft.body
            
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
                "total_personas": len(messages_list)
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
        
        # LLM 호출
        llm = get_llm_provider(request.model_name)
        tuned_text = await llm.generate(messages, max_tokens=1024, temperature=0.7)
        
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
    """LLM 출력에서 [제목]과 [본문] 파싱"""
    title = ""
    body = ""
    
    raw = (text or "").strip()
    if not raw:
        return title, body
    # JSON 우선 파싱
    if raw.startswith("{") and raw.endswith("}"):
        try:
            import json
            data = json.loads(raw)
            if isinstance(data, dict):
                title = str(data.get("title", "")).strip()
                body = str(data.get("body", "")).strip()
                return title, body
        except Exception:
            pass

    # Normalize line breaks and strip bullet markers
    lines = [line.strip() for line in raw.replace("\r\n", "\n").split("\n") if line.strip()]
    current_section = None
    
    for line in lines:
        line_stripped = line.strip()
        
        if "[제목]" in line_stripped:
            current_section = "title"
            # 같은 줄에 내용이 있는 경우
            content = line_stripped.replace("[제목]", "").strip()
            if content:
                title = content
        elif "[본문]" in line_stripped:
            current_section = "body"
            content = line_stripped.replace("[본문]", "").strip()
            if content:
                body = content
        elif current_section == "title" and not title:
            title = line_stripped
        elif current_section == "body":
            if body:
                body += "\n" + line_stripped
            else:
                body = line_stripped

    # 추가 포맷 대응: "제목:", "본문:" 라벨
    if not title or not body:
        title_line = ""
        body_lines = []
        found_body = False
        for line in lines:
            if line.startswith("제목:"):
                title_line = line.replace("제목:", "").strip()
                continue
            if line.startswith("본문:"):
                found_body = True
                content = line.replace("본문:", "").strip()
                if content:
                    body_lines.append(content)
                continue
            if found_body:
                body_lines.append(line)
        if not title and title_line:
            title = title_line
        if not body and body_lines:
            body = "\n".join(body_lines).strip()

    # 라벨/헤더 텍스트 제거
    if body:
        cleaned = []
        for line in body.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue
            if stripped in ("[제목]", "[본문]"):
                continue
            if stripped.startswith("제목") or stripped.startswith("본문"):
                continue
            cleaned.append(stripped)
        body = "\n".join(cleaned).strip()

    # 파싱 실패 시: 첫 줄을 제목, 나머지를 본문으로
    if not body:
        if lines:
            if not title:
                title = lines[0]
                body = "\n".join(lines[1:]).strip()
            else:
                body = "\n".join(lines).strip()
        else:
            body = raw
    
    return title, body


# ===========================
# Main Entry
# ===========================

app.mount("/data", StaticFiles(directory=str(DATA_DIR)), name="data")
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
