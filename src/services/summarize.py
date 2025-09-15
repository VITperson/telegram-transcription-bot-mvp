from __future__ import annotations

from typing import Literal
from tenacity import retry, stop_after_attempt, wait_exponential
from src.core.config import get_settings

Mode = Literal["summary", "keypoints"]


class SummarizationProvider:
    def __init__(self) -> None:
        self.settings = get_settings()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    def summarize(self, text: str, mode: Mode, language: str | None) -> str | list[str]:
        if not self.settings.OPENAI_API_KEY:
            # No API key -> return simple fallback
            if mode == "summary":
                return text[:1000]
            else:
                return [line.strip() for line in text.split(".") if line.strip()][:5]

        from openai import OpenAI, BadRequestError
        client = OpenAI(api_key=self.settings.OPENAI_API_KEY)
        prompt = (
            "Summarize the text" if mode == "summary" else "Extract 5-10 key bullet points from the text"
        )
        if language and language != "auto":
            prompt += f" in {language}"
        prompt += ":\n\n" + text[:12000]
        req = {
            "model": self.settings.OPENAI_MODEL,
            "messages": [{"role": "user", "content": prompt}],
        }
        # Add temperature if configured; some models only support default (1) and will reject it.
        if self.settings.OPENAI_TEMPERATURE is not None:
            req["temperature"] = float(self.settings.OPENAI_TEMPERATURE)

        try:
            resp = client.chat.completions.create(**req)  # type: ignore[arg-type]
        except BadRequestError as e:
            # Retry once without temperature if the model does not support custom sampling params
            msg = getattr(e, "message", str(e))
            if "temperature" in msg and "Only the default" in msg:
                req.pop("temperature", None)
                resp = client.chat.completions.create(**req)  # type: ignore[arg-type]
            else:
                raise
        content = resp.choices[0].message.content or ""
        if mode == "summary":
            return content.strip()
        # keypoints: split into lines stripping bullets
        bullets = []
        for line in content.splitlines():
            line = line.strip().lstrip("-•*").strip()
            if line:
                bullets.append(line)
        return bullets
