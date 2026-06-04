# 部署与运维指南（Phase 6）

## 1. 服务器要求

- Python 3.9+
- 可访问外网（RSS、OpenAI API、飞书 Webhook）
- 建议：1 核 512MB 以上，无 GPU

## 2. 安装步骤

```bash
git clone <your-repo> AI_Daily_Brief
cd AI_Daily_Brief
bash scripts/bootstrap.sh
```

编辑 `.env`：

```bash
OPENAI_API_KEY=sk-...
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/...
```

## 3. 手动试跑

```bash
source venv/bin/activate

# 仅采集+分类
python -m ai_news_bot.main --crawl-only

# 完整试运行（不调 OpenAI / 不推送）
python -m ai_news_bot.main --dry-run --preview-card output/card.json

# 生产运行
python -m ai_news_bot.main --log-file logs/brief-$(date +%Y%m%d).log
```

## 4. 定时任务

**不依赖 Mac 开机/登录**：见 **[CLOUD_SCHEDULE.md](CLOUD_SCHEDULE.md)**（GitHub Actions 推荐）。

本机定时（仅 Mac 唤醒且通常需已登录时可靠）：

复制 [`crontab.example`](../crontab.example) 到 crontab：

```bash
crontab -e
```

示例：工作日 08:00（北京时间，依赖服务器时区或显式 TZ）：

```cron
TZ=Asia/Shanghai
0 8 * * 1-5 cd /path/to/AI_Daily_Brief && ./venv/bin/python -m ai_news_bot.main --log-file logs/brief.log >> logs/cron.log 2>&1
```

## 5. 日志与产物

| 路径 | 说明 |
|------|------|
| `logs/brief-YYYYMMDD.log` | `--log-file` 结构化日志 |
| `logs/cron.log` | cron 标准输出/错误 |
| `output/brief-YYYYMMDD.json` | 每次正式运行自动保存简报 |
| `output/card.json` | `--preview-card` 飞书卡片 payload |

## 6. 密钥安全

- `.env` 已加入 `.gitignore`，**勿提交仓库**
- 生产环境可用系统环境变量代替 `.env`
- 飞书 Webhook 泄露后应在群内重置机器人

## 7. 故障排查

| 现象 | 处理 |
|------|------|
| 采集为 0 | 检查网络；查看 `[crawler]` 各源错误 |
| OpenAI 失败 | 确认 `OPENAI_API_KEY`；检查 `OPENAI_BASE_URL` |
| 飞书发送失败 | 检查 Webhook；用 `--preview-card` 本地验 JSON |
| cron 无输出 | 确认绝对路径、`venv` 可执行、日志目录可写 |

## 8. 验收命令

```bash
make verify-all          # Phase 1–6（需网络）
make verify-all-live     # 含 OpenAI 真实调用（需密钥）
```
