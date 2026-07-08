from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RagSessionViewSet, RagQueryView, RagStreamView, RagSourcesView, RagHealthView,
    KnowledgeDocumentViewSet, RagSessionListView,
)

router = DefaultRouter()
router.register('session', RagSessionViewSet, basename='rag-session')
router.register('documents', KnowledgeDocumentViewSet, basename='rag-documents')

urlpatterns = [
    path('', include(router.urls)),
    path('query/', RagQueryView.as_view(), name='rag-query'),
    path('stream/', RagStreamView.as_view(), name='rag-stream'),
    path('sessions/', RagSessionListView.as_view(), name='rag-session-list'),
    path('sources/', RagSourcesView.as_view(), name='rag-sources'),
    path('health/', RagHealthView.as_view(), name='rag-health'),
]
