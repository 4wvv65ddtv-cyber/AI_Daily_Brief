# 云端定时推送（无需 Mac 开机 / 登录）

本机 `cron` / LaunchAgent **依赖电脑在 8:00 已唤醒且通常需已登录**，合盖休眠或 8 点后才开机都会漏发。

若需要 **每天固定时间自动发飞书、不依赖你开电脑**，请用 **GitHub Actions**（或其它云服务器）跑任务。

---

## 方案 A：GitHub Actions（推荐，免费额度内够用）

### 1. 把项目推到 GitHub

```bash
cd /Users/yanxin/Desktop/AI_Daily_Brief
git init   # 若尚未初始化
git add .
git commit -m "Add cloud scheduled brief"
# 在 GitHub 新建仓库后：
git remote add origin https://github.com/4wvv65ddtv-cyber/AI_Daily_Brief.git
git push -u origin main
```

确保 **不要** 把 `.env` 提交上去（已在 `.gitignore`）。

### 2. 配置 Secrets

仓库 → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**：

| Secret 名称 | 内容 |
|-------------|------|
| `OPENAI_API_KEY` | DeepSeek / OpenAI 的 API Key |
| `FEISHU_WEBHOOK_URL` | 飞书小群机器人 Webhook 完整 URL |

可选 **Variables**（非敏感，不设则用默认）：

| Variable | 示例 |
|----------|------|
| `LLM_PROVIDER` | `deepseek` |
| `OPENAI_MODEL` | `deepseek-chat` |
| `OPENAI_BASE_URL` | `https://api.deepseek.com` |

### 3. 启用定时

仓库已包含 [`.github/workflows/daily-brief.yml`](../.github/workflows/daily-brief.yml)：

- **北京时间 每天 08:00** 自动运行（含周六日）；8:15 / 8:30 / 9:00 备用，**一天只推一条**
- 也可在 GitHub **Actions** 页点击 **Run workflow** 手动试跑

### 4. 停用本机定时（避免重复推送）

若已安装本机 LaunchAgent / crontab，云端生效后建议关掉本机：

```bash
launchctl bootout gui/$(id -u)/com.ai.daily-brief 2>/dev/null || true
launchctl bootout gui/$(id -u)/com.ai.daily-brief.login 2>/dev/null || true
crontab -r 2>/dev/null || true
```

### 5. 说明

- GitHub 定时可能有 **几分钟延迟**，属平台正常行为。
- 私有仓库也可使用 Actions（有每月分钟数限额，本任务每次约 1–3 分钟）。
- 失败时可在 Actions 运行详情里下载 `brief-logs-*`  artifact 排查。

---

## 方案 B：云服务器 / NAS（可选）

任意常开 Linux 机器上：

```bash
# 安装后 crontab -e
TZ=Asia/Shanghai
0 8 * * * cd /path/to/AI_Daily_Brief && ./venv/bin/python -m ai_news_bot.main --log-file logs/brief.log
```

在服务器上配置 `.env` 或系统环境变量即可，**不依赖你的 Mac**。

---

## 对比

| 方式 | 需 Mac 8 点开机 | 需登录 | 休眠后补发 |
|------|-----------------|--------|------------|
| 本机 cron / LaunchAgent | 是 | 通常需要 | 仅「登录补跑」脚本 |
| **GitHub Actions** | **否** | **否** | 不适用（云端准时跑） |
| 云服务器 cron | 否 | 否 | 否 |
