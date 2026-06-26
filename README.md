# AstrBot TTS 插件

多服务商 TTS 插件，支持语言路由自动切换。

基于 [muyouzhi6/astrbot_plugin_tts_emotion_router](https://github.com/muyouzhi6/astrbot_plugin_tts_emotion_router) 改造。

## 支持的 TTS 服务商

- **MiniMax** — 中文场景推荐，性价比高
- **ElevenLabs** — 英文场景推荐，支持 v3 / Flash v2.5 / Multilingual v2，Voice Design 自定义音色
- **SiliconFlow** — 硅基流动

## 语言路由

开启后插件自动检测文本语言，按中文字符占比选择服务商。典型用法：

- 中文 → MiniMax（便宜、中文自然）
- 非中文 → ElevenLabs（音质好、英音地道）

阈值可调，默认 0.5（中文字符超过一半走中文服务商）。

## 配置

在 AstrBot 管理面板（6185 端口）→ 插件配置：

### 单服务商模式

`tts_engine.provider` 选 `minimax` / `elevenlabs` / `siliconflow`，填对应的 API Key 和参数。

### 语言路由模式

`tts_engine.language_router.enable` 设为 `true`，然后分别配置：

- `chinese_provider`: 中文服务商（默认 minimax）
- `other_provider`: 非中文服务商（默认 elevenlabs）
- `threshold`: 中文字符占比阈值（默认 0.5）

两边的服务商参数（key、voice_id 等）需要各自填完整。

### ElevenLabs 配置项

| 参数 | 说明 | 默认值 |
|------|------|--------|
| key | API Key（xi-api-key） | - |
| voice_id | 音色 ID | - |
| model_id | 模型 | eleven_v3 |
| stability | 稳定性（0~1） | 0.5 |
| similarity_boost | 相似度增强（0~1） | 0.75 |
| style | 风格化程度（0~1） | 0.0 |
| output_format | 输出格式 | mp3_44100_128 |

## 命令

| 命令 | 说明 |
|------|------|
| tts_on | 开启当前会话语音输出 |
| tts_off | 关闭当前会话语音输出 |
| tts_all_on | 开启全局自动语音 |
| tts_all_off | 关闭全局自动语音 |
| tts_status | 查看当前状态 |
| tts_say [文本] | 手动发一条语音 |

LLM 工具调用：`tts_speak(text)` — Bot 主动发送语音。

## 安装

1. 在 AstrBot 插件市场安装或 git clone 到插件目录
2. 确保系统有 `ffmpeg`
3. 在管理面板填写配置
4. 重启插件

## 致谢

原插件作者 [muyouzhi6](https://github.com/muyouzhi6)
