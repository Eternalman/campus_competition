"""
整合 FQA 与 RAG 的问答系统（Django 集成版）。

整体流程：
    1. 初始化系统组件
       1.1 初始化 BM25 检索器（基于 FqaEntry ORM + Django cache）
       1.2 初始化 Milvus 向量存储
       1.3 初始化 RAG 系统（RAGSystem）
       1.4 初始化 OpenAI DashScope 客户端
    2. LLM 流式调用
       2.1 通过 DashScope API 发起流式请求
       2.2 逐块 yield token
       2.3 异常时 yield 错误提示
    3. 对话管理（Django ORM）
       3.1 保存对话记录
       3.2 获取最近 5 轮对话历史（正序）
       3.3 软删除清除对话历史
    4. FQA 检索
       4.1 委托 BM25Search.search() 执行检索
       4.2 返回 (answer, need_rag) 元组
    5. 主流程：问题 -> 答案
       5.1 校验 query 非空
       5.2 读取历史对话
       5.3 先走 FQA 检索
       5.4 FQA 命中直接返回（流式），保存对话
       5.5 需要时再走 RAG 流式生成，保存对话
       5.6 未命中时返回兜底提示
"""

import logging
import re
import time
from typing import List, Optional, Tuple, Generator

from django.conf import settings
from django.core.cache import cache
from openai import OpenAI

from rag.models import FqaEntry, Conversation
# 注意：以下重模块（torch/transformers/sentence_transformers）不在模块级导入，
# 改为在 IntegratedQASystem.__init__ 内延迟导入，避免 Django 管理命令触发 segfault
# from rag.fqa.bm25_search import BM25Search
# from rag.core.rag_system import RAGSystem
# from rag.core.vector_store import VectorStore

logger = logging.getLogger(__name__)


# ======================== 问候语规则 ========================

GREETING_PATTERNS = [
    {
        "pattern": r"^(你好|您好|hi|hello|hey|嗨)",
        "response": "你好！我是校园竞赛智能助手，专注于为学生答疑解惑，很高兴为你服务！",
    },
    {
        "pattern": r"^(你是谁|您是谁|你叫什么|你的名字|who are you)",
        "response": "我是校园竞赛智能助手，你的智能学习助手，致力于提供竞赛相关的解答！",
    },
    {
        "pattern": r"^(在吗|在不在|有人吗)",
        "response": "我在！我是校园竞赛智能助手，随时为你解答问题！",
    },
    {
        "pattern": r"^(干嘛呢|你在干嘛|做什么)",
        "response": "我正在待命，随时为你解答竞赛相关的问题！有什么我可以帮你的？",
    },
    {
        "pattern": r"^(谢谢|多谢|感谢|thanks|thank you|thx)",
        "response": "不客气！如果还有其他竞赛相关问题，随时问我哦！",
    },
    {
        "pattern": r"^(再见|拜拜|bye|see you|回头见|88)",
        "response": "再见！祝你竞赛顺利，取得好成绩！",
    },
    {
        "pattern": r"^(好的|ok|嗯嗯|明白了|知道了|懂了|收到)",
        "response": "好的！还有什么需要帮你了解的吗？",
    },
    {
        "pattern": r"^(吃了吗|你吃饭了吗|你吃了吗|你吃了什么|你吃啥了|你吃了啥)",
        "response": "我不需要吃饭，随时为你解答竞赛相关的问题！有什么我可以帮你的？",
    },
]


def check_greeting(query: str) -> Optional[str]:
    """
    检查用户输入是否为简单问候语。

    命中则返回对应的固定答复，未命中返回 None。
    用于在调用 FQA/RAG 前做规则短路，减少不必要的模型调用开销。

    :param query: 用户输入文本
    :return: 问候语答复字符串，或 None（非问候语）
    """
    query_text = query.strip()
    for pattern_info in GREETING_PATTERNS:
        if re.match(pattern_info["pattern"], query_text, re.IGNORECASE):
            return pattern_info["response"]
    return None


# ======================== 集成问答系统 ========================


class IntegratedQASystem:
    """
    整合 FQA 与 RAG 的问答系统。

    工作流：
        用户 query -> 问候语检测 -> FQA (BM25) -> RAG (Milvus + LLM) -> 流式答案 -> 保存对话历史

    初始化时加载所有 ML 模型（bge-m3, bge-reranker-large, bert_query_classifier）
    并连接 Milvus，耗时约 30-60 秒。通过 rag.core.get_qa_system() 懒加载单例，
    仅在首次 API 请求时执行初始化，不影响 manage.py migrate/shell 等管理命令。
    """

    def __init__(self):
        """初始化所有系统组件。"""
        logger.info("正在初始化 IntegratedQASystem（Django 集成版）...")

        # 延迟导入重模块（torch/transformers/sentence_transformers），
        # 避免在 Django 管理命令中触发 segfault
        from rag.fqa.bm25_search import BM25Search
        from rag.core.vector_store import VectorStore
        from rag.core.rag_system import RAGSystem

        # 1. 初始化 BM25 FQA 检索器
        #    BM25Search 内部使用 FqaEntry.objects.all() 构建索引，
        #    使用 Django cache 做答案缓存，无需额外的 MysqlClient/RedisClient
        self.fqa_bm25search = BM25Search()
        logger.info("BM25 FQA 检索器初始化完成")

        # 2. 初始化 Milvus 向量存储
        #    加载 bge-m3 嵌入模型、bge-reranker-large 精排模型，
        #    连接 Milvus 并加载集合
        self.vector_store = VectorStore()
        logger.info("Milvus 向量存储初始化完成")

        # 3. 初始化 RAG 系统
        #    传入向量存储和 LLM 调用函数，RAGSystem 内部会加载
        #    bert_query_classifier 和 StrategySelector
        self.rag_system = RAGSystem(
            vector_store=self.vector_store,
            llm=self.call_llm,
        )
        logger.info("RAG 系统初始化完成")

        # 4. 初始化 OpenAI DashScope 客户端（用于非 RAG 场景的直接 LLM 调用）
        self.client = OpenAI(
            api_key=settings.RAG_CONFIG["DASHSCOPE_API_KEY"],
            base_url=settings.RAG_CONFIG["DASHSCOPE_BASE_URL"],
        )

        # 5. 保存配置引用（方便内部访问 RAG 参数和客服电话等）
        self.config = settings.RAG_CONFIG

        logger.info("IntegratedQASystem 初始化完成。")

    # ======================== LLM 调用 ========================

    def call_llm(self, prompt: str, system_prompt: str = "") -> Generator[str, None, None]:
        """
        流式调用 DashScope LLM，逐块 yield token。

        同时作为 RAGSystem.generate_answer() 内部的 llm 回调使用。

        :param prompt: 用户提示词（user role）
        :param system_prompt: 系统提示词（system role），为空时不发送 system 消息
        :yield: 每次 yield 一个 token 字符串
        """
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            completion = self.client.chat.completions.create(
                model=settings.RAG_CONFIG["LLM_MODEL"],
                messages=messages,
                temperature=0.1,
                stream=True,
            )
            for chunk in completion:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            yield "抱歉，服务暂时不可用，请稍后重试。"

    # ======================== 对话管理（Django ORM） ========================

    def save_conversation(self, session_id: str, question: str, answer: str, user=None) -> Conversation:
        """
        保存一条对话记录到数据库。

        :param session_id: 会话 ID（UUID4 字符串）
        :param question: 用户问题
        :param answer: 系统回答
        :param user: 关联的用户（可选，None 表示未认证用户）
        :return: 新创建的 Conversation 实例
        """
        try:
            conv = Conversation.objects.create(
                session_id=session_id,
                user=user,
                question=question,
                answer=answer,
            )
            logger.info(f"对话 {session_id} 已保存: {question[:30]}...")
            return conv
        except Exception as e:
            logger.error(f"保存对话失败: {e}")
            raise

    def get_history(self, session_id: str) -> List[dict]:
        """
        获取指定会话最近 5 轮未删除的对话历史（时间正序）。

        :param session_id: 会话 ID
        :return: 对话历史列表，每项为 {"question": ..., "answer": ...}，按时间正序排列
        """
        try:
            conversations = Conversation.objects.filter(
                session_id=session_id,
                is_deleted=False,
            ).order_by("-timestamp")[:5]

            # 倒序查询后用切片反转得到时间正序（最早 -> 最晚）
            history = [
                {"question": c.question, "answer": c.answer}
                for c in conversations
            ]
            return history[::-1]
        except Exception as e:
            logger.error(f"获取对话历史失败: {e}")
            return []

    def clear_history(self, session_id: str) -> bool:
        """
        软删除指定会话的全部对话记录。

        :param session_id: 会话 ID
        :return: True 表示成功，False 表示失败
        """
        try:
            updated_count = Conversation.objects.filter(
                session_id=session_id,
            ).update(is_deleted=True)
            logger.info(f"对话 {session_id} 历史已清除，共标记 {updated_count} 条")
            return True
        except Exception as e:
            logger.error(f"清除对话历史失败: {e}")
            return False

    def get_last_sources(self):
        """返回最近一次 RAG 检索的数据来源列表"""
        if hasattr(self, 'rag_system') and self.rag_system:
            return getattr(self.rag_system, 'last_sources', [])
        return []

    # ======================== FQA 检索 ========================

    def search_fqa(self, query: str) -> Tuple[Optional[str], bool]:
        """
        通过 BM25 检索 FQA 高频问答库。

        :param query: 用户问题
        :return: (answer, need_rag) 元组
                 - answer: 匹配到的答案文本，未命中时为 None
                 - need_rag: 是否需要进一步走 RAG 检索
        """
        return self.fqa_bm25search.search(query)

    # ======================== 主流程：问题 -> 答案 ========================

    def query(
        self,
        query: str,
        source_filter: Optional[str] = None,
        session_id: Optional[str] = None,
        user=None,
    ) -> Generator[Tuple[str, bool], None, None]:
        """
        FQA + RAG 完整问答主流程，流式输出答案。

        工作流：
            输入校验 -> 读取历史 -> FQA 检索 -> RAG 流式生成 -> 保存对话

        :param query: 用户问题
        :param source_filter: 学科过滤（如 "ai", "java"），为 None 时不过滤
        :param session_id: 会话 ID，用于关联对话历史；为 None 时不保存历史
        :param user: 关联的用户（可选）
        :yield: (token, is_complete) 元组
                 - token: 当前输出的文本片段（流式 token）
                 - is_complete: True 表示整个答案已输出完毕
        """
        # 0. 输入校验
        if not query:
            yield "请输入问题!", True
            return

        # 1. 记录开始时间
        start_time = time.time()

        # 2. 读取历史对话
        history = self.get_history(session_id) if session_id else []

        # 3. 先走 FQA 检索
        answer, is_need_rag = self.search_fqa(query)

        # 4. FQA 命中 — 直接返回
        if answer:
            duration = time.time() - start_time
            logger.info(f"FQA 命中，执行时间: {duration:.2f}s")
            if session_id:
                self.save_conversation(
                    session_id=session_id,
                    user=user,
                    question=query,
                    answer=answer,
                )
            yield answer, True
            return

        logger.info(f"FQA 未命中，问题：{query}")

        # 5. 需要走 RAG — 流式生成
        if is_need_rag:
            logger.info(f"尝试查询 RAG 模块，问题：{query}")
            collected_answer = ""
            try:
                for chunk in self.rag_system.generate_answer(
                    query,
                    source_filter=source_filter,
                    history=history,
                ):
                    collected_answer += chunk
                    yield chunk, False

                # RAG 流式输出完毕，保存对话
                if session_id:
                    try:
                        self.save_conversation(
                            session_id=session_id,
                            user=user,
                            question=query,
                            answer=collected_answer,
                        )
                    except Exception as save_err:
                        logger.error(f"保存对话失败: {save_err}")

                duration = time.time() - start_time
                logger.info(f"RAG 查询完成，执行时间: {duration:.2f}s")
                yield "", True
                return
            except Exception as rag_err:
                logger.error(f"RAG 流式生成异常: {rag_err}", exc_info=True)
                yield f"抱歉，服务暂时不可用，请稍后重试。", True
                return

        # 6. 未命中 — 返回兜底提示
        duration = time.time() - start_time
        logger.info(f"未能查询到对应的答案: {duration:.2f}s")
        phone = self.config.get("CUSTOMER_SERVICE_PHONE", "10086")
        yield f"未找到对应的答案。请联系客服：{phone}", True
