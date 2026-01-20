import os
import torch
import time
from transformers import AutoModelForCausalLM, AutoTokenizer
try:
    from .openrouter_utils import OpenRouterGenerator
except (ImportError, ValueError):
    from openrouter_utils import OpenRouterGenerator

def get_device():
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"

class LocalHFGenerator:
    """HuggingFace 로컬 모델을 위한 범용 제너레이터"""
    _CACHE = {}

    def __init__(self, model_name, use_cache=True):
        self.model_name = model_name
        self.device = get_device()
        
        if use_cache and model_name in self._CACHE:
            self.tokenizer = self._CACHE[model_name]["tokenizer"]
            self.model = self._CACHE[model_name]["model"]
            return

        print(f"[Local HF] 로딩 중: {model_name} ({self.device})")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        dtype = torch.float16 if self.device == "cuda" else torch.float32
        kwargs = {"trust_remote_code": True, "torch_dtype": dtype}
        if self.device == "cuda":
            kwargs["device_map"] = "auto"
        
        self.model = AutoModelForCausalLM.from_pretrained(model_name, **kwargs)
        self.model.eval()

        if use_cache:
            self._CACHE[model_name] = {"tokenizer": self.tokenizer, "model": self.model}

    async def generate(self, messages, max_tokens=512, temperature=0.1):
        try:
            input_text = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        except:
            input_text = "\n".join([f"{m['role']}: {m['content']}" for m in messages])

        inputs = self.tokenizer(input_text, return_tensors="pt", truncation=True, max_length=4096).to(self.device)
        
        with torch.inference_mode():
            output_ids = self.model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=temperature,
                top_p=0.9,
                do_sample=True if temperature > 0 else False,
                pad_token_id=self.tokenizer.pad_token_id
            )
        
        generated_ids = output_ids[0][inputs['input_ids'].shape[1]:]
        return self.tokenizer.decode(generated_ids, skip_special_tokens=True).strip()

def get_llm_generator(model_name, use_cache=True):
    """모델 이름에 따라 로컬 또는 원격 제너레이터를 반환하는 팩토리 함수"""
    # OpenRouter 판별:
    # - OpenRouter 모델은 보통 suffix로 :free 같은 태그를 붙임
    # - ':'가 있으면 무조건 OpenRouter로 간주 (로컬 HF 모델명에는 보통 사용되지 않음)
    is_openrouter = (":" in model_name) or (
        "/" in model_name and
        not any(model_name.startswith(p) for p in ["Qwen/", "LGAI-EXAONE/", "meta-llama/"])
    )
    
    if is_openrouter:
        print(f"[Factory] OpenRouter 사용: {model_name}")
        return OpenRouterGenerator(model_name=model_name)
    else:
        print(f"[Factory] 로컬 HF 사용: {model_name}")
        # 특정 모델용 커스텀 클래스가 필요하다면 여기서 분기 가능하지만, 
        # 대부분은 LocalHFGenerator로 통합 가능합니다.
        return LocalHFGenerator(model_name=model_name, use_cache=use_cache)
