"""
RAG 核心模块 — 懒加载单例

ML 模型（~4GB）仅在首次调用 get_qa_system() 时加载，
避免阻塞 python manage.py migrate / shell 等管理命令。
"""
import logging

logger = logging.getLogger(__name__)

_qa_system = None


def get_qa_system():
    """
    获取 IntegratedQASystem 单例。

    首次调用时加载全部 ML 模型（bert, bge-m3, bge-reranker）
    并连接 Milvus，耗时约 30-60 秒。后续调用直接返回已加载的实例。
    """
    global _qa_system
    if _qa_system is None:
        logger.info("首次加载 RAG 系统，正在初始化 ML 模型和 Milvus 连接...")
        from rag.qa_system import IntegratedQASystem
        _qa_system = IntegratedQASystem()
        logger.info("RAG 系统初始化完成。")
    return _qa_system


def reset_qa_system():
    """重置 RAG 系统实例（用于开发调试或热重载）"""
    global _qa_system
    _qa_system = None
    logger.info("RAG 系统实例已重置。")
