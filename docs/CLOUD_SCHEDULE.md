# 云端定时推送（无需 Mac 开机 / 登录）

## 为什么 GitHub 内置 `schedule` 不靠谱？

GitHub Actions 的 `on.schedule` **不保证准时**：

- 高负载时可能 **延迟数小时**（本项目曾出现 8:00 应跑、实际 17:30 才跑）
- 有时 **早上窗口直接跳过**
- 这是平台机制，**换 cron 表达式、加时区都无法根治**

因此：**不要指望仓库里的 `schedule:` 让你在 8:00 收到飞书。**

---

## 推荐方案：外部准时触发 + GitHub Actions 执行

思路：准时服务在 **8:00** 调用 GitHub API → 触发 `workflow_dispatch` → 仓库里现有 workflow 跑简报并推飞书。

| 环节 | 用什么 | 是否准时 |
|------|--------|----------|
| 到点「叫醒」 | [cron-job.org](https://console.cron-job.org/)（免费） | ✅ 通常 ±1 分钟 |
| 真正跑任务 | GitHub Actions `daily-brief.yml` | ✅ 触发后 1–3 分钟完成 |
| 内置 `schedule` | 保留作兜底 | ❌ 仅备用 |

### 一键配置向导

```bash
cd /Users/yanxin/Desktop/AI_Daily_Brief

# 1. 在 .env 写入 GITHUB_PAT（见下方「创建 Token」）
# 2. 运行向导（会验证 Token 并打印 cron-job.org 填法）
bash scripts/setup_external_cron.sh
```

### 创建 GitHub Token（只需一次）

1. 打开 https://github.com/settings/tokens?type=beta  
2. **Generate new token**  
3. **Repository access** → 只选 `AI_Daily_Brief`  
4. **Permissions** → `Actions: Read and write`，`Metadata: Read`  
5. 复制 token，写入 `.env`：

```bash
GITHUB_PAT=github_pat_xxxxxxxx
```

### cron-job.org 关键参数

| 字段 | 值 |
|------|-----|
| URL | `https://api.github.com/repos/4wvv65ddtv-cyber/AI_Daily_Brief/actions/workflows/daily-brief.yml/dispatches` |
| Method | `POST` |
| Schedule | 每天 `08:00`，时区 `Asia/Shanghai` |
| Header | `Authorization: Bearer <GITHUB_PAT>` |
| Header | `Accept: application/vnd.github+json` |
| Header | `Content-Type: application/json` |
| Body | `{"ref":"main"}` |

也可手动测试触发：

```bash
GITHUB_PAT=github_pat_xxx ./scripts/trigger_github_workflow.sh
```

---

## 方案 B：本机 crontab（Mac 8 点在线时）

不依赖 GitHub 准时，但 **需要 Mac 8 点醒着且已登录**：

```bash
bash scripts/install_crontab.sh   # 每天 8:00 + 8:15
```

项目在桌面时，若 launchd 报 `Operation not permitted`，优先用 crontab，或给启动脚本「完全磁盘访问权限」。

---

## 方案 C：云服务器 / NAS

任意常开 Linux：

```bash
TZ=Asia/Shanghai
0 8 * * * cd /path/to/AI_Daily_Brief && ./venv/bin/python -m ai_news_bot.main --log-file logs/brief.log
```

---

## GitHub Secrets（云端跑任务必备）

仓库 → **Settings** → **Secrets and variables** → **Actions**：

| Secret | 内容 |
|--------|------|
| `OPENAI_API_KEY` | **必填**。与本机 `.env` 相同的 DeepSeek `sk-...` key（未配置会推「试运行」假内容） |
| `DEEPSEEK_API_KEY` | 可选别名，与 `OPENAI_API_KEY` 二选一 |
| `FEISHU_WEBHOOK_URL` | 飞书机器人 Webhook URL |

更新 Secret：仓库 → **Settings** → **Secrets and variables** → **Actions** → 编辑 `OPENAI_API_KEY`，粘贴本机 `.env` 里的 `sk-` 密钥后保存，再手动 **Run workflow** 验证。

---

## 推荐组合（按你的使用习惯）

| 你的情况 | 推荐 |
|----------|------|
| Mac 经常关着，要 8 点准时 | **cron-job.org + GitHub Actions**（方案 A） |
| Mac 每天 8 点前已开机 | 本机 crontab（方案 B）+ 可选方案 A 双保险 |
| 有常开 NAS/云主机 | 方案 C 最稳 |

**防重复**：workflow 内有「今天已发过则跳过」，8:00 和 8:15 各触发一次也只会收到 **一条** 飞书。

---

## 对比

| 方式 | Mac 要开机 | 8 点准时 | 含周末 |
|------|------------|----------|--------|
| GitHub 内置 schedule | 否 | ❌ | ✅ |
| **cron-job.org 触发** | **否** | **✅** | **✅** |
| 本机 crontab | 是 | ✅ | ✅ |
| 云服务器 cron | 否 | ✅ | ✅ |
