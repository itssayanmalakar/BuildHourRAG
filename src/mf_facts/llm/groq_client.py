from __future__ import annotations

from groq import Groq

from mf_facts.llm.base import LLMResult


class GroqLLM:
    def __init__(self, api_key: str, model: str, temperature: float = 0.0,
                 max_tokens: int = 350, timeout_s: int = 20, max_retries: int = 1):
        self.client = Groq(api_key=api_key, timeout=timeout_s)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.max_retries = max_retries

    def complete(self, system: str, user: str) -> LLMResult:
        last: Exception | None = None
        for _ in range(self.max_retries + 1):
            try:
                resp = self.client.chat.completions.create(
                    model=self.model,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                )
                usage = resp.usage
                return LLMResult(
                    text=resp.choices[0].message.content or "",
                    input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
                    output_tokens=getattr(usage, "completion_tokens", 0) or 0,
                    model=self.model,
                )
            except Exception as exc:  # noqa: BLE001 - retried below
                last = exc
        raise RuntimeError(f"LLM call failed: {last}")
