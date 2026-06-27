# -*- coding: utf-8 -*-
"""TTS 双服务商插件 — MiniMax (中文) + ElevenLabs (非中文)"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from .core.compat import initialize_compat

initialize_compat()

from .core.compat import (
    import_astr_message_event,
    import_filter,
    import_message_components,
    import_context_and_star,
    import_astrbot_config,
)

AstrMessageEvent = import_astr_message_event()
filter = import_filter()
Record, Plain = import_message_components()
Context, Star, register = import_context_and_star()
AstrBotConfig = import_astrbot_config()

from .tts.provider_minimax import MiniMaxTTS
from .tts.provider_elevenlabs import ElevenLabsTTS
from .utils.audio import ensure_dir, cleanup_dir

logger = logging.getLogger(__name__)

PLUGIN_ID = "astrbot_plugin_tts_emotion_router"
PLUGIN_NAME = "TTS 双服务商"
PLUGIN_DESC = "MiniMax (中文) + ElevenLabs (非中文) 双 TTS 工具"
PLUGIN_VERSION = "5.0.0"
TEMP_DIR = Path(__file__).parent / "temp"
CLEANUP_TTL = 3600


@register(PLUGIN_ID, PLUGIN_NAME, PLUGIN_DESC, PLUGIN_VERSION)
class TTSPlugin(Star):
    def __init__(self, context: Context, config: Optional[dict] = None):
        super().__init__(context)
        self._background_tasks: List[asyncio.Task] = []

        if isinstance(config, AstrBotConfig):
            self._cfg = dict(config)
        else:
            self._cfg = config or {}

        ensure_dir(TEMP_DIR)
        self._init_providers()

    # ───────── providers ─────────

    def _init_providers(self):
        mm = self._cfg.get("minimax", {}) or {}
        self.minimax: Optional[MiniMaxTTS] = None
        if mm.get("key"):
            self.minimax = MiniMaxTTS(
                api_url=str(mm.get("url", "https://api.minimaxi.com/v1/t2a_v2")),
                api_key=str(mm["key"]),
                model=str(mm.get("model", "speech-2.8-hd")),
                fmt=str(mm.get("audio_format", "mp3")),
                speed=float(mm.get("speed", 1.0)),
                voice_id=str(mm.get("voice_id", "")),
                vol=float(mm.get("vol", 1.0)),
                pitch=int(mm.get("pitch", 0)),
                default_emotion=str(mm.get("emotion", "neutral")),
                sample_rate=int(mm.get("sample_rate", 32000)),
                bitrate=int(mm.get("bitrate", 128000)),
                channel=int(mm.get("channel", 1)),
                max_retries=2,
                timeout=30,
            )
            logger.info("MiniMax TTS initialized, voice_id=%s", mm.get("voice_id"))
        else:
            logger.warning("MiniMax TTS not configured (no key)")

        el = self._cfg.get("elevenlabs", {}) or {}
        self.elevenlabs: Optional[ElevenLabsTTS] = None
        if el.get("key"):
            self.elevenlabs = ElevenLabsTTS(
                api_key=str(el["key"]),
                voice_id=str(el.get("voice_id", "")),
                model_id=str(el.get("model_id", "eleven_v3")),
                api_url=str(el.get("url", "https://api.elevenlabs.io")),
                stability=float(el.get("stability", 0.5)),
                similarity_boost=float(el.get("similarity_boost", 0.75)),
                style=float(el.get("style", 0.0)),
                use_speaker_boost=bool(el.get("use_speaker_boost", True)),
                output_format=str(el.get("output_format", "mp3_44100_128")),
                max_retries=2,
                timeout=60,
            )
            logger.info("ElevenLabs TTS initialized, voice_id=%s", el.get("voice_id"))
        else:
            logger.warning("ElevenLabs TTS not configured (no key)")

    # ───────── lifecycle ─────────

    async def terminate(self):
        for t in list(self._background_tasks):
            if not t.done():
                t.cancel()
                try:
                    await t
                except asyncio.CancelledError:
                    pass
        self._background_tasks.clear()
        for provider in (self.minimax, self.elevenlabs):
            if provider:
                try:
                    await provider.close()
                except Exception:
                    pass

    # ───────── helpers ─────────

    async def _synth_and_send(
        self,
        event: AstrMessageEvent,
        text: str,
        provider: Any,
        provider_name: str,
        voice_override: str = "",
    ) -> str:
        if not provider:
            return f"{provider_name} 未配置，请在管理面板填写 API Key。"

        content = (text or "").strip()
        if not content:
            return "文本为空。"

        logger.info("TTS [%s]: text_len=%d, text_preview=%s",
                     provider_name, len(content), content[:50])

        try:
            audio_path = await provider.synth(
                content,
                voice_override,
                TEMP_DIR,
            )
        except Exception as e:
            logger.error("TTS [%s] synth error: %s", provider_name, e, exc_info=True)
            return f"语音合成失败：{e}"

        if not audio_path:
            logger.error("TTS [%s] returned empty path", provider_name)
            return "语音合成失败：未生成音频文件。"

        audio_path = Path(audio_path)
        if not audio_path.exists() or audio_path.stat().st_size == 0:
            logger.error("TTS [%s] audio file invalid: %s", provider_name, audio_path)
            return "语音合成失败：音频文件无效。"

        norm = str(audio_path.resolve())
        try:
            await event.send(event.chain_result([Record(file=norm)]))
            event.stop_event()
            logger.info("TTS [%s]: sent audio %s", provider_name, norm)
            return f"[语音已发送：{content[:20]}...]"
        except Exception as e:
            logger.error("TTS [%s] send error: %s", provider_name, e, exc_info=True)
            return f"语音发送失败：{e}"

    # ───────── LLM tools ─────────

    if hasattr(filter, "llm_tool"):

        @filter.llm_tool(name="tts_speak_cn")
        async def tts_speak_cn(self, event: AstrMessageEvent, text: str):
            """用中文语音说话（MiniMax）。当你想用中文语音回复用户时调用此工具。

            Args:
                text(string): 要合成为中文语音的文本。
            """
            return await self._synth_and_send(event, text, self.minimax, "MiniMax")

        @filter.llm_tool(name="tts_speak_en")
        async def tts_speak_en(self, event: AstrMessageEvent, text: str):
            """用非中文语音说话（ElevenLabs）。当你想用英文或其他非中文语言语音回复用户时调用此工具。

            Args:
                text(string): 要合成为语音的非中文文本。
            """
            return await self._synth_and_send(event, text, self.elevenlabs, "ElevenLabs")

    # ───────── commands ─────────

    @filter.command("tts_test_cn")
    async def cmd_test_cn(self, event: AstrMessageEvent):
        """测试 MiniMax 中文语音"""
        result = await self._synth_and_send(
            event, "你好，这是一条中文语音测试。", self.minimax, "MiniMax"
        )
        if "失败" in result or "未配置" in result:
            yield event.plain_result(result)

    @filter.command("tts_test_en")
    async def cmd_test_en(self, event: AstrMessageEvent):
        """测试 ElevenLabs 英文语音"""
        result = await self._synth_and_send(
            event, "Hello, this is an English voice test.", self.elevenlabs, "ElevenLabs"
        )
        if "失败" in result or "未配置" in result:
            yield event.plain_result(result)

    @filter.command("tts_status")
    async def cmd_status(self, event: AstrMessageEvent):
        """查看 TTS 状态"""
        lines = ["TTS 状态："]
        lines.append(f"MiniMax: {'✅ 已配置' if self.minimax else '❌ 未配置'}")
        lines.append(f"ElevenLabs: {'✅ 已配置' if self.elevenlabs else '❌ 未配置'}")
        yield event.plain_result("\n".join(lines))
