from django.db import models
from django.conf import settings


class FqaEntry(models.Model):
    """FQA 高频问答对（映射源项目 jpkb 表）"""
    subject_name = models.CharField(max_length=50, verbose_name='学科名称')
    question = models.CharField(max_length=255, unique=True, verbose_name='问题')
    answer = models.TextField(verbose_name='答案')

    class Meta:
        db_table = 'rag_fqa_entry'
        verbose_name = 'FQA问答对'
        verbose_name_plural = 'FQA问答对'

    def __str__(self):
        return self.question[:50]


class Conversation(models.Model):
    """RAG 对话历史（映射源项目 conversations 表）"""
    session_id = models.CharField(max_length=36, db_index=True, verbose_name='会话ID')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        null=True, blank=True, db_index=True, verbose_name='所属用户'
    )
    question = models.TextField(verbose_name='用户问题')
    answer = models.TextField(verbose_name='系统回答')
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='对话时间')
    is_deleted = models.BooleanField(default=False, verbose_name='是否删除')

    class Meta:
        db_table = 'rag_conversation'
        verbose_name = '对话记录'
        verbose_name_plural = '对话记录'
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.session_id[:8]}... - {self.question[:30]}"


class KnowledgeDocument(models.Model):
    """知识库文档，追踪上传和处理状态"""
    STATUS_CHOICES = (
        ('uploaded', '已上传'),
        ('processing', '处理中'),
        ('completed', '已完成'),
        ('failed', '失败'),
    )
    original_name = models.CharField(max_length=255, verbose_name='原始文件名')
    stored_name = models.CharField(max_length=255, verbose_name='存储文件名')
    file_path = models.CharField(max_length=500, verbose_name='完整存储路径')
    file_size = models.BigIntegerField(default=0, verbose_name='文件大小(bytes)')
    file_type = models.CharField(max_length=10, verbose_name='文件类型')
    source = models.CharField(max_length=50, default='general', verbose_name='学科分类')
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='uploaded', verbose_name='处理状态'
    )
    chunk_count = models.IntegerField(default=0, verbose_name='切分子块数')
    error_message = models.TextField(blank=True, default='', verbose_name='错误信息')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='上传时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'rag_knowledge_document'
        verbose_name = '知识库文档'
        verbose_name_plural = '知识库文档'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.original_name} ({self.get_status_display()})"
