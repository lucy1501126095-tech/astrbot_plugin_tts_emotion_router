# -*- coding: utf-8 -*-
"""Language-based TTS router. Routes to different providers based on text language."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# CJK Unicode ranges
_CJK_RE = re.compile(
    r"[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff"
    r"\U00020000-\U0002a6df\U0002a700-\U0002b73f"
    r"\U0002b740-\U0002b81f\U0002b820-\U0002ceaf"
    r"\U0002ceb0-\U0002ebef\U00030000-\U0003134f]"
)


def chinese_ratio(text: str) -> float:
    """Return the ratio of Chinese characters in text (0.0 ~ 1.0)."""
    if not text:
        return 0.0
    # Strip whitespace and punctuation for a fairer count
    chars = re.sub(r"\s+", "", text)
    if not chars:
        return 0.0
    cn_count = len(_CJK_RE.findall(chars))
    return cn_count / len(chars)


class LanguageRouterTTS:
    """Routes TTS requests to different providers based on detected language.

    Chinese text -> chinese_provider (e.g. MiniMax)
    Non-Chinese text -> other_provider (e.g. ElevenLabs)
    """

    def __init__(
        self,
        chinese_provider: Any,
        other_provider: Any,
        threshold: float = 0.5,
    ):
        """
        Args:
            chinese_provider: TTS provider for Chinese text.
            other_provider: TTS provider for non-Chinese text.
            threshold: Chinese character ratio threshold (0~1).
                       Above this -> chinese_provider, below -> other_provider.
        """
        self.chinese_provider = chinese_provider
        self.other_provider = other_provider
        self.threshold = threshold

    async def close(self):
        for provider in (self.chinese_provider, self.other_provider):
            if provider is not None:
                try:
                    await provider.close()
                except Exception:
                    pass

    def _pick_provider(self, text: str) -> Any:
        ratio = chinese_ratio(text)
        if ratio >= self.threshold:
            logger.info("LanguageRouter: Chinese ratio %.2f >= %.2f -> chinese_provider", ratio, self.threshold)
            return self.chinese_provider
        else:
            logger.info("LanguageRouter: Chinese ratio %.2f < %.2f -> other_provider", ratio, self.threshold)
            return self.other_provider

    async def synth(
        self,
        text: str,
        voice: str,
        out_dir: Path,
        speed: Optional[float] = None,
        *,
        emotion: Optional[str] = None,
    ) -> Optional[Path]:
        provider = self._pick_provider(text)
        return await provider.synth(
            text,
            voice,
            out_dir,
            speed=speed,
            emotion=emotion,
        )
