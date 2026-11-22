# 审讯室 · 谎言侦探（Interrogation Room）

一款「AI 审讯」网页游戏：你是侦探，对面坐着**一个 AI 嫌疑人**。它藏着秘密、会说谎、会狡辩、会反咬，但**记得你说过的每句话、出示过的每个证据**。你要抓矛盾、压镇定、做指认，破案或放跑真凶。

参赛作品 · AI+∞ 开发者创作大赛 第三期「AI 造游戏」· 方向：故事与 AI NPC。

## 玩法

1. **案情简报**：死者、现场、证据。
2. **审讯**：自由输入问话；或点「施压」「观察微表情」。
3. **出示证据**：点证据托盘里的证据 → 若与嫌疑人此前说法冲突，触发「矛盾！」，镇定大跌。
4. **镇定博弈**：施压/抓矛盾降低镇定；镇定过低会破防招供；无证据乱施压 3 次，嫌疑人要求律师 → 审讯终止。
5. **指认**：填「凶手 + 手法 + 动机」→ 判定破案 / 失败，并揭晓真相。

## 技术架构

- 后端：FastAPI（Python），SQLite 持久化会话。
- 前端：原生 HTML/CSS/JS 单页，`fetch` + 流式读取。
- LLM：ModelScope OpenAI 兼容端点（运行时调用，Key 走环境变量）。
- 部署：Docker → 魔搭创空间（监听 7860）。
- AI 原生机制：真相档案（Ground Truth）+ 谎言一致性约束 + 跨回合记忆 + 矛盾检测 + 镇定状态机。

## 本地运行

```bash
cd backend
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
# 需要真实 AI：设置环境变量
export MODELSPACE_API_KEY=ms-xxxxxxxx
export MODELSPACE_MODEL=Qwen/Qwen2.5-72B-Instruct   # 可选
.venv/bin/python -m uvicorn app:app --port 7860
# 打开 http://localhost:7860/
```

> 不设置 `MODELSPACE_API_KEY` 也能启动，只是 AI 不会回复（适合先看界面）。

## 测试

```bash
cd backend
.venv/bin/python -m pytest -q     # 27 passed
```

## 部署

见 [DEPLOY.md](DEPLOY.md)。

## 目录结构

```
backend/
  app.py              FastAPI 入口 + 所有 /api 路由
  settings.py         环境变量配置
  session_store.py    SQLite 会话持久化
  truth_engine.py     真相档案 / 矛盾检测 / 镇定 / 结局判定
  prompt_builder.py   提示词组装（含一致性约束 + 记忆）
  llm_client.py       ModelScope 流式调用
  cases/case_001.py   「雨夜书房」真相档案
  web/                前端 index.html / style.css / game.js
  tests/              pytest 测试
  Dockerfile
```