# 飞书个人推送配置（非群聊）

群机器人 **Webhook 只能发到群**，不能发到「与自己的私聊」。  
要**单独推给你自己**，请用 **飞书开放平台自建应用**（本项目默认 `FEISHU_PUSH_MODE=app`）。

---

## 方案对比

| 方式 | 推送到 | 配置难度 |
|------|--------|----------|
| **企业自建应用（推荐）** | 你的飞书私聊 | 中等，一次配置 |
| 仅自己一人的群 + Webhook | 小群会话（像私信） | 简单，但不是真私聊 |
| 群 Webhook | 群成员可见 | 最简单 |

---

## 推荐：企业自建应用 → 私聊推送

### 1. 创建应用

1. 打开 [飞书开放平台](https://open.feishu.cn/app)
2. **创建企业自建应用**（名称如「AI早报」）
3. 记录 **App ID**、**App Secret**（凭证与基础信息）

### 2. 开启机器人

1. 应用后台 → **添加应用能力** → **机器人**
2. 启用机器人

### 3. 申请权限（权限管理 → 开通）

至少开通：

- `im:message`
- `im:message:send_as_bot`
- `contact:user.email:readonly`（若用邮箱查 open_id）

保存后，在 **版本管理与发布** 中创建版本并**发布给企业**（或可用范围包含你自己）。

### 4. 在飞书客户端激活机器人

1. 飞书 App → 搜索你的应用名 → 打开机器人
2. **随便发一条消息**（用于建立会话，否则可能收不到主动推送）

### 5. 配置 `.env`

```env
# 个人私聊（默认）
FEISHU_PUSH_MODE=app
FEISHU_APP_ID=cli_xxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxxxxx

# 方式 A：直接填 open_id（推荐，最稳定）
FEISHU_RECEIVE_ID=ou_xxxxxxxxxxxxxxxx
FEISHU_RECEIVE_ID_TYPE=open_id

# 方式 B：用企业邮箱自动查 open_id（二选一）
# FEISHU_USER_EMAIL=you@your-company.com
```

### 6. 获取你的 `open_id`

配置好 `FEISHU_APP_ID`、`FEISHU_APP_SECRET` 后：

```bash
cd /Users/yanxin/Desktop/AI_Daily_Brief
source venv/bin/activate
python scripts/feishu_get_open_id.py 你的企业邮箱@company.com
```

把输出的 `open_id` 填入 `.env` 的 `FEISHU_RECEIVE_ID`。

### 7. 试跑

```bash
python -m ai_news_bot.main --no-push   # 先测 OpenAI
python -m ai_news_bot.main             # 推送到你的飞书私聊
```

成功时日志：`[feishu] Personal message sent successfully`

---

## 备选：仅自己一人的群（Webhook）

若暂时不想建应用：

1. 新建一个**只有你自己**的飞书群
2. 群设置 → 群机器人 → 自定义机器人 → 复制 Webhook
3. `.env` 设置：

```env
FEISHU_PUSH_MODE=webhook
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/...
```

消息会出现在该群会话里，效果接近「个人收件箱」，但不是应用私聊。

---

## 常见问题

| 问题 | 处理 |
|------|------|
| `Failed to get tenant token` | 检查 App ID / Secret |
| `No user found for email` | 邮箱需为企业飞书账号；检查通讯录权限 |
| 发送成功但收不到 | 先在飞书里给机器人发过一条消息 |
| `code 230013` 无权限 | 补开 `im:message:send_as_bot` 并重新发布应用 |
