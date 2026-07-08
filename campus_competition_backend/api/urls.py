from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import (
    UserViewSet, CompetitionViewSet, CategoryViewSet, CategoryOptionViewSet, RegistrationViewSet,
    NoticeViewSet, AdvertisementViewSet, MessageViewSet, LoginLogViewSet,
    OperationLogViewSet, ErrorLogViewSet, StatisticsViewSet, SystemInfoViewSet,
    AdminLoginView, CustomTokenObtainPairView, FileUploadView, add_competition_view,
    ScoreViewSet,
)

router = DefaultRouter()
# 核心业务路由
router.register('users', UserViewSet, basename='users')
router.register('category-options', CategoryOptionViewSet, basename='category-options')  # 【新增】分类下拉接口
router.register('categories', CategoryViewSet, basename='categories')  # 分类管理接口
router.register('competitions', CompetitionViewSet, basename='competitions')  # 赛事管理（含封面上传接口）
router.register('registrations', RegistrationViewSet, basename='registrations')
router.register('notices', NoticeViewSet, basename='notices')
router.register('adverts', AdvertisementViewSet, basename='adverts')
router.register('messages', MessageViewSet, basename='messages')
# 日志路由
router.register('login-logs', LoginLogViewSet, basename='login-logs')
router.register('operation-logs', OperationLogViewSet, basename='operation-logs')
router.register('error-logs', ErrorLogViewSet, basename='error-logs')
# 统计与系统路由
router.register('statistics', StatisticsViewSet, basename='statistics')
router.register('system', SystemInfoViewSet, basename='system')
router.register('scores', ScoreViewSet, basename='scores')
urlpatterns = [
    path('', include(router.urls)),
    # JWT 认证接口
    path('auth/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    # 后台管理员登录接口
    path('auth/admin-login/', AdminLoginView.as_view(), name='admin_login'),
    # 注册接口（保留一个即可，这里保留 /api/auth/register/，更符合语义）
    path('auth/register/', UserViewSet.as_view({'post': 'register'}), name='user_register'),
    path('upload/', FileUploadView.as_view(), name='file-upload'),  # 必须有
    path('competitions/<int:pk>/add-view/', add_competition_view, name='competition-add-view'),
]
