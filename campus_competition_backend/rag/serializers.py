from rest_framework import serializers

class RagQuerySerializer(serializers.Serializer):
    query = serializers.CharField(required=True)
    session_id = serializers.CharField(required=False, allow_blank=True)
    source_filter = serializers.CharField(required=False, allow_blank=True)

class StreamQuerySerializer(serializers.Serializer):
    query = serializers.CharField(required=True)
    session_id = serializers.CharField(required=False, allow_blank=True)
    source_filter = serializers.CharField(required=False, allow_blank=True)


class KnowledgeDocumentSerializer(serializers.ModelSerializer):
    """知识库文档序列化器"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        from rag.models import KnowledgeDocument
        model = KnowledgeDocument
        fields = '__all__'
        read_only_fields = [
            'id', 'stored_name', 'file_path', 'file_size',
            'file_type', 'status', 'chunk_count', 'error_message',
            'created_at', 'updated_at',
        ]