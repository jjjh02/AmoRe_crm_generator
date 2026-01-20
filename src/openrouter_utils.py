import os
import json
import time
import httpx
from dotenv import load_dotenv

load_dotenv()

class OpenRouterGenerator:
    """OpenRouter API를 사용하여 마케팅 초안 또는 톤 보정을 수행합니다."""
    
    def __init__(self, model_name="google/gemini-2.0-flash-exp:free"):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.model_name = model_name
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        
        if not self.api_key:
            print("[WARN] OPENROUTER_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")

    async def _call_api(self, messages, max_tokens=1024, temperature=0.1):
        if not self.api_key:
            return "Error: OPENROUTER_API_KEY missing", 0.0

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/jinsuhhur/Amore_crm_generator",
            "X-Title": "Amore CRM Generator",
        }

        payload = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        start_time = time.time()
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(self.base_url, headers=headers, json=payload)
                response.raise_for_status()
                res_json = response.json()
                
                content = res_json["choices"][0]["message"]["content"]
                duration = time.time() - start_time
                return content.strip(), duration
        except Exception as e:
            print(f"[OpenRouter Error] {e}")
            return f"Error: {str(e)}", time.time() - start_time

    async def generate(self, messages, max_tokens=1024, temperature=0.4):
        """ExaoneToneCorrector.generate 와 인터페이스 호환용 (text만 반환)"""
        content, _ = await self._call_api(messages, max_tokens, temperature)
        return content

    async def generate_marketing_draft(self, brand_name, product_name, persona, reviews, highlights, campaign_event_info=None):
        """LocalQwenGenerator.generate_marketing_draft 와 인터페이스 호환용 (draft, duration 반환)"""
        # Prompt building logic copied from LocalQwenGenerator for independence
        persona_traits = ", ".join(persona.get("traits", []) if isinstance(persona.get("traits"), list) else [])
        if reviews and isinstance(reviews[0], dict):
            review_text = "\n".join([f"- {r.get('text', '')[:150]}" for r in reviews[:3]])
        else:
            review_text = "\n".join([f"- {str(r)[:150]}" for r in reviews[:3]])
        highlights_text = "\n".join([f"- {h}" for h in highlights[:3]])

        event_section = ""
        if campaign_event_info:
            event_section = f"""
[캠페인/이벤트 정보]
이벤트명: {campaign_event_info.get('name', '')}
상세 내용: {campaign_event_info.get('detail', '')}
"""

        prompt = f"""당신은 마케팅 카피라이터입니다. 아래 정보를 바탕으로 마케팅 초안을 작성하세요.

[제품]
브랜드: {brand_name}
제품명: {product_name}

[타겟 페르소나]
특성: {persona_traits}
주요 관심사: {persona.get('value_focus', '제품 품질')}
{event_section}
[고객 리뷰 요약]
{review_text}

[핵심 포인트]
{highlights_text}

작성 규칙:
1. 반드시 다음 형식을 따르세요:

[제목]
(간결하고 임팩트 있게, 30~40자)

[본문]
(페르소나 공감과 제품 효과 중심, 200~300자)

2. 리뷰에서 확인 가능한 사실만 사용하세요.
3. 숫자, 할인율, 이벤트명은 절대 사용하지 마세요. 
4. 단, [캠페인/이벤트 정보]가 제공된 경우 해당 내용은 적극 활용하세요
5. 페르소나의 가치관을 반영하되, 페르소나 이름(고객군명)은 절대 직접 언급하지 마세요.
6. 고객을 "당신", "이 제품을 원하는 분들" 등으로 표현하세요.
"""
        messages = [
            {"role": "system", "content": f"{persona.get('name', '고객')} 페르소나를 위한 마케팅 전문가입니다."},
            {"role": "user", "content": prompt}
        ]
        
        return await self._call_api(messages, max_tokens=1024, temperature=0.1)

    async def generate_text(self, messages, max_tokens=1024, temperature=0.1):
        """LocalQwenGenerator.generate_text 와 인터페이스 호환용"""
        return await self._call_api(messages, max_tokens, temperature)
