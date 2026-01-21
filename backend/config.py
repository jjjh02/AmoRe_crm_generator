"""
Configuration management
"""

import os
from pathlib import Path
from typing import Dict, List
from dotenv import load_dotenv

# .env 파일 로드
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Settings:
    # LLM Provider (default)
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "ollama")
    
    # Ollama Settings
    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2")
    OLLAMA_API_KEY: str = os.getenv("OLLAMA_API_KEY", "")
    
    # OpenRouter Settings
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_DEFAULT_MODEL: str = os.getenv("OPENROUTER_DEFAULT_MODEL", "anthropic/claude-3.5-sonnet")
    
    # Data paths
    DATA_DIR: Path = BASE_DIR / "data"
    
    # API settings
    API_PREFIX: str = "/api/v1"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # Available Models Configuration
    AVAILABLE_MODELS: Dict[str, List[Dict]] = {
        "ollama": [
            {"id": "llama3.2", "name": "Llama 3.2", "description": "Meta의 최신 경량 모델"},
            {"id": "llama3.1", "name": "Llama 3.1", "description": "Meta의 고성능 모델"},
            {"id": "qwen2.5", "name": "Qwen 2.5", "description": "Alibaba의 다국어 모델"},
            {"id": "gemma2", "name": "Gemma 2", "description": "Google의 경량 오픈 모델"},
        ],
        "openrouter": [
            {"id": "anthropic/claude-3.5-sonnet", "name": "Claude 3.5 Sonnet", "description": "Anthropic의 최고 성능 모델"},
            {"id": "anthropic/claude-3-haiku", "name": "Claude 3 Haiku", "description": "빠르고 경제적인 모델"},
            {"id": "openai/gpt-4o", "name": "GPT-4o", "description": "OpenAI의 최신 멀티모달 모델"},
            {"id": "openai/gpt-4o-mini", "name": "GPT-4o Mini", "description": "빠르고 저렴한 모델"},
            {"id": "google/gemini-pro-1.5", "name": "Gemini Pro 1.5", "description": "Google의 고성능 모델"},
            {"id": "meta-llama/llama-3.1-70b-instruct", "name": "Llama 3.1 70B", "description": "Meta의 대형 오픈 모델"},
            {"id": "qwen/qwen-2.5-72b-instruct", "name": "Qwen 2.5 72B", "description": "Alibaba의 대형 모델"},
        ]
    }


settings = Settings()
