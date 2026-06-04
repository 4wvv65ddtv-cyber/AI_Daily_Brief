# GitHub Actions / Secrets 显示「空白」— 排查说明

## 一、Secrets 页：没有显示密钥内容 = 正常

路径：**Settings → Secrets and variables → Actions → Repository secrets**

| 你看到的 | 含义 |
|----------|------|
| 列表里有 `OPENAI_API_KEY`、`FEISHU_WEBHOOK_URL` 两行 | ✅ 已添加成功 |
| 值全是 `***` 或空白 | ✅ GitHub **故意不显示**，防止泄露 |
| 整个列表一张表都没有 | ❌ 可能点成了 **Variables** 标签，或还没点 **Add secret** 保存 |

**不要**在 **Environment secrets** 里找（那是另一套，默认是空的）。

---

## 二、Actions 页：工作流在，但运行记录可能是空的

仓库里**已经有**工作流文件：`.github/workflows/daily-brief.yml`（名称：**AI Daily Brief**）。

### 正确打开方式

1. 打开：**https://github.com/4wvv65ddtv-cyber/AI_Daily_Brief/actions**
2. 看**左侧边栏**「All workflows」下是否有 **「AI Daily Brief」**
3. 点进去后，右侧若写 *This workflow has no runs yet* — 只是**还没跑过**，不是没配置

### 直接打开工作流（可手动运行）

**https://github.com/4wvv65ddtv-cyber/AI_Daily_Brief/actions/workflows/daily-brief.yml**

右侧点击 **Run workflow** → 分支选 **main** → 再点绿色 **Run workflow**。

### 若左侧完全没有「AI Daily Brief」

按顺序检查：

**① 启用 Actions**

Settings → **Actions** → **General** →  
「Actions permissions」选 **Allow all actions and reusable workflows** → **Save**

**② 首次进入 Actions 的授权横幅**

打开 Actions 页，若出现 *Workflows aren't being run on this repository* 或 *Approve workflows*，点 **I understand my workflows, go ahead and enable them**。

**③ 确认代码在 main 分支**

Code 页能看到文件夹 `.github` → `workflows` → `daily-brief.yml`。  
若没有，在 GitHub Desktop 点 **Push origin**。

**④ 再推送一次（触发自动运行）**

本地若已更新工作流，GitHub Desktop **Push origin** 后，Actions 应出现一条新记录。

---

## 三、Secrets 与工作流的关系

| 情况 | Actions 表现 |
|------|----------------|
| 没配 Secret | 工作流**仍在左侧**，运行后变红 ❌，日志写 key 缺失 |
| Secret 配错 | 运行红 ❌，日志 401 / webhook 失败 |
| 一切正常 | 运行绿 ✅，飞书收到卡片 |

---

## 四、推荐操作顺序（3 分钟）

1. Settings → Actions → General → **Allow all actions** → Save  
2. 打开 [工作流页面](https://github.com/4wvv65ddtv-cyber/AI_Daily_Brief/actions/workflows/daily-brief.yml) → **Run workflow**  
3. 等 1～2 分钟，点进最新一条运行记录看是否绿色  
4. 检查飞书是否收到早报  

仍空白时，说明是：① Actions 未启用、② 没进对仓库、③ 还在 Secrets 页而不是 Actions 页。
