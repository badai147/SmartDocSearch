# 智能文档问答助手（LangChain + FastAPI + Vue）

- **后端**：FastAPI + LangChain
- **向量数据库**：Chroma（本地持久化）
- **RAG**：查询增强（Query Enhancement）→ Agent 调用检索工具 → 结合上下文生成回答；提示词、工具与编排代码分文件维护（`prompts/`、`tools/`、`services/rag.py`）
- **文档 ETL**：上传文件 → **MarkItDown** 转为 **Markdown 全文** →（可选）Agent 决定切分参数 → 按 Markdown 友好分隔符递归分块 → 仅在写入向量库前转为 LangChain `Document` → embedding → Chroma
- **前端**：Vue（上传文档、提问、展示回答与来源）

## 项目结构

- `backend/`：后端服务
  - `backend/app/prompts/`：RAG / 查询改写 / ETL 等提示词与拼装函数
  - `backend/app/tools/`：检索、ETL 参数提交等 LangChain 工具工厂
  - `backend/app/services/`：业务编排（RAG、ETL、向量库、LLM 等）
- `frontend/`：前端页面（Vite）

## 准备环境

### 后端

1. 安装依赖  
   `cd backend`  
   `pip install -r requirements.txt`  

2. 配置环境变量  
   复制 `backend/.env.example` 为 `backend/.env`，按 `backend/app/core/config.py` 中的 `Settings` 字段填写 API Key、模型名、Base URL 等（兼容 OpenAI 风格的 Embedding / Chat 接口即可）。

3. 启动后端  
   在项目根目录运行：`uvicorn backend.app.main:app --reload --port 8000`

后端接口：

- `GET /api/health`
- `POST /api/docs/ingest`（上传文档：具体可解析类型取决于 MarkItDown；服务端会先落盘再执行 ETL）
- `POST /api/chat/ask`（提问：返回 `answer` + `sources`）

### 前端

1. 安装依赖  
   `cd frontend`  
   `npm install`

2. 启动  
   `npm run dev`

3. 打开页面  
   浏览器访问 `http://localhost:5173`

## 数据落地位置

- 上传文档：`backend/data/docs/`
- 向量数据库：`backend/data/chroma/`

## 使用流程

1. 在前端上传文档并导入
2. 输入问题并发送
3. 助手会基于检索到的片段回答
