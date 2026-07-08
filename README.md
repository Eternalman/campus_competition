# 高校赛事管理系统

基于 Django + Vue3 的全栈校园竞赛管理平台，集成 **RAG 智能问答系统**（Milvus 向量库 + BGE-M3 嵌入 + DashScope LLM），为师生提供赛事发布、报名管理、成绩查询和 AI 智能助手服务。

## 功能概览

### 前台（师生端）

| 模块 | 说明 |
|------|------|
| 赛事浏览 | 首页赛事列表、热门推荐、分类筛选、浏览量统计 |
| 赛事报名 | 赛事详情查看、在线报名、附件上传 |
| 个人中心 | 个人信息修改、密码修改、报名记录查询、成绩查看 |
| **AI 智能助手** | 基于知识库的 RAG 问答，支持多轮对话、会话管理、历史记录 |

### 后台（管理员端）

| 模块 | 说明 |
|------|------|
| 赛事管理 | 赛事的增删改查、发布/草稿状态管理 |
| 分类管理 | 赛事分类维护 |
| 用户管理 | 用户列表、角色管理 |
| 报名管理 | 报名记录查看、审核、成绩录入 |
| 通知公告 | 系统通知发布 |
| 日志管理 | 登录日志、操作日志、错误日志 |
| 数据统计 | ECharts 可视化统计面板 |
| **知识库管理** | 文档上传、自动处理、向量化入库 |

### RAG 智能问答系统

```
用户提问 → 问候语检测 → FQA (BM25) 检索 → BERT 意图分类 → RAG 检索增强生成
                                                              ├─ 通用知识 → LLM 直接回答
                                                              └─ 专业咨询 → 向量检索 + LLM 生成
```

- **多策略检索**：假设问题 (HyDE)、子查询、回溯问题、直接检索四种策略自动选择
- **混合检索**：稠密向量 (Dense) + 稀疏向量 (Sparse) + CrossEncoder 精排
- **缓存加速**：Redis 缓存 FQA/RAG 答案，重复问题秒级响应
- **数据来源追溯**：RAG 回答附带引用的知识库文档名称

## 技术栈

### 前端

| 技术 | 用途 |
|------|------|
| Vue 3 + Vite | 核心框架 |
| Element Plus | UI 组件库 |
| Vue Router | 路由管理 |
| Axios + Fetch | HTTP 请求 |
| ECharts | 数据可视化 |

### 后端

| 技术 | 用途 |
|------|------|
| Django 5.2 + DRF | Web 框架 + REST API |
| Simple JWT | JWT 双 Token 认证 |
| MySQL | 业务数据库 |
| Redis | 缓存（问答缓存、会话） |
| Milvus | 向量存储与检索 |
| PyTorch + CUDA | 深度学习推理 |

### RAG 模型

| 模型 | 用途 |
|------|------|
| BGE-M3 | 文档/查询向量化（Dense + Sparse） |
| BGE-Reranker-Large | 检索结果精排 |
| BERT-Base-Chinese | 查询意图分类（通用知识/专业咨询） |
| DashScope LLM | 答案生成（通义千问） |

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- MySQL 8.0+
- Redis 7.0+
- Milvus 2.4+
- CUDA 12.6（GPU 推理，可选）

### 1. 克隆项目

```bash
git clone <repo-url>
cd campus_competition
```

### 2. 后端配置

```bash
cd campus_competition_backend

# 创建虚拟环境
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置 .env 文件（参考下方环境变量说明）
cp .env.example .env

# 数据库迁移
python manage.py migrate

# 初始化 FQA 数据（可选）
python manage.py init_rag_data

# 启动开发服务器
python manage.py runserver
```

### 3. 前端配置

```bash
cd campus_competition_frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

### 4. 模型下载

将以下模型下载到 `campus_competition_backend/models/` 目录：

- `bge-m3` — BAAI/BAAI-bge-m3
- `bge-reranker-large` — BAAI/bge-reranker-large
- `bert-base-chinese` — google/bert-base-chinese
- `bert_query_classifier` — 微调后的 BERT 意图分类模型

### 环境变量（.env）

```env
# Django
SECRET_KEY=your-secret-key
DEBUG=True

# MySQL
DB_NAME=campus_competition
DB_USER=root
DB_PASSWORD=your-password
DB_HOST=127.0.0.1
DB_PORT=3306

# Redis
RAG_REDIS_HOST=127.0.0.1
RAG_REDIS_PORT=6379
RAG_REDIS_PASSWORD=
RAG_REDIS_DB=0

# Milvus
RAG_MILVUS_HOST=127.0.0.1
RAG_MILVUS_PORT=19530
RAG_MILVUS_COLLECTION_NAME=edurag
RAG_MILVUS_DATABASE_NAME=itcast

# DashScope LLM
RAG_DASHSCOPE_API_KEY=your-api-key
RAG_DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation
RAG_LLM_MODEL=qwen-plus
```

## 项目结构

```
campus_competition/
├── campus_competition_backend/       # Django 后端
│   ├── api/                          # 业务 API（赛事、用户、报名、通知等）
│   │   ├── models.py                 # 数据模型（User, Competition, Registration 等）
│   │   ├── views.py                  # 业务视图
│   │   ├── serializers.py            # 序列化器
│   │   └── middlewares.py            # 操作日志、全局异常处理中间件
│   ├── rag/                          # RAG 智能问答模块
│   │   ├── core/                     # 核心引擎
│   │   │   ├── rag_system.py         # RAG 检索增强生成主逻辑
│   │   │   ├── vector_store.py       # Milvus 向量存储与混合检索
│   │   │   ├── query_classifier.py   # BERT 查询意图分类器
│   │   │   ├── strategy_selector.py  # 检索策略选择器
│   │   │   ├── document_processor.py # 文档加载与双层切分
│   │   │   └── prompts.py            # 提示词模板
│   │   ├── fqa/                      # FQA 高频问答
│   │   │   ├── bm25_search.py        # BM25 检索 + Redis 缓存
│   │   │   └── preprocess.py         # 文本预处理（jieba 分词）
│   │   ├── loaders/                  # 文档加载器（PDF/DOCX/PPT/IMG）
│   │   ├── splitters/                # 文本分割器（中文递归分割）
│   │   ├── models.py                 # FQA/对话/知识库文档模型
│   │   ├── views.py                  # RAG API 视图
│   │   └── qa_system.py             # 集成问答系统（FQA + RAG + LLM）
│   ├── campus_competition_backend/   # Django 项目配置
│   │   ├── settings.py               # 全局配置
│   │   └── urls.py                   # URL 路由
│   └── models/                       # 本地模型文件
│       ├── bge-m3/
│       ├── bge-reranker-large/
│       ├── bert-base-chinese/
│       └── bert_query_classifier/
│
├── campus_competition_frontend/      # Vue3 前端
│   └── src/
│       ├── views/
│       │   ├── front/                # 前台页面
│       │   │   ├── AIAssistant.vue   # AI 助手（侧边栏+聊天区）
│       │   │   ├── Home.vue          # 首页
│       │   │   ├── CompetitionDetail.vue  # 赛事详情
│       │   │   └── Profile.vue       # 个人中心
│       │   └── admin/                # 后台管理页面
│       ├── components/               # 公共组件
│       │   ├── AIAssistant.vue       # 导航栏 AI 助手弹窗
│       │   └── Header.vue            # 页头导航
│       ├── composables/
│       │   └── useRagChat.js         # RAG 聊天 Composable
│       ├── router/index.js           # 路由配置
│       └── utils/request.js          # Axios 封装（JWT 认证）
│
└── 项目问题与解决.md                  # 开发问题记录
```

## API 接口

### RAG 智能问答

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/rag/query/` | 统一问答（问候语→FQA→RAG，JSON 响应） |
| POST | `/api/rag/stream/` | SSE 流式问答（保留，生产环境可用） |
| POST | `/api/rag/session/` | 创建会话 |
| GET | `/api/rag/sessions/` | 获取当前用户会话列表 |
| GET | `/api/rag/session/{id}/history/` | 获取会话历史 |
| DELETE | `/api/rag/session/{id}/clear_history/` | 清除会话历史 |
| GET | `/api/rag/health/` | 健康检查 |
| GET | `/api/rag/sources/` | 获取学科分类列表 |
| CRUD | `/api/rag/documents/` | 知识库文档管理 |

### 业务 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET/POST | `/api/competitions/` | 赛事列表/创建 |
| GET/PUT/DELETE | `/api/competitions/{id}/` | 赛事详情/编辑/删除 |
| GET/POST | `/api/category-options/` | 赛事分类 |
| GET/POST | `/api/registrations/` | 报名管理 |
| POST | `/api/token/` | JWT 登录 |
| POST | `/api/token/refresh/` | Token 刷新 |
| GET/PUT | `/api/users/me/` | 当前用户信息 |

## RAG 问答流程详解

```
POST /api/rag/query/ {query, session_id}
│
├─ 1. 问候语检测（正则匹配，秒级响应）
│   └─ 命中 → 直接返回问候语
│
├─ 2. 加载 QA 系统（首次触发，加载 BGE-M3/BGE-Reranker/BERT/Milvus，约 30-60s）
│
├─ 3. FQA 检索
│   ├─ Redis 缓存命中 → 直接返回
│   ├─ 精确问题匹配 → 查 MySQL → 写 Redis
│   └─ BM25 语义检索 → 超过阈值 → 查 MySQL → 写 Redis
│
└─ 4. RAG 检索增强生成
    ├─ BERT 意图分类（通用知识 / 专业咨询）
    ├─ 检索策略选择（HyDE / 子查询 / 回溯 / 直接）
    ├─ Milvus 混合检索（Dense + Sparse → RRF 融合 → CrossEncoder 精排）
    ├─ 构建上下文 + 历史对话
    ├─ DashScope LLM 流式生成答案
    └─ 返回 {answer, session_id, source, references}
```

## 开发问题记录

详见 [项目问题与解决.md](./项目问题与解决.md)，涵盖：

1. 前端 AI 页面接入 RAG 功能
2. Milvus 混合检索稀疏向量为空报错
3. 后端服务流式响应后静默崩溃
4. FQA/RAG 答案 Redis 缓存缺失
5. AI 助手新建对话 + 侧边栏历史
6. 用户对话隔离
7. RAG 回答附带数据来源
8. 知识库文档上传后台处理
9. BERT 分类器误判通用知识
10. Windows 控制台 UTF-8 编码

## License

MIT
