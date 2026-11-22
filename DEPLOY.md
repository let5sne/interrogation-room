# 部署到魔搭创空间（ModelScope Studio）

本游戏是 Docker 应用（FastAPI + 原生前端），部署到**魔搭创空间（ModelScope Studio）**。

> 已验证：`docker build` 成功（镜像 289MB），容器内 `/api/health`、首页、静态资源均 200，`uvicorn` 正常监听 7860。

## 方式 A：一键脚本（推荐）

```bash
export MODELSCOPE_API_KEY=ms-xxxxxxxx        # 从 https://modelscope.cn/my/myaccesstoken 获取
python3 scripts/deploy_studio.py --owner <你的用户名> --repo interrogation-room
```

脚本自动完成：查用户 → 建 Docker 创空间 → 推送代码（main→master）→ 写密钥 `MODELSPACE_API_KEY`/`MODELSPACE_MODEL` → 触发部署 → 跟踪日志 → 打印创空间地址。

> ⚠️ **Docker 类型创空间前提**：需先完成「阿里云账号绑定 + 实名认证」，否则镜像无法构建：<https://modelscope.cn/docs/studios/docker>
>
> 默认免费规格 `platform/2v-cpu-16g-mem`；付费规格（`--hardware paid/...`）会计费，需你自行确认。

## 方式 B：网页后台手动部署（约 10 分钟）

## 0. 前置准备

1. 注册/登录 [modelscope.cn](https://modelscope.cn)。
2. 获取 **ModelScope API Key**（免费，每日 2000 次调用）：
   - 登录后打开 [API Key 管理页](https://www.modelscope.cn/my/myaccesstoken)
   - 创建 SDK Token，形如 `ms-xxxxxxxx`。
3. 确认本仓库 `backend/` 目录可访问（就在本机）。
4. （Docker 类型必做）完成「阿里云账号绑定 + 实名认证」：<https://modelscope.cn/docs/studios/docker>，否则镜像无法构建。

## 1. 新建创空间（Studio）

1. 打开 [modelscope.cn/createspace](https://modelscope.cn/createspace)（或「我的 → 创空间 → 新建创空间」）。
2. 选择 **Docker** 类型（不是 Gradio/Streamlit/Static）。
3. 填写：
   - 名称：`interrogation-room`（或你喜欢的英文名）
   - 可见性：公开（比赛要求公开可访问）
4. 创建后进入创空间的「文件」页。

## 2. 上传代码

把整个 `backend/` 目录里的**内容**上传到创空间根目录，确保根目录下有：

```
Dockerfile
requirements.txt
app.py
settings.py
session_store.py
truth_engine.py
prompt_builder.py
llm_client.py
cases/__init__.py
cases/case_001.py
web/index.html
web/style.css
web/game.js
```

> 不要上传 `.venv`、`__pycache__`、`*.db`（已在 `.dockerignore` / `.gitignore` 排除）。
>
> 若创空间支持关联 Git 仓库，也可以把本仓库根目录关联，并把 **构建上下文设为 `backend/`**。

## 3. 配置密钥变量（Secrets）

在创空间的「设置 / Settings → 环境变量 / Secrets」中新增：

| 变量名 | 值 |
|---|---|
| `MODELSPACE_API_KEY` | 你的 `ms-xxxxxxxx` |
| `MODELSPACE_MODEL` | `Qwen/Qwen2.5-72B-Instruct`（或 `deepseek-ai/DeepSeek-V3`） |

> `MODELSPACE_BASE_URL` 有默认值 `https://api-inference.modelscope.cn/v1`，无需设置。

## 4. 启动 / 部署

1. 在创空间点「启动 / 部署 / Restart」。
2. 等待构建日志出现 `Uvicorn running on http://0.0.0.0:7860`。
3. 打开创空间公网地址，确认：
   - 出现「案情简报」弹窗 + 证据列表
   - 点「开始审讯」，输入问话，嫌疑人流式回复
   - 点「施压」镇定下降；点证据出现「矛盾！」；点「指认」能结算

## 5. 常见问题

- **首页 500 / 起不来**：查看创空间「日志」，多为缺依赖或密钥未配；确认 `MODELSPACE_API_KEY` 已设置。
- **AI 不回复 / 报错**：确认 `MODELSPACE_API_KEY` 有效、`MODELSPACE_MODEL` 是平台可用模型 ID。
- **端口**：容器监听 `7860`（Dockerfile 已 `EXPOSE 7860`）。
- **数据持久化**：默认 `sessions.db` 在容器内，重启会丢；比赛演示足够，如需持久化可挂载卷或后续改用外部 DB。

## 6. 参赛提交清单（对照赛事要求）

- [ ] 创空间公开可访问（URL 能打开、能玩）
- [ ] 小红书发布参赛构想，带话题：`#AI无限开发者创作大赛 #AI造游戏 #盛趣游戏 #赞寄科技XSUPERZONE #华硕AI智能体电脑`，并 @魔搭ModelScope社区 @Qoder
- [ ] 官网提交帖子链接
- [ ] 魔搭开发者实践发布「创作手记」（模板见 `modelscope.cn/learn/437860`），附演示视频
- [ ] 报名截止 12.01 12:00 / 作品提交截止 12.01 18:00