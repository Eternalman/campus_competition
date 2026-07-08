"""
RAG 智能问答应用配置

注意：不在 ready() 中加载 ML 模型（会导致 migrate 等管理命令阻塞或崩溃）。
模型通过 rag.core.get_qa_system() 懒加载，仅在首次 API 请求时初始化。
"""
from django.apps import AppConfig


class RagConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'rag'
    verbose_name = 'RAG智能问答'

    def ready(self):
        # 不在此处加载模型，使用懒加载单例模式
        pass