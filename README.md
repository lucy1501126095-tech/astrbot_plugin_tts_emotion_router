# AstrBot TTS 双服务商插件

MiniMax (中文) + ElevenLabs (非中文) 双 TTS 工具插件。

基于 [muyouzhi6/astrbot_plugin_tts_emotion_router](https://github.com/muyouzhi6/astrbot_plugin_tts_emotion_router) 改造。

## 工作方式

插件注册两个 LLM 工具，由模型自主决定调用：

- **tts_speak_cn** — 中文语音，走 MiniMax
- **tts_speak_en** — 非中文语音，走 ElevenLabs

## 配置

在 AstrBot 管理面板填写两个服务商的配置：

**MiniMax：** API Key + Voice ID
**ElevenLabs：** API Key + Voice ID + Model ID

两边独立配置，互不影响。只配一个也能用。

## 命令

| 命令 | 说明 |
|------|------|
| tts_test_cn | 测试 MiniMax 中文语音 |
| tts_test_en | 测试 ElevenLabs 英文语音 |
| tts_status | 查看配置状态 |

## 安装

1. git clone 到 AstrBot 插件目录
2. 管理面板填写配置
3. 重启

## 致谢

原插件作者 [muyouzhi6](https://github.com/muyouzhi6)
