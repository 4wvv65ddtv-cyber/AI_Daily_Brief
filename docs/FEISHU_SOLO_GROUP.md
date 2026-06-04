# 个人小群 Webhook（最快 3 分钟）

## 飞书里操作

1. 飞书 → **消息** → 右上角 **+** → **创建群组**
2. 群名称随意（如「AI早报-个人」），**不要拉其他人**（仅自己即可）
3. 进入群聊 → 右上角 **设置** → **群机器人** → **添加机器人** → **自定义机器人**
4. 名称：`AI早报`，安全设置可选 **自定义关键词** 填 `AI` 或 `早报`
5. **添加** 后复制 **Webhook 地址**（一整条 URL）

## 本地操作

1. 打开项目 `.env`，把 `FEISHU_WEBHOOK_URL=` 后面换成刚复制的地址
2. 确认有这两行：
   ```
   FEISHU_PUSH_MODE=webhook
   FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/你的ID
   ```
3. 终端执行：
   ```bash
   cd /Users/yanxin/Desktop/AI_Daily_Brief
   source venv/bin/activate
   python -m ai_news_bot.main
   ```
4. 在该小群里应看到「📊 今日AI早报」卡片

## 你需要提供什么

只需 **Webhook 完整 URL**（可本地自己贴进 `.env`，不必发给别人）。
