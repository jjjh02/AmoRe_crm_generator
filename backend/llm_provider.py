"""
LLM Provider 추상화
- BaseLLMProvider: 추상 베이스 클래스
- OllamaProvider: Ollama API 호출 구현
- 추후 OpenAIProvider, ClaudeProvider 등 확장 가능
"""

import os
import httpx
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


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


class OllamaProvider(BaseLLMProvider):
    """Ollama API Provider"""
    
    def __init__(
        self,
        host: str = None,
        model: str = None,
        api_key: str = None,
        timeout: float = 120.0
    ):
        self.host = host or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.model = model or os.getenv("OLLAMA_MODEL", "llama3.2")
        self.api_key = api_key or os.getenv("OLLAMA_API_KEY")
        self.timeout = timeout
        
        # API endpoint
        self.chat_endpoint = f"{self.host}/api/chat"
        
        # Headers
        self.headers = {"Content-Type": "application/json"}
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"
    
    async def generate(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1024,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """비동기 메시지 생성"""
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature
            }
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                self.chat_endpoint,
                json=payload,
                headers=self.headers
            )
            response.raise_for_status()
            result = response.json()
            
            # Ollama 응답 형식: {"message": {"role": "assistant", "content": "..."}}
            return result.get("message", {}).get("content", "")
    
    def generate_sync(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1024,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """동기 메시지 생성"""
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature
            }
        }
        
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                self.chat_endpoint,
                json=payload,
                headers=self.headers
            )
            response.raise_for_status()
            result = response.json()
            
            return result.get("message", {}).get("content", "")


def get_llm_provider(provider_type: str = None) -> BaseLLMProvider:
    """LLM Provider 팩토리 함수"""
    provider_type = provider_type or os.getenv("LLM_PROVIDER", "ollama")
    
    if provider_type == "ollama":
        return OllamaProvider()
    else:
        raise ValueError(f"Unknown LLM provider: {provider_type}")
