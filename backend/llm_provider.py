"""
LLM Provider 추상화
- BaseLLMProvider: 추상 베이스 클래스
- ModelAgnosticProvider: 통합 LLM 제너레이터 호출 구현
"""

import os
import httpx
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
from src.llm_utils import get_llm_generator


class BaseLLMProvider(ABC):
    """LLM Provider 추상 베이스 클래스"""
    
    @abstractmethod
    async def generate(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1024,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """메시지 기반 텍스트 생성"""
        pass
    
    @abstractmethod
    def generate_sync(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1024,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """동기 버전 텍스트 생성"""
        pass


class ModelAgnosticProvider(BaseLLMProvider):
    """llm_utils를 사용하여 다양한 모델을 지원하는 Provider"""
    
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.generator = get_llm_generator(model_name)
    
    async def generate(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1024,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        # generator.generate()는 [{role, content}] 형식을 인자로 받음
        return await self.generator.generate(messages)
    
    def generate_sync(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1024,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        # 동기 호출은 generator의 generate가 async이므로 래핑 필요할 수 있지만, 
        # 여기서는 단순히 generator 인터페이스를 따름
        import asyncio
        import nest_asyncio
        nest_asyncio.apply()
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.generator.generate(messages))


def get_llm_provider(model_name: str = None) -> BaseLLMProvider:
    """LLM Provider 팩토리 함수"""
    model_name = model_name or os.getenv("OLLAMA_MODEL", "Qwen/Qwen2.5-1.5B-Instruct")
    return ModelAgnosticProvider(model_name)
