# 更换大模型（不必用 OpenAI）

本项目的总结模块使用 **OpenAI 官方 Python SDK**，但支持一切 **OpenAI 兼容接口**。  
只需改 `.env`，**不用改代码**。

---

## 最快切换方式

在 `.env` 增加一行预设名称 + 对应平台的 API Key：

```env
LLM_PROVIDER=deepseek
OPENAI_API_KEY=你在该平台申请的密钥
```

然后运行：

```bash
python -m ai_news_bot.main
```

---

## 推荐替代（国内常用、相对便宜）

### DeepSeek（推荐）

```env
LLM_PROVIDER=deepseek
OPENAI_API_KEY=sk-xxxxxxxx
# 可选显式指定：
# OPENAI_BASE_URL=https://api.deepseek.com
# OPENAI_MODEL=deepseek-chat
```

注册：https://platform.deepseek.com

### 月之暗面 Moonshot (Kimi)

```env
LLM_PROVIDER=moonshot
OPENAI_API_KEY=sk-xxxxxxxx
```

注册：https://platform.moonshot.cn

### 智谱 GLM

```env
LLM_PROVIDER=zhipu
OPENAI_API_KEY=xxxxxxxx
```

注册：https://open.bigmodel.cn

### Groq（有免费额度，海外）

```env
LLM_PROVIDER=groq
OPENAI_API_KEY=gsk_xxxxxxxx
```

注册：https://console.groq.com

---

## 完全免费：本地 Ollama

1. 安装 Ollama：https://ollama.com  
2. 拉模型：`ollama pull qwen2.5:7b`  
3. `.env`：

```env
LLM_PROVIDER=ollama
OPENAI_API_KEY=ollama
OPENAI_MODEL=qwen2.5:7b
```

4. 保持 Ollama 运行后再执行 `python -m ai_news_bot.main`

---

## 继续用 OpenAI

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

需账户有可用余额（你之前的 `insufficient_quota` 需去 Billing 充值）。

---

## 自定义任意兼容 API

不填 `LLM_PROVIDER`，直接写：

```env
OPENAI_API_KEY=你的密钥
OPENAI_BASE_URL=https://你的网关/v1
OPENAI_MODEL=模型名称
```

---

## 不调用任何大模型

仅 RSS + 飞书预览（无 AI 总结费用）：

```bash
python -m ai_news_bot.main --dry-run
```

或 OpenAI 失败时会自动降级为预览版（已在 `main.py` 实现）。

---

## 预设一览

| LLM_PROVIDER | 默认模型 | 说明 |
|--------------|----------|------|
| `openai` | gpt-4o-mini | 官方，按量付费 |
| `deepseek` | deepseek-chat | 价格低、中文好 |
| `moonshot` | moonshot-v1-8k | Kimi 同源 API |
| `zhipu` | glm-4-flash | 智谱，有免费档 |
| `groq` | llama-3.3-70b-versatile | 速度快 |
| `ollama` | qwen2.5:7b | 本地免费 |

显式设置的 `OPENAI_BASE_URL` / `OPENAI_MODEL` 会覆盖预设默认值。
