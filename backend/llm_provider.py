"""
LLM Provider 추상화
- BaseLLMProvider: 추상 베이스 클래스
- OllamaProvider: Ollama API 호출 구현
- OpenRouterProvider: OpenRouter API 호출 구현 (다양한 모델 지원)
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
        model: str = None,
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
        model: str = None,
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
        self.default_model = model or os.getenv("OLLAMA_MODEL", "llama3.2")
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
        model: str = None,
        **kwargs
    ) -> str:
        """비동기 메시지 생성"""
        use_model = model or self.default_model
        
        payload = {
            "model": use_model,
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
        model: str = None,
        **kwargs
    ) -> str:
        """동기 메시지 생성"""
        use_model = model or self.default_model
        
        payload = {
            "model": use_model,
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


class OpenRouterProvider(BaseLLMProvider):
    """OpenRouter API Provider - 다양한 LLM 모델 지원"""
    
    def __init__(
        self,
        api_key: str = None,
        base_url: str = None,
        default_model: str = None,
        timeout: float = 120.0,
        site_url: str = "http://localhost:3000",
        site_name: str = "CRM Message Studio"
    ):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY", "")
        self.base_url = base_url or os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        self.default_model = default_model or os.getenv("OPENROUTER_DEFAULT_MODEL", "anthropic/claude-3.5-sonnet")
        self.timeout = timeout
        self.site_url = site_url
        self.site_name = site_name
        
        # API endpoint
        self.chat_endpoint = f"{self.base_url}/chat/completions"
        
        # Headers
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": self.site_url,
            "X-Title": self.site_name
        }
    
    async def generate(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1024,
        temperature: float = 0.7,
        model: str = None,
        **kwargs
    ) -> str:
        """비동기 메시지 생성"""
        use_model = model or self.default_model
        
        payload = {
            "model": use_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                self.chat_endpoint,
                json=payload,
                headers=self.headers
            )
            response.raise_for_status()
            result = response.json()
            
            # OpenAI 호환 응답 형식
            return result.get("choices", [{}])[0].get("message", {}).get("content", "")
    
    def generate_sync(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1024,
        temperature: float = 0.7,
        model: str = None,
        **kwargs
    ) -> str:
        """동기 메시지 생성"""
        use_model = model or self.default_model
        
        payload = {
            "model": use_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                self.chat_endpoint,
                json=payload,
                headers=self.headers
            )
            response.raise_for_status()
            result = response.json()
            
            return result.get("choices", [{}])[0].get("message", {}).get("content", "")


class LLMProviderManager:
    """여러 Provider를 관리하고 동적으로 선택할 수 있는 매니저"""
    
    def __init__(self):
        self._providers: Dict[str, BaseLLMProvider] = {}
        self._initialize_providers()
    
    def _initialize_providers(self):
        """환경에 따라 사용 가능한 Provider 초기화"""
        # Ollama는 항상 시도
        try:
            self._providers["ollama"] = OllamaProvider()
        except Exception as e:
            print(f"Ollama provider 초기화 실패: {e}")
        
        # OpenRouter는 API 키가 있을 때만
        openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
        if openrouter_key:
            try:
                self._providers["openrouter"] = OpenRouterProvider()
            except Exception as e:
                print(f"OpenRouter provider 초기화 실패: {e}")
    
    def get_provider(self, provider_type: str = None) -> BaseLLMProvider:
        """Provider 타입으로 가져오기"""
        provider_type = provider_type or os.getenv("LLM_PROVIDER", "ollama")
        
        if provider_type not in self._providers:
            # Fallback: 첫 번째 사용 가능한 provider
            if self._providers:
                return list(self._providers.values())[0]
            raise ValueError(f"No LLM provider available. Requested: {provider_type}")
        
        return self._providers[provider_type]
    
    def get_available_providers(self) -> List[str]:
        """사용 가능한 Provider 목록"""
        return list(self._providers.keys())
    
    async def generate(
        self,
        messages: List[Dict[str, str]],
        provider: str = None,
        model: str = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """Provider와 Model을 지정하여 생성"""
        llm = self.get_provider(provider)
        return await llm.generate(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            model=model,
            **kwargs
        )


# 싱글톤 매니저 인스턴스
_llm_manager: Optional[LLMProviderManager] = None


def get_llm_manager() -> LLMProviderManager:
    """LLM Provider Manager 싱글톤 가져오기"""
    global _llm_manager
    if _llm_manager is None:
        _llm_manager = LLMProviderManager()
    return _llm_manager


def get_llm_provider(provider_type: str = None) -> BaseLLMProvider:
    """LLM Provider 팩토리 함수 (하위 호환성)"""
    return get_llm_manager().get_provider(provider_type)
