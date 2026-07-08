# RAG 智能问答系统迁移计划

## 背景

将 `F:\codes\edu_rag\integrated_qa_system` 中的完整 RAG（检索增强生成）智能问答项目迁移到校园赛事管理系统 `F:\codes\projects\campus_competition` 的 Django 后端中。源项目是基于 FastAPI 的独立服务，需要改造为 Django 应用。

**目标**：在校园赛事管理系统中增加智能问答能力，支持：
- 高频问答（FQA）：MySQL + BM25 关键词匹配，快速回答常见问题
- RAG 深度问答：BERT 分类 → LLM 策略选择 → Milvus 混合检索 → 重排序 → LLM 流式生成
- 会话管理、对话历史
- 可选：与赛事数据联动，回答关于比赛的问题

---

## 架构决策

1. **独立 Django app**：新建 `rag` 应用，放在 `api` 同级，URL 挂载在 `/api/rag/`
2. **数据库统一**：FQA 和对话历史表迁移到现有 `campus_competition` 数据库，使用 Django ORM 管理
3. **缓存替换**：用 Django cache framework + django-redis 替代源项目的 raw Redis 客户端
4. **流式输出**：用 SSE（Server-Sent Events）替代 WebSocket，基于 `StreamingHttpResponse`
5. **模型文件**：已复制到 `campus_competition_backend/models/` 目录下，无需软链接
6. **配置统一**：`config.ini` → Django settings + `.env` 环境变量

---

## 最终 URL 结构

```
/api/rag/session/              POST   创建会话
/api/rag/session/{id}/history/ GET    获取对话历史
/api/rag/session/{id}/         DELETE 清除对话历史
/api/rag/query/                POST   非流式查询（问候语 + FQA）
/api/rag/stream/               POST   SSE 流式查询（完整 RAG）
/api/rag/sources/              GET    获取支持的学科来源
/api/rag/health/               GET    健康检查
```

---

## 实施计划（按顺序执行）

### 阶段 1：创建 rag Django 应用基础结构

**目录结构：**
```
campus_competition_backend/
├── rag/                          # 新建 Django 应用
│   ├── __init__.py
│   ├── apps.py                   # AppConfig，懒加载
│   ├── models.py                 # FqaEntry + Conversation
│   ├── urls.py                   # 路由注册
│   ├── views.py                  # DRF 视图（session/query/stream）
│   ├── serializers.py            # DRF 序列化器
│   ├── migrations/
│   │   └── __init__.py
│   ├── core/                     # RAG 核心管线（从 rag_qa/core/ 迁移）
│   │   ├── __init__.py           # 懒加载单例 get_qa_system()
│   │   ├── rag_system.py         # RAGSystem 调度器（源: rag_qa/core/rag_system.py）
│   │   ├── vector_store.py       # Milvus 向量存储（源: rag_qa/core/vector_store.py）
│   │   ├── query_classifier.py   # BERT 分类器（源: rag_qa/core/query_classifier.py）
│   │   ├── strategy_selector.py  # LLM 策略选择器（源: rag_qa/core/strategy_selector.py）
│   │   ├── document_processor.py # 文档加载+切分（源: rag_qa/core/document_processor.py）
│   │   └── prompts.py            # 提示词模板（源: rag_qa/core/prompts.py）
│   ├── loaders/                  # 文档加载器（从 rag_qa/edu_document_loaders/ 迁移）
│   │   ├── __init__.py
│   │   ├── edu_docloader.py
│   │   ├── edu_pdfloader.py
│   │   ├── edu_pptloader.py
│   │   ├── edu_imgloader.py
│   │   └── edu_ocr.py
│   ├── splitters/                # 文本分割器（从 rag_qa/edu_text_spliter/ 迁移）
│   │   ├── __init__.py
│   │   ├── edu_chinese_recursive_text_splitter.py
│   │   └── edu_model_text_spliter.py
│   ├── fqa/                      # FQA 模块（从 mysql_qa/ 迁移）
│   │   ├── __init__.py
│   │   ├── bm25_search.py        # BM25 检索器
│   │   └── preprocess.py         # jieba 分词
│   ├── management/               # Django 管理命令
│   │   └── commands/
│   │       ├── __init__.py
│   │       └── init_rag_data.py  # RAG 数据初始化
│   └── data/                     # 静态数据
│       ├── JP学科知识问答.csv     # FQA 种子数据
│       └── model_generic.json     # BERT 训练数据
└── models/                        # ML 模型（已从源项目复制）
    ├── bert-base-chinese/
    ├── bert_query_classifier/
    ├── bge-m3/
    └── bge-reranker-large/
```

**操作步骤：**
1. 创建 `rag/` 目录及所有子目录
2. 编写 `rag/apps.py`（含懒加载逻辑，不在启动时加载 ML 模型）
3. 在 `settings.py` 的 `INSTALLED_APPS` 中注册 `'rag'`
4. 在根 `urls.py` 中添加 `path('api/rag/', include('rag.urls'))`

### 阶段 2：Django ORM 模型 + 数据库迁移

**`rag/models.py` 内容：**
- `FqaEntry`：高频问答对（`subject_name`, `question` unique, `answer`），对应源项目 `jpkb` 表
- `Conversation`：对话历史（`session_id`, `question`, `answer`, `timestamp`, `is_deleted`），对应源项目 `conversations` 表

**操作步骤：**
1. 编写 `rag/models.py`
2. 运行 `python manage.py makemigrations rag`
3. 运行 `python manage.py migrate`

### 阶段 3：配置集成

**在 `settings.py` 中新增：**
- `RAG_CONFIG` 字典：LLM（DashScope API）、Milvus、Redis、检索参数等（从 `config.ini` 映射，通过环境变量覆盖）
- `CACHES` 配置：django-redis，24h TTL
- `LOGGING` 配置：增加 `rag` logger（控制台 + 文件）

**操作步骤：**
1. 将 `config.ini` 各节转换为 `RAG_CONFIG` 字典
2. 添加 `django-redis` 缓存配置
3. 将 API key 等敏感信息移到 `.env` 文件
4. 更新 `.gitignore` 添加 `.env`

### 阶段 4：复制并适配 RAG 核心代码

**文件复制映射（源 → 目标）：**

| 源路径 | 目标路径 | 修改内容 |
|--------|----------|----------|
| `rag_qa/core/rag_system.py` | `rag/core/rag_system.py` | config→Django settings，logger→Django logging，去掉 `__main__` |
| `rag_qa/core/vector_store.py` | `rag/core/vector_store.py` | config→settings，模型路径修正 |
| `rag_qa/core/query_classifier.py` | `rag/core/query_classifier.py` | 模型路径改为 `settings.RAG_CONFIG['MODELS_DIR']` |
| `rag_qa/core/strategy_selector.py` | `rag/core/strategy_selector.py` | config→settings |
| `rag_qa/core/document_processor.py` | `rag/core/document_processor.py` | 更新加载器/分割器导入路径 |
| `rag_qa/core/prompts.py` | `rag/core/prompts.py` | **重写提示词**：从 IT 教育领域改为校园竞赛领域 |
| `rag_qa/edu_document_loaders/*` | `rag/loaders/*` | 更新内部导入路径 |
| `rag_qa/edu_text_spliter/*` | `rag/splitters/*` | 更新内部导入路径 |
| `mysql_qa/retrieval/bm25_search.py` | `rag/fqa/bm25_search.py` | 用 Django ORM 替代 MysqlClient，用 Django cache 替代 RedisClient |
| `mysql_qa/utils/preprocess.py` | `rag/fqa/preprocess.py` | 更新导入 |

**核心导入修改模式：**
```python
# 之前
from base.config import config
from base.logger import logger

# 之后
from django.conf import settings
config = settings.RAG_CONFIG
import logging
logger = logging.getLogger(__name__)
```

**关键改写：**
- **BM25 检索器**：`self.mysql_client.fetch_questions()` → `FqaEntry.objects.values_list('question', flat=True)`；`self.redis_client.get_answer(q)` → `cache.get(f"answer:{q}")`
- **对话历史**：raw SQL → `Conversation.objects.filter(session_id=..., is_deleted=False)`
- **模型路径**：不再使用 `__file__` 的相对路径推导，统一从 `RAG_CONFIG['MODELS_DIR']` 读取
- **日志**：所有 `logger.info/error/warning` 改为 `logging.getLogger(__name__)`

### 阶段 5：创建 DRF 视图和路由

**`rag/views.py` 核心视图：**

1. **`RagSessionViewSet`** — 会话管理
   - `create`：生成 UUID session_id
   - `get_history`：查询最近 5 轮对话
   - `clear_history`：软删除

2. **`RagQueryView`** — 非流式查询（先走问候语 → FQA，命中直接返回；未命中返回 `is_streaming: true` 引导前端用 SSE）

3. **`RagStreamView`** — SSE 流式查询，完整 RAG 管线：
   - `event: start` → `event: token` × N → `event: end` / `event: error`
   - 使用 Django `StreamingHttpResponse`

4. **`RagSourcesView`** — 返回有效学科来源
5. **`RagHealthView`** — 健康检查（不加载模型）

**`rag/urls.py`**：使用 `DefaultRouter` 注册 ViewSet + 显式 `path()` 注册 APIView

**懒加载单例 `rag/core/__init__.py`：**
```python
_qa_system = None
def get_qa_system():
    global _qa_system
    if _qa_system is None:
        # 首次请求时才加载 ML 模型和 Milvus 连接
        _qa_system = IntegratedQASystem()
    return _qa_system
```

### 阶段 6：创建 Django 管理命令

**`rag/management/commands/init_rag_data.py`**：
- 导入 FQA CSV 到 `FqaEntry` 表
- 检查 Milvus 集合，若为空则构建向量索引
- 用法：`python manage.py init_rag_data`

### 阶段 7：安装依赖

需要新增安装的包（用户说已安装，确认清单）：
```
langchain, pymilvus, milvus-model, sentence-transformers, transformers,
jieba, rank-bm25, scikit-learn, python-docx, python-pptx, PyMuPDF,
opencv-python, rapidocr-onnxruntime, torch, django-redis, openai
```

### 阶段 8：重写提示词模板（IT 教育 → 校园竞赛）

源项目提示词面向 **IT 教育领域**（黑马程序员），需要全部改写为 **校园竞赛** 场景。

**`rag/core/prompts.py` 改写对照：**

| 方法 | 原内容 | 改写后 |
|------|--------|--------|
| `rag_system_prompt()` | "IT教育领域智能助手，面向学生和教育从业者" | "校园赛事智能助手，面向参赛学生、评委和管理员" |
| `general_system_prompt()` | "IT教育领域智能助手" | "校园赛事智能助手" |
| `strategy_system_prompt()` | 保持不变（通用指令执行） | 保持不变 |
| `rag_prompt()` | `{phone}` 客服电话 | 保留 `{phone}` 变量，示例改为赛事相关 |
| `general_prompt()` | 通用知识回答 | 微调为校园竞赛语境 |
| `hyde_prompt()` | 假设答案生成 | 不变（与领域无关） |
| `subquery_prompt()` | 子查询分解 | 不变（与领域无关） |
| `backtracking_prompt()` | 查询简化 | 不变（与领域无关） |

**改写后的 system prompt：**
- RAG 模式：`"你是一名专业的校园赛事智能助手，面向参赛学生、评委和管理员。回答应准确、清晰、简洁，易于理解。仅基于提供的上下文回答，禁止使用自身知识。"`
- 通用模式：`"你是一名专业的校园赛事智能助手。请根据你的知识准确、清晰、简洁地回答用户问题。"`

### 阶段 9：模型文件确认

4 个 ML 模型已复制到 `campus_competition_backend/models/`：
- `bert-base-chinese/`
- `bert_query_classifier/`
- `bge-m3/`
- `bge-reranker-large/`

`RAG_CONFIG['MODELS_DIR']` 指向 `BASE_DIR / 'models'` 即可。

---

## 不需要迁移的部分

- `app.py` → 被 DRF views 替代
- `old_main.py` → 旧版架构，不需要
- `base/config.py`、`base/logger.py` → 被 Django settings/logging 替代
- `mysql_qa/db/mysql_client.py` → 被 Django ORM 替代
- `mysql_qa/cache/redis_client.py` → 被 Django cache 替代
- `static/` → 前端由 Vue 3 重写，不需要旧 HTML
- `rag_qa/rag_assesment/` → 评估工具，后续有需要再迁移
- `rag_qa/main.py` → 独立入口，不需要

---

## 风险与注意事项

1. **模型加载阻塞**：采用懒加载单例模式，4 个 ML 模型（几 GB）仅在首次 API 请求时加载，不影响 `migrate`、`shell` 等管理命令
2. **SSE 与 WSGI**：开发环境 `runserver` 可处理 SSE；生产环境需用 Daphne/Uvicorn（已有 `asgi.py`）
3. **pymysql vs mysqlclient**：源项目用 pymysql，目标用 mysqlclient，无冲突（删除 mysql_client.py 后不再需要 pymysql）
4. **API Key 安全**：`config.ini` 中有硬编码的 DashScope API Key，迁移到 `.env`，加入 `.gitignore`

---

## 验证清单

RAG 系统依赖链：**Django → MySQL → Redis → FQA数据 → Milvus → ML模型 → LLM API**

验证从简到繁，逐层确认：

### 第 1 层：基础健康检查（不加载 ML 模型，秒级）

```bash
# 1. Django 配置
python manage.py check

# 2. 启动开发服务器
python manage.py runserver

# 3. 健康检查（另一个终端）
curl http://localhost:8000/api/rag/health/
# 预期: {"status": "healthy"}

# 4. 学科来源
curl http://localhost:8000/api/rag/sources/
# 预期: {"valid_sources": ["ai","java","test","ops","bigdata"]}
```

### 第 2 层：会话管理（不加载 ML 模型，秒级）

```bash
# 1. 创建会话
curl -X POST http://localhost:8000/api/rag/session/
# 预期: {"session_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"}

# 记录返回的 session_id，后续测试使用
SESSION_ID="<上面返回的 session_id>"

# 2. 获取历史（空会话）
curl http://localhost:8000/api/rag/session/$SESSION_ID/history/
# 预期: {"session_id": "...", "history": []}
```

### 第 3 层：问候语 + 简单问答（不加载 ML 模型，秒级）

```bash
# 1. 问候语测试
curl -X POST http://localhost:8000/api/rag/query/ \
  -H "Content-Type: application/json" \
  -d '{"query": "你好", "session_id": "'$SESSION_ID'"}'
# 预期: {"answer": "你好！我是校园竞赛智能助手...", "source": "greeting"}

# 2. 感谢语测试
curl -X POST http://localhost:8000/api/rag/query/ \
  -H "Content-Type: application/json" \
  -d '{"query": "谢谢", "session_id": "'$SESSION_ID'"}'
# 预期: {"answer": "不客气！...", "source": "greeting"}
```

### 第 4 层：FQA 数据导入 + 检索（需要 MySQL，不需要 Milvus）

```bash
# 1. 导入 FQA 种子数据（约 300+ 条问答对）
python manage.py init_rag_data
# 预期: 显示导入进度和统计信息

# 2. 测试 FQA 命中（CSV 中已有问题）
curl -X POST http://localhost:8000/api/rag/query/ \
  -H "Content-Type: application/json" \
  -d '{"query": "Python是什么", "session_id": "'$SESSION_ID'"}'
# 预期: {"answer": "...Python是一种...", "source": "fqa"}

# 3. FQA 未命中 → 应提示需要 RAG
curl -X POST http://localhost:8000/api/rag/query/ \
  -H "Content-Type: application/json" \
  -d '{"query": "校园程序设计竞赛什么时候开始报名", "session_id": "'$SESSION_ID'"}'
# 预期: {"is_streaming": true, "message": "需要使用流式接口获取答案..."}
```

### 第 5 层：完整 RAG 流式问答（需要 Milvus + ML 模型 + LLM API）

**前提条件**：
- Milvus 服务运行中（`127.0.0.1:19530`）
- 知识库文档已向量化存入 Milvus
- 网络可访问 DashScope API

```bash
# 1. SSE 流式查询（首次会加载 4 个 ML 模型，约 30-60 秒）
curl -X POST http://localhost:8000/api/rag/stream/ \
  -H "Content-Type: application/json" \
  -d '{"query": "大模型要学哪些知识？", "session_id": "'$SESSION_ID'"}' \
  --no-buffer
# 预期: 逐 token 流式输出 SSE 事件
#   event: start
#   event: token {"token": "大"}
#   event: token {"token": "模型"}
#   ...
#   event: end {"is_complete": true, "processing_time": 3.5}

# 2. 验证对话历史已保存
curl http://localhost:8000/api/rag/session/$SESSION_ID/history/
# 预期: 返回刚才的问答对

# 3. 清除历史
curl -X DELETE http://localhost:8000/api/rag/session/$SESSION_ID/
# 预期: {"session_id": "...", "cleared": true}
```

### 验证通过标准

| 层级 | 验证内容 | 依赖 | 通过标志 |
|------|----------|------|----------|
| 1 | 基础健康 | Django 启动 | health 返回 200 |
| 2 | 会话管理 | 无 | 创建/查询/删除正常 |
| 3 | 问候语 | 无 | 返回校园竞赛相关问候 |
| 4 | FQA | MySQL + CSV 数据 | 命中返回答案 |
| 5 | RAG 流式 | Milvus + 模型 + API | SSE 流式输出 token |

### 常见问题排查

| 症状 | 可能原因 | 排查命令 |
|------|----------|----------|
| health 返回 500 | settings 配置错误 | `python manage.py check` |
| init_rag_data 失败 | CSV 文件缺失 | `ls rag/data/JP学科知识问答.csv` |
| FQA 不命中 | BM25 阈值过高 | 检查 bm25_search.py 阈值参数 |
| RAG 流式超时 | Milvus 未启动 | `docker ps \| grep milvus` |
| RAG 流式报错 | DashScope API Key 无效 | 检查 settings.py 中 DASHSCOPE_API_KEY |
