---
license: apache-2.0
task_categories:
- reinforcement-learning
- text-generation
language:
- ko
- en
tags:
- dpo
- preference-learning
- crm
- alignment
- trl
---
# AmoRe CRM DPO Dataset

이 데이터셋은 **CRM 메시지 생성 모델을 위한 Direct Preference Optimization (DPO)** 학습용 선호 데이터셋입니다.
각 샘플은 동일한 프롬프트에 대해 **더 나은 응답(chosen)** 과 **덜 나은 응답(rejected)** 의 쌍으로 구성되어 있습니다.

---

## 📌 Dataset Structure

각 샘플은 다음 JSON 형식을 따릅니다:

```json
{
  "prompt": "<사용자 상황 / 페르소나 / 목표>",
  "chosen": "<더 적합한 CRM 메시지>",
  "rejected": "<덜 적합한 CRM 메시지>",
  "best_index": "<더 적합한 CRM 인덱스>",
  "rejected_index": "<덜 적합한 CRM 인덱스>",
  "reason_best": "<더 적합한 이유>",
  "reason_rejected": "<덜 적합한 이유>"
}
```

prompt: 사용자 맥락, 페르소나, 캠페인 목적 등을 포함

chosen: 목표(AARRR 단계, 감성 적합도 등)에 더 부합하는 응답

rejected: 상대적으로 품질이 낮거나 목적과 어긋나는 응답

## 🎯 Purpose

본 데이터셋은 다음 목적을 위해 설계되었습니다:

* CRM 메시지 **감성 적합도 향상**
* AARRR 단계별 메시지 품질 정렬
* 소형 생성 모델(≈2B)을 강한 기준 모델의 선호에 맞게 정렬
* **SFT 이후 단계의 alignment 학습**

---

## 🧠 Generation & Labeling

* 응답은 **사전 학습된 LLM**을 사용해 생성
* 선호(chosen / rejected)는
  * 메시지 감성
  * CTA 명확성
  * CRM 목적 부합도
  * 사용자 관점 설득력

    을 기준으로 비교 평가됨

> ⚠️ 이 데이터셋은 **offline preference dataset**이며,
>
> DPO 학습 중 외부 API 호출 없이 사용되는 것을 전제로 합니다.

---

## 🏗 Recommended Usage

### Load with 🤗 Datasets

<pre class="overflow-visible! px-0!" data-start="1205" data-end="1337"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-[calc(--spacing(9)+var(--header-height))] @w-xl/main:top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-python"><span><span>from</span><span> datasets </span><span>import</span><span> load_dataset

dataset = load_dataset(</span><span>"YOUR_ID/AmoRe-crm-dpo-dataset"</span><span>)
train_ds = dataset[</span><span>"train"</span><span>]
</span></span></code></div></div></pre>

### DPO Training (TRL)

<pre class="overflow-visible! px-0!" data-start="1362" data-end="1402"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-[calc(--spacing(9)+var(--header-height))] @w-xl/main:top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-python"><span><span>from</span><span> trl </span><span>import</span><span> DPOTrainer
</span></span></code></div></div></pre>

* `prompt`, `chosen`, `rejected` 컬럼명을 그대로 사용해야 합니다.
* `prompt + response` 길이가 `max_seq_length`를 초과하지 않도록 주의하세요.

---

## 🔗 Related Models

* **Base Model** : `LGAI-EXAONE/EXAONE-4.0-1.2B`
* **Training Method** : DPO + LoRA (PEFT)
* **Framework** : Hugging Face TRL

---

## ⚠️ Notes

* 본 데이터셋은 연구 및 실험 목적을 위해 제공됩니다.
* 실제 서비스 적용 시 추가적인 검증이 필요합니다.
* CRM 도메인 특성상 일부 표현은 의도적으로 감성적으로 설계되었습니다.

---

## 📜 License

Apache 2.0
