# -*- coding: utf-8 -*-
"""ElevenLabs TTS provider for AstrBot TTS plugin."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from pathlib import Path
from typing import Optional

import aiohttp

from ..utils.audio import validate_audio_file

logger = logging.getLogger(__name__)


class ElevenLabsTTS:
    def __init__(
        self,
        api_key: str,
        voice_id: str,
        *,
        model_id: str = "eleven_v3",
        api_url: str = "https://api.elevenlabs.io",
        stability: float = 0.5,
        similarity_boost: float = 0.75,
        style: float = 0.0,
        use_speaker_boost: bool = True,
        output_format: str = "mp3_44100_128",
        max_retries: int = 2,
        timeout: int = 60,
    ):
        self.api_key = api_key.strip()
        self.voice_id = voice_id.strip()
        self.model_id = model_id or "eleven_v3"
        self.api_url = api_url.rstrip("/")
        self.stability = float(stability)
        self.similarity_boost = float(similarity_boost)
        self.style = float(style)
        self.use_speaker_boost = bool(use_speaker_boost)
        self.output_format = output_format or "mp3_44100_128"
        self.max_retries = max(0, int(max_retries))
        self.timeout = max(5, int(timeout))
        self._session: Optional[aiohttp.ClientSession] = None

        # Determine file extension from output_format
        fmt = self.output_format.lower()
        if fmt.startswith("mp3"):
            self._ext = "mp3"
        elif fmt.startswith("pcm"):
            self._ext = "wav"
        elif fmt.startswith("ulaw"):
            self._ext = "wav"
        else:
            self._ext = "mp3"

    async def close(self):
        if self._session:
            await self._session.close()
            self._session = None

    async def _ensure_session(self):
        if self._session is None or self._session.closed:
            client_timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(timeout=client_timeout)

    @staticmethod
    async def _write_bytes(path: Path, content: bytes) -> None:
        def _write():
            with open(path, "wb") as f:
                f.write(content)
        await asyncio.to_thread(_write)

    async def synth(
        self,
        text: str,
        voice: str,
        out_dir: Path,
        speed: Optional[float] = None,
        *,
        emotion: Optional[str] = None,
    ) -> Optional[Path]:
        """Synthesize text to speech using ElevenLabs API.

        Args:
            text: Text to synthesize.
            voice: Voice ID override (uses self.voice_id if empty).
            out_dir: Directory to save audio file.
            speed: Not used by ElevenLabs (ignored).
            emotion: Not used by ElevenLabs (ignored, v3 uses audio tags).

        Returns:
            Path to generated audio file, or None on failure.
        """
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        if not self.api_key:
            logger.error("ElevenLabsTTS: missing api key")
            return None

        effective_voice = voice or self.voice_id
        if not effective_voice:
            logger.error("ElevenLabsTTS: no voice_id configured")
            return None

        # v3 has a 3000 character limit per request
        if len(text) > 3000:
            text = text[:3000]
            logger.warning("ElevenLabsTTS: text truncated to 3000 chars (v3 limit)")

        # Cache key
        cache_key = hashlib.sha256(
            json.dumps(
                {
                    "text": text,
                    "voice": effective_voice,
                    "model": self.model_id,
                    "stability": self.stability,
                    "similarity": self.similarity_boost,
                    "style": self.style,
                    "format": self.output_format,
                },
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()[:16]

        out_path = out_dir / f"{cache_key}.{self._ext}"
        if out_path.exists() and out_path.stat().st_size > 0:
            return out_path

        # Build request
        url = f"{self.api_url}/v1/text-to-speech/{effective_voice}"
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }
        params = {"output_format": self.output_format}

        payload = {
            "text": text,
            "model_id": self.model_id,
            "voice_settings": {
                "stability": self.stability,
                "similarity_boost": self.similarity_boost,
                "style": self.style,
                "use_speaker_boost": self.use_speaker_boost,
            },
        }

        await self._ensure_session()
        last_error = None
        backoff = 1.0

        for attempt in range(1, self.max_retries + 2):
            try:
                assert self._session is not None
                async with self._session.post(
                    url,
                    headers=headers,
                    params=params,
                    json=payload,
                ) as resp:
                    if 200 <= resp.status < 300:
                        raw = await resp.read()
                        if not raw:
                            last_error = "empty audio response"
                            break
                        await self._write_bytes(out_path, raw)

                        if not await validate_audio_file(out_path):
                            last_error = "audio file validation failed"
                            break
                        return out_path

                    # Handle errors
                    try:
                        err_data = await resp.json(content_type=None)
                        err_detail = err_data.get("detail", {})
                        if isinstance(err_detail, dict):
                            last_error = f"http {resp.status}: {err_detail.get('message', err_data)}"
                        else:
                            last_error = f"http {resp.status}: {err_detail}"
                    except Exception:
                        last_error = f"http {resp.status}: {await resp.text()}"

                    if resp.status in (429,) or 500 <= resp.status < 600:
                        if attempt <= self.max_retries:
                            await asyncio.sleep(backoff)
                            backoff = min(backoff * 2, 8)
                            continue
                    break

            except Exception as e:
                last_error = str(e)
                if attempt <= self.max_retries:
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, 8)
                    continue
                break

        # Cleanup empty file
        try:
            if out_path.exists() and out_path.stat().st_size == 0:
                out_path.unlink()
        except Exception:
            pass

        logger.error("ElevenLabsTTS synth failed: %s", last_error)
        return None
