import json
import os
import time
import uuid
import threading

from django.conf import settings
from django.http import StreamingHttpResponse
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from rag.core import get_qa_system
from rag.qa_system import check_greeting
from rag.serializers import (
    RagQuerySerializer, StreamQuerySerializer, KnowledgeDocumentSerializer,
)


# ======================== Session ViewSet ========================

class RagSessionViewSet(GenericViewSet):
    """会话管理：创建会话、获取历史、清除历史。"""
    permission_classes = [AllowAny]

    def _get_user(self, request):
        """返回已认证用户，未认证返回 None"""
        return request.user if request.user.is_authenticated else None

    def create(self, request):
        """POST /session/ — 生成新会话 ID。"""
        session_id = str(uuid.uuid4())
        return Response({"session_id": session_id}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"], url_path="history")
    def get_history(self, request, pk=None):
        """GET /session/{pk}/history/ — 获取最近 5 轮对话历史（按用户隔离）。"""
        from rag.models import Conversation
        user = self._get_user(request)
        qs = Conversation.objects.filter(session_id=pk, is_deleted=False)
        if user:
            # 已登录：只看自己的对话，以及迁移前 user=NULL 的旧数据
            from django.db.models import Q
            qs = qs.filter(Q(user=user) | Q(user__isnull=True))
        history_qs = qs.order_by('-timestamp')[:5]
        history = [
            {"question": h.question, "answer": h.answer}
            for h in reversed(history_qs)
        ]
        return Response({"session_id": pk, "history": history})

    @action(detail=True, methods=["delete"])
    def clear_history(self, request, pk=None):
        """DELETE /session/{pk}/clear_history/ — 清除会话全部对话历史（按用户隔离）。"""
        from rag.models import Conversation
        user = self._get_user(request)
        qs = Conversation.objects.filter(session_id=pk, is_deleted=False)
        if user:
            from django.db.models import Q
            qs = qs.filter(Q(user=user) | Q(user__isnull=True))
        updated = qs.update(is_deleted=True)
        return Response({"session_id": pk, "cleared": True, "deleted_count": updated})


# ======================== 非流式查询 ========================

class RagQueryView(APIView):
    """
    POST /query/ — 统一查询接口（非流式）。

    流程：问候语 → FQA → RAG（内部收集完整 LLM 输出后一次性返回 JSON）。
    不使用 StreamingHttpResponse，避免 Django 开发服务器的流式兼容问题。
    """
    permission_classes = [AllowAny]

    def post(self, request):
        import logging
        logger = logging.getLogger(__name__)

        serializer = RagQuerySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        query = serializer.validated_data["query"]
        session_id = serializer.validated_data.get("session_id") or str(uuid.uuid4())
        source_filter = serializer.validated_data.get("source_filter") or None
        user = request.user if request.user.is_authenticated else None

        # 1. 问候语检测（不加载 ML 模型，秒级响应）
        greeting = check_greeting(query)
        if greeting:
            if session_id:
                from rag.models import Conversation
                Conversation.objects.create(
                    session_id=session_id, user=user, question=query, answer=greeting
                )
            return Response({
                "answer": greeting,
                "session_id": session_id,
                "source": "greeting",
            })

        # 2. 加载 QA 系统（首次触发 ML 模型加载，30-60 秒）
        qa = get_qa_system()

        # 3. FQA 检索
        answer, need_rag = qa.search_fqa(query)
        if answer:
            if session_id:
                qa.save_conversation(session_id=session_id, user=user, question=query, answer=answer)
            return Response({
                "answer": answer,
                "session_id": session_id,
                "source": "fqa",
            })

        # 4. RAG 流式生成 — 内部收集完整答案，一次性返回
        if need_rag:
            try:
                collected_answer = ""
                for token, is_complete in qa.query(
                    query, source_filter=source_filter, session_id=session_id, user=user
                ):
                    if token:
                        collected_answer += token
                    if is_complete:
                        break

                # 回写 Redis 缓存，下次同样问题直接从缓存命中（跳过 RAG 全流程）
                if collected_answer:
                    from django.core.cache import cache
                    cache.set(f"answer:{query}", collected_answer, timeout=86400)

                # 获取 RAG 检索引用的数据来源（stored_name → original_name）
                references = []
                stored_sources = qa.get_last_sources()
                if stored_sources:
                    from rag.models import KnowledgeDocument
                    doc_map = {
                        d.stored_name: d.original_name
                        for d in KnowledgeDocument.objects.filter(stored_name__in=stored_sources)
                    }
                    for s in stored_sources:
                        references.append(doc_map.get(s, s))

                return Response({
                    "answer": collected_answer,
                    "session_id": session_id,
                    "source": "rag",
                    "references": references,
                })
            except Exception as e:
                logger.error(f"RAG 查询异常: {e}", exc_info=True)
                return Response({
                    "answer": "抱歉，服务暂时不可用，请稍后重试。",
                    "session_id": session_id,
                    "source": "error",
                })

        # 5. 未命中
        phone = settings.RAG_CONFIG.get("CUSTOMER_SERVICE_PHONE", "10086")
        return Response({
            "answer": f"未找到对应的答案。请联系客服：{phone}",
            "session_id": session_id,
            "source": "fallback",
        })


# ======================== SSE 流式查询 ========================

class RagStreamView(APIView):
    """
    POST /stream/ — SSE 流式查询。

    事件格式：event: <name>\\ndata: <json>\\n\\n
    事件类型：start → token* → end | error
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = StreamQuerySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        query = serializer.validated_data["query"]
        session_id = serializer.validated_data.get("session_id") or str(uuid.uuid4())
        source_filter = serializer.validated_data.get("source_filter") or None

        response = StreamingHttpResponse(
            self._event_stream(query, session_id, source_filter),
            content_type="text/event-stream",
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response

    def _event_stream(self, query, session_id, source_filter):
        """生成器：逐事件产出 SSE 格式数据。"""
        import logging
        logger = logging.getLogger(__name__)
        start_time = time.time()

        yield f"event: start\ndata: {json.dumps({'session_id': session_id})}\n\n"

        try:
            # 1. 问候语检测（不加载 ML 模型，秒级响应）
            greeting = check_greeting(query)
            if greeting:
                if session_id:
                    from rag.models import Conversation
                    Conversation.objects.create(
                        session_id=session_id, question=query, answer=greeting
                    )
                yield f"event: token\ndata: {json.dumps({'token': greeting})}\n\n"
                yield f"event: end\ndata: {json.dumps({'is_complete': True, 'processing_time': time.time() - start_time})}\n\n"
                return

            # 2. 加载 QA 系统（首次触发 ML 模型加载）
            qa = get_qa_system()

            # FQA 先检索
            answer, need_rag = qa.search_fqa(query)
            if answer:
                if session_id:
                    qa.save_conversation(session_id=session_id, question=query, answer=answer)
                yield f"event: token\ndata: {json.dumps({'token': answer})}\n\n"
                yield f"event: end\ndata: {json.dumps({'is_complete': True, 'processing_time': time.time() - start_time})}\n\n"
                return

            if not need_rag:
                phone = settings.RAG_CONFIG.get("CUSTOMER_SERVICE_PHONE", "10086")
                fallback = f"未找到对应的答案。请联系客服：{phone}"
                if session_id:
                    qa.save_conversation(session_id=session_id, question=query, answer=fallback)
                yield f"event: token\ndata: {json.dumps({'token': fallback})}\n\n"
                yield f"event: end\ndata: {json.dumps({'is_complete': True, 'processing_time': time.time() - start_time})}\n\n"
                return

            # Full RAG streaming
            collected = ""
            for token, is_complete in qa.query(
                query, source_filter=source_filter, session_id=session_id
            ):
                if token:
                    collected += token
                    yield f"event: token\ndata: {json.dumps({'token': token})}\n\n"
                if is_complete:
                    yield f"event: end\ndata: {json.dumps({'is_complete': True, 'processing_time': time.time() - start_time})}\n\n"
                    return

        except Exception as e:
            logger.error(f"SSE 流式处理异常: {e}", exc_info=True)
            yield f"event: error\ndata: {json.dumps({'error': '服务器内部错误，请稍后重试'})}\n\n"


# ======================== 辅助视图 ========================

class RagSessionListView(APIView):
    """GET /sessions/ — 返回当前用户的会话列表（去重，含首条问题标题）。"""
    permission_classes = [AllowAny]

    def get(self, request):
        from django.db.models import Max, OuterRef, Subquery, Q
        from rag.models import Conversation
        import logging
        logger = logging.getLogger(__name__)

        user = request.user if request.user.is_authenticated else None
        logger.info(f"会话列表查询: user={user}, authenticated={request.user.is_authenticated}")

        # 子查询：每个 session 最早一条记录的 question
        first_q = Conversation.objects.filter(
            session_id=OuterRef('session_id'), is_deleted=False,
        ).order_by('timestamp').values('question')[:1]

        qs = Conversation.objects.filter(is_deleted=False)
        if user:
            # 已登录：看自己的 + 迁移前 user=NULL 的旧数据
            qs = qs.filter(Q(user=user) | Q(user__isnull=True))
            first_q = first_q.filter(Q(user=user) | Q(user__isnull=True))

        sessions = (
            qs.values('session_id')
            .annotate(
                title=Subquery(first_q),
                updated_at=Max('timestamp'),
            )
            .order_by('-updated_at')
        )

        result = [
            {
                "session_id": s["session_id"],
                "title": (s["title"] or "新对话")[:50],
                "updated_at": s["updated_at"].isoformat() if s["updated_at"] else None,
            }
            for s in sessions
        ]
        logger.info(f"返回 {len(result)} 个会话")

        return Response({"sessions": result})


class RagSourcesView(APIView):
    """GET /sources/ — 返回有效学科过滤列表。"""
    permission_classes = [AllowAny]

    def get(self, request):
        valid_sources = settings.RAG_CONFIG.get("VALID_SOURCES", [])
        return Response({"valid_sources": valid_sources})


class RagHealthView(APIView):
    """GET /health/ — 健康检查。"""
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"status": "healthy"})


# ======================== 知识库文档管理 ========================

SUPPORTED_EXTENSIONS = {
    '.txt', '.pdf', '.docx', '.ppt', '.pptx',
    '.jpg', '.png', '.md', '.csv', '.xlsx', '.xls',
}


class KnowledgeDocumentViewSet(ModelViewSet):
    """知识库文档 CRUD — 上传自动处理、删除清理 Milvus"""
    permission_classes = [AllowAny]  # 临时：开发阶段放开，生产改为 IsAdminUser
    parser_classes = [MultiPartParser, FormParser]
    serializer_class = KnowledgeDocumentSerializer

    def get_queryset(self):
        from rag.models import KnowledgeDocument
        return KnowledgeDocument.objects.all().order_by('-created_at')

    def create(self, request, *args, **kwargs):
        """上传文档 → 保存文件 → 创建记录 → 后台异步处理"""
        from rag.models import KnowledgeDocument

        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return Response({'error': '请选择要上传的文件'}, status=400)

        # 校验文件类型
        ext = os.path.splitext(uploaded_file.name)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            return Response(
                {'error': f'不支持的文件类型：{ext}，仅支持：{",".join(sorted(SUPPORTED_EXTENSIONS))}'},
                status=400,
            )

        # 保存文件
        unique_name = f"{uuid.uuid4().hex}{ext}"
        save_dir = os.path.join(str(settings.MEDIA_ROOT), 'knowledge_base')
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, unique_name)
        with open(save_path, 'wb+') as f:
            for chunk in uploaded_file.chunks():
                f.write(chunk)

        source = request.data.get('source', 'general')

        # 创建数据库记录
        doc = KnowledgeDocument.objects.create(
            original_name=uploaded_file.name,
            stored_name=unique_name,
            file_path=save_path,
            file_size=uploaded_file.size,
            file_type=ext.lstrip('.'),
            source=source,
            status='uploaded',
        )

        # 后台异步处理
        threading.Thread(
            target=self._process_document,
            args=(doc.id,),
            daemon=True,
        ).start()

        serializer = self.get_serializer(doc)
        return Response(serializer.data, status=201)

    def destroy(self, request, *args, **kwargs):
        """删除文档 — 清理文件 + Milvus 向量 + 数据库记录"""
        from rag.models import KnowledgeDocument

        doc = self.get_object()

        errors = []

        # 1. 删除 Milvus 中的向量
        try:
            qa = get_qa_system()
            vs = qa.vector_store
            # 用 stored_name 作为 source 过滤器删除
            expr = f"source == '{doc.stored_name}'"
            vs.client.delete(
                collection_name=vs.collection_name,
                filter=expr,
            )
        except Exception as e:
            errors.append(f"Milvus清理失败: {e}")

        # 2. 删除服务器文件
        try:
            if os.path.exists(doc.file_path):
                os.remove(doc.file_path)
        except Exception as e:
            errors.append(f"文件删除失败: {e}")

        # 3. 删除数据库记录
        doc.delete()

        if errors:
            return Response(
                {'deleted': True, 'warnings': errors},
                status=200,
            )
        return Response({'deleted': True}, status=200)

    @action(detail=True, methods=['post'], url_path='reprocess')
    def reprocess(self, request, pk=None):
        """重新处理文档"""
        doc = self.get_object()
        if doc.status == 'processing':
            return Response({'error': '文档正在处理中，请稍候'}, status=400)

        doc.status = 'uploaded'
        doc.error_message = ''
        doc.save()

        threading.Thread(
            target=self._process_document,
            args=(doc.id,),
            daemon=True,
        ).start()

        return Response({'message': '已重新提交处理', 'id': doc.id})

    @staticmethod
    def _process_document(doc_id):
        """后台处理文档：加载 → 切分 → 向量化 → 写入 Milvus"""
        import logging
        import traceback
        logger = logging.getLogger(__name__)

        # 后台线程必须关闭主线程遗留的旧数据库连接，否则 ORM 操作会报
        # "DatabaseWrapper objects created in a thread can only be used in that same thread"
        from django.db import connections
        for conn_name in connections:
            connections[conn_name].close_if_unusable_or_obsolete()

        from rag.models import KnowledgeDocument
        from rag.core.document_processor import process_documents

        doc = None
        try:
            doc = KnowledgeDocument.objects.get(id=doc_id)
        except KnowledgeDocument.DoesNotExist:
            logger.error(f"文档不存在: {doc_id}")
            return

        # 更新状态为处理中
        doc.status = 'processing'
        doc.save()

        try:
            logger.info(f"开始处理文档: {doc.original_name} (stored: {doc.stored_name})")

            # 1. 先复制到临时目录（process_documents 需要目录路径）
            temp_dir = os.path.join(str(settings.MEDIA_ROOT), 'knowledge_base', f"_temp_{doc.stored_name}")
            os.makedirs(temp_dir, exist_ok=True)
            import shutil
            shutil.copy2(doc.file_path, os.path.join(temp_dir, doc.original_name))

            # 2. 加载并处理
            child_chunks = process_documents(temp_dir)
            logger.info(f"文档切分完成: {len(child_chunks)} 个子块")

            # 清理临时目录
            shutil.rmtree(temp_dir, ignore_errors=True)

            if not child_chunks:
                doc.status = 'failed'
                doc.error_message = '文档内容为空或无法解析'
                doc.save()
                logger.error(f"文档处理失败（无内容）: {doc.original_name}")
                return

            # 3. 写入 Milvus
            logger.info(f"开始写入 Milvus, 子块数: {len(child_chunks)}")
            qa = get_qa_system()
            vs = qa.vector_store
            # 给每个 chunk 打上该文档的 source 标记
            for chunk in child_chunks:
                chunk.metadata['source'] = doc.stored_name
            vs.add_documents(child_chunks)
            logger.info(f"Milvus 写入完成")

            # 4. 更新状态
            doc.status = 'completed'
            doc.chunk_count = len(child_chunks)
            doc.save()
            logger.info(f"文档处理完成: {doc.original_name}, 子块数: {len(child_chunks)}")

        except Exception as e:
            logger.error(f"文档处理失败: {getattr(doc, 'original_name', 'unknown')}\n{traceback.format_exc()}")
            if doc is not None:
                try:
                    doc.status = 'failed'
                    doc.error_message = str(e)[:500]
                    doc.save()
                except Exception as save_err:
                    logger.error(f"保存失败状态时出错: {save_err}")
