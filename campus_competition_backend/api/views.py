# ==================== 标准库导入 ====================
import os
import uuid
import platform
from datetime import timedelta

# ==================== Django 核心导入 ====================
from django.conf import settings
from django.db import connection
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.http import JsonResponse
from django.utils import timezone

# ==================== DRF 框架导入 ====================
from rest_framework import viewsets, filters, status, serializers
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny, BasePermission
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser

# ==================== JWT 认证导入 ====================
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken

# ==================== 项目内部导入 ====================
from .models import (
    User, Competition, Category, Registration, Notice, Advertisement,
    Message, LoginLog, OperationLog, ErrorLog, UserCompetitionView, Score,
)
from .serializers import (
    UserSerializer, CompetitionSerializer, CategoryOptionSerializer, RegistrationSerializer,
    NoticeSerializer, AdvertisementSerializer, MessageSerializer, LoginLogSerializer,
    OperationLogSerializer, ErrorLogSerializer, AdminLoginSerializer, CategorySerializer,
    ScoreSerializer,
)


# ==================== 自定义权限类 ====================

class IsJudgeOrAdmin(BasePermission):
    """评委或管理员权限 — 用于需要后台管理但不需要超级管理员权限的操作"""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.role in ['judge', 'admin']


class IsAdminOnly(BasePermission):
    """仅管理员权限 — 用于敏感操作如删除、查看日志等"""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.role == 'admin'


# ==================== 自定义分页 ====================

class CustomPageNumberPagination(PageNumberPagination):
    """通用分页类，同时支持 page_size 和 limit 参数（兼容不同前端调用方式）"""
    page_size = 12
    page_size_query_param = 'page_size'
    limit_query_param = 'limit'
    max_page_size = 100


# 用户管理接口
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['username']

    def get_permissions(self):
        if self.action == 'register':
            return [AllowAny()]
        elif self.action in ['profile', 'update_profile', 'me']:
            return [IsAuthenticated()]
        # 评委可以访问list, retrieve, create, update操作
        elif self.action in ['list', 'retrieve', 'create', 'update', 'partial_update']:
            return [IsJudgeOrAdmin()]
        return [IsAdminOnly()]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        # 评委可以看到普通用户和其他评委
        if user.is_authenticated and user.role == 'judge':
            queryset = queryset.filter(role__in=['user', 'judge'])
        return queryset

    def perform_create(self, serializer):
        user = self.request.user
        if user.role == 'judge':
            # 评委只能创建普通用户
            serializer.save(role='user')
        else:
            serializer.save()

    def perform_update(self, serializer):
        user = self.request.user
        if user.role == 'judge':
            # 评委只能编辑普通用户，且不能修改角色
            data = serializer.validated_data
            data.pop('role', None)
            serializer.save(**data)
        else:
            serializer.save()

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def register(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'message': '注册成功'}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def profile(self, request):
        return Response(UserSerializer(request.user).data)

    @action(detail=False, methods=['put'])
    def update_profile(self, request):
        data = request.data.copy()
        data.pop('role', None)

        # 密码修改逻辑
        password = data.get('password')
        old_password = data.get('old_password')

        if password:
            # 1. 原密码校验
            if not old_password:
                return Response({'detail': '请输入原密码'}, status=400)
            if not request.user.check_password(old_password):
                return Response({'detail': '原密码错误'}, status=400)

            # 🔥 新增：密码长度强制校验（最少6位）
            if len(password) < 6:
                return Response({'detail': '密码长度不能少于6位'}, status=400)
        else:
            data.pop('password', None)

        serializer = UserSerializer(request.user, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    # 新增：获取当前登录用户信息的接口（供前台登录后调用）
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)


# 管理员专属登录视图
class AdminLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = AdminLoginSerializer(data=request.data)
        # 获取登录信息
        username = request.data.get('username', '')
        ip_address = request.META.get('REMOTE_ADDR', '127.0.0.1')
        user_agent = request.META.get('HTTP_USER_AGENT', '未知')

        try:
            serializer.is_valid(raise_exception=True)
            user = serializer.validated_data['user']

            # 生成Token
            refresh = RefreshToken.for_user(user)
            data = {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': UserSerializer(user).data
            }

            # 记录登录成功日志
            LoginLog.objects.create(
                user=user,
                username=username,
                ip_address=ip_address,
                user_agent=user_agent,
                status='success'
            )
            return Response(data)

        except Exception as e:
            # 记录登录失败日志
            LoginLog.objects.create(
                user=None,
                username=username,
                ip_address=ip_address,
                user_agent=user_agent,
                status='failed',
                fail_reason=str(e)
            )
            raise e


class CustomTokenObtainPairView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        username = request.data.get('username', '')
        ip_address = request.META.get('REMOTE_ADDR', '127.0.0.1')
        user_agent = request.META.get('HTTP_USER_AGENT', '未知')

        try:
            response = super().post(request, *args, **kwargs)
            # 登录成功，获取用户
            user = User.objects.get(username=username)

            # 记录登录成功日志
            LoginLog.objects.create(
                user=user,
                username=username,
                ip_address=ip_address,
                user_agent=user_agent,
                status='success'
            )
            return response

        except Exception as e:
            # 记录登录失败日志
            LoginLog.objects.create(
                user=None,
                username=username,
                ip_address=ip_address,
                user_agent=user_agent,
                status='failed',
                fail_reason=str(e)
            )
            raise e


# ==================== 赛事视图集（列表所有人可看，管理仅管理员）====================
class CompetitionViewSet(viewsets.ModelViewSet):
    queryset = Competition.objects.all().order_by('-created_at')
    serializer_class = CompetitionSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['title', 'organizer']
    pagination_class = CustomPageNumberPagination

    # 分接口精准控制权限
    def get_permissions(self):
        # 列表、详情：所有人都能看，不管登没登录
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        # 新增、编辑、封面上传、删除、批量删除：评委或管理员可操作
        return [IsJudgeOrAdmin()]

    # 支持分类、等级、关键词筛选，同时保留权限过滤
    def get_queryset(self):
        queryset = super().get_queryset()
        # 1. 权限过滤：非管理员和评委，只返回已发布的赛事
        user = self.request.user
        if not user.is_authenticated or user.role not in ['admin', 'judge']:
            queryset = queryset.filter(status='published')

        # 2. 分类筛选：前端传category参数（分类ID）
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category_id=category)

        # 3. 等级筛选：前端传level参数（校级/市级等对应的code）
        level = self.request.query_params.get('level')
        if level:
            queryset = queryset.filter(level=level)

        # 4. 排序：最新/最热
        sort = self.request.query_params.get('sort')
        if sort == 'hot':
            queryset = queryset.order_by('-view_count')
        else:
            queryset = queryset.order_by('-created_at')

        return queryset

    # 封面上传接口：仅处理文件上传，不创建赛事记录
    @action(detail=False, methods=['post'], url_path='upload-cover')
    def upload_cover(self, request):
        # 1. 基础校验：文件是否存在
        cover_file = request.FILES.get('file')
        if not cover_file:
            return Response(
                {'code': 400, 'msg': '请选择要上传的图片文件', 'data': None},
                status=status.HTTP_400_BAD_REQUEST
            )
        # 2. 安全校验：仅允许图片类型
        allow_image_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
        if cover_file.content_type not in allow_image_types:
            return Response(
                {'code': 400, 'msg': '仅支持 jpg/png/gif/webp 格式的图片', 'data': None},
                status=status.HTTP_400_BAD_REQUEST
            )
        # 3. 大小校验：最大2MB
        max_file_size = 2 * 1024 * 1024
        if cover_file.size > max_file_size:
            return Response(
                {'code': 400, 'msg': '图片大小不能超过 2MB', 'data': None},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            # 4. 生成唯一文件名（避免重名覆盖）
            file_ext = os.path.splitext(cover_file.name)[1]
            unique_file_name = f"{uuid.uuid4().hex}{file_ext}"
            # 5. 自动创建保存目录（不存在则新建）
            save_dir = os.path.join(settings.MEDIA_ROOT, 'competition_covers')
            os.makedirs(save_dir, exist_ok=True)
            save_path = os.path.join(save_dir, unique_file_name)
            # 6. 写入文件到服务器
            with open(save_path, 'wb+') as f:
                for chunk in cover_file.chunks():
                    f.write(chunk)
            # 7. 构造图片访问URL并返回
            file_url = f"{settings.MEDIA_URL}competition_covers/{unique_file_name}"
            return Response(
                {'code': 200, 'msg': '封面上传成功', 'data': {'url': file_url}},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            # 8. 异常捕获：避免服务器错误直接暴露给前端
            return Response(
                {'code': 500, 'msg': f'上传失败，请稍后重试：{str(e)}', 'data': None},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    # 批量删除接口
    @action(detail=False, methods=['post'], url_path='batch-delete')
    def batch_delete(self, request):
        ids = request.data.get('ids', [])
        if not ids:
            return Response(
                {'code': 400, 'msg': '请选择要删除的赛事'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            deleted_count, _ = Competition.objects.filter(id__in=ids).delete()
            return Response(
                {'code': 200, 'msg': f'成功删除 {deleted_count} 个赛事'},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {'code': 500, 'msg': f'删除失败：{str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ==================== 分类下拉选项接口（所有人可访问）====================
class CategoryOptionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategoryOptionSerializer
    # 【核心修复】放开权限，所有人都能获取分类下拉选项
    permission_classes = [AllowAny]


# ====================分类管理接口 ====================
class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all().order_by('id')
    serializer_class = CategorySerializer

    # 分接口控制权限
    def get_permissions(self):
        # 列表接口：所有人可访问
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        # 新增、编辑、删除：评委或管理员
        return [IsJudgeOrAdmin()]

    # 分类选项接口（类内生效）
    @action(detail=False, methods=['get'], url_path='options', permission_classes=[AllowAny])
    def get_category_options(self, request):
        categories = Category.objects.all()
        serializer = CategoryOptionSerializer(categories, many=True)
        return Response(serializer.data)


# ==================== 报名管理接口 ====================
class RegistrationViewSet(viewsets.ModelViewSet):
    queryset = Registration.objects.all().order_by('-created_at')
    serializer_class = RegistrationSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'competition__title']  # 支持按姓名和赛事名称搜索

    # 分接口配置权限
    def get_permissions(self):
        # 我的报名、报名详情：需要登录
        if self.action in ['my_registrations', 'retrieve']:
            return [IsAuthenticated()]
        # 新增报名：需要登录
        if self.action == 'create':
            return [IsAuthenticated()]
        # 管理操作：评委或管理员
        return [IsJudgeOrAdmin()]

    # 报名列表过滤：管理员和评委看全部，普通用户只看自己的，支持按赛事筛选
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if not user.is_authenticated or user.role not in ['admin', 'judge']:
            queryset = queryset.filter(user=user)
        # 按赛事筛选
        competition_id = self.request.query_params.get('competition')
        if competition_id:
            queryset = queryset.filter(competition_id=competition_id)
        return queryset

    # 新增报名：自动绑定当前用户，校验重复报名
    def perform_create(self, serializer):
        user = self.request.user
        competition_id = self.request.data.get('competition')
        # 校验是否已经报名
        if Registration.objects.filter(user=user, competition_id=competition_id).exists():
            raise serializers.ValidationError({'detail': '您已经报名过该赛事，请勿重复报名'})
        # 保存数据
        serializer.save(user=user, status='normal')

    # 【前台用】获取当前用户的报名列表
    @action(detail=False, methods=['get'], url_path='my', permission_classes=[IsAuthenticated])
    def my_registrations(self, request):
        try:
            registrations = Registration.objects.filter(user=request.user).order_by('-created_at')
            serializer = self.get_serializer(registrations, many=True)
            return Response(serializer.data)
        except Exception as e:
            print('我的报名接口报错：', str(e))
            return Response([], status=200)

    # 【后台用】取消报名
    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel_registration(self, request, pk=None):
        registration = self.get_object()
        if registration.status == 'canceled':
            raise serializers.ValidationError({'detail': '该报名已取消，无需重复操作'})
        registration.status = 'canceled'
        registration.save()
        return Response({'code': 200, 'msg': '取消成功'})

    # 【后台用】录入成绩
    @action(detail=True, methods=['post'], url_path='set-score')
    def set_score(self, request, pk=None):
        registration = self.get_object()
        score = request.data.get('score')
        if not score:
            raise serializers.ValidationError({'detail': '请输入成绩'})
        registration.score = score
        registration.status = 'finished'
        registration.save()
        return Response({'code': 200, 'msg': '成绩录入成功'})


class FileUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        try:
            file = request.FILES.get('file')
            if not file:
                return JsonResponse({'code': 400, 'message': '请选择要上传的文件'}, status=400)

            # 校验文件格式
            ext = os.path.splitext(file.name)[1].lower()
            allowed_exts = ['.jpg', '.jpeg', '.png', '.mp4', '.avi', '.mov']
            if ext not in allowed_exts:
                return JsonResponse({
                    'code': 400,
                    'message': f'不支持的文件格式，仅支持：{",".join(allowed_exts)}'
                }, status=400)

            # 生成唯一文件名（避免重名）
            unique_filename = f"{uuid.uuid4().hex}{ext}"
            # 定义保存路径
            save_path = os.path.join(settings.MEDIA_ROOT, 'registrations', unique_filename)
            # 确保目录存在
            os.makedirs(os.path.dirname(save_path), exist_ok=True)

            # 直接保存文件（不创建报名记录）
            with open(save_path, 'wb+') as destination:
                for chunk in file.chunks():
                    destination.write(chunk)

            # 构造文件访问URL
            file_url = request.build_absolute_uri(f"{settings.MEDIA_URL}registrations/{unique_filename}")

            return JsonResponse({
                'code': 200,
                'message': '上传成功',
                'file_url': file_url
            })
        except Exception as e:
            print(f"上传错误详情：{str(e)}")
            return JsonResponse({
                'code': 500,
                'message': f'上传失败：{str(e)}'
            }, status=500)


# 公告管理接口
# 公告管理接口（彻底修复权限问题）
class NoticeViewSet(viewsets.ModelViewSet):
    queryset = Notice.objects.all().order_by('-create_time')
    serializer_class = NoticeSerializer

    # 【核心修复】分接口精准控制权限，覆盖所有场景
    def get_permissions(self):
        # 前台接口：列表、详情、最新公告，所有人可访问
        if self.action in ['list', 'retrieve', 'latest_notices']:
            return [AllowAny()]
        # 后台管理接口：新增、编辑，评委或管理员
        elif self.action in ['create', 'update', 'partial_update']:
            return [IsJudgeOrAdmin()]
        # 删除：仅管理员
        return [IsAdminOnly()]

    # 前台获取最新公告列表（用于通知中心）
    @action(detail=False, methods=['get'], url_path='latest')
    def latest_notices(self, request):
        # 只返回已发布的公告
        notices = Notice.objects.filter(is_published=True).order_by('-create_time')[:10]
        serializer = self.get_serializer(notices, many=True)
        return Response(serializer.data)


# 广告管理接口
class AdvertisementViewSet(viewsets.ModelViewSet):
    queryset = Advertisement.objects.all()
    serializer_class = AdvertisementSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        elif self.action in ['create', 'update', 'partial_update']:
            return [IsJudgeOrAdmin()]
        return [IsAdminOnly()]


# 留言管理接口
class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.all().order_by('-create_time')
    serializer_class = MessageSerializer

    def get_permissions(self):
        if self.action == 'create':
            # return [IsAuthenticated()]
            return [AllowAny()]
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        # 评委可以查看和回复留言
        elif self.action in ['update', 'partial_update']:
            return [IsJudgeOrAdmin()]
        return [IsAdminOnly()]


# 登录日志接口
class LoginLogViewSet(viewsets.ModelViewSet):
    """登录日志视图集（仅管理员可查看）"""
    queryset = LoginLog.objects.all().order_by('-login_time')
    serializer_class = LoginLogSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [filters.SearchFilter]
    search_fields = ['username', 'ip_address']  # 支持按用户名和IP搜索
    pagination_class = CustomPageNumberPagination

    @action(detail=False, methods=['post'], url_path='batch-delete')
    def batch_delete(self, request):
        ids = request.data.get('ids', [])
        if not ids:
            return Response({'code': 400, 'msg': '请选择要删除的日志'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            deleted_count, _ = LoginLog.objects.filter(id__in=ids).delete()
            return Response({'code': 200, 'msg': f'成功删除 {deleted_count} 条日志'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'code': 500, 'msg': f'删除失败：{str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# 操作日志接口
class OperationLogViewSet(viewsets.ModelViewSet):
    """操作日志视图集（仅管理员可查看）"""
    # 修复：把 create_time 改成 created_at
    queryset = OperationLog.objects.all().order_by('-created_at')
    serializer_class = OperationLogSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [filters.SearchFilter]
    search_fields = ['request_url', 'ip_address', 'user__username']
    pagination_class = CustomPageNumberPagination

    @action(detail=False, methods=['post'], url_path='batch-delete')
    def batch_delete(self, request):
        ids = request.data.get('ids', [])
        if not ids:
            return Response({'code': 400, 'msg': '请选择要删除的日志'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            deleted_count, _ = OperationLog.objects.filter(id__in=ids).delete()
            return Response({'code': 200, 'msg': f'成功删除 {deleted_count} 条日志'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'code': 500, 'msg': f'删除失败：{str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# 错误日志接口
class ErrorLogViewSet(viewsets.ModelViewSet):
    """错误日志视图集（仅管理员可查看）"""
    queryset = ErrorLog.objects.all().order_by('-created_at')
    serializer_class = ErrorLogSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [filters.SearchFilter]
    search_fields = ['request_url', 'error_message', 'ip_address']
    pagination_class = CustomPageNumberPagination

    @action(detail=False, methods=['post'], url_path='batch-delete')
    def batch_delete(self, request):
        ids = request.data.get('ids', [])
        if not ids:
            return Response({'code': 400, 'msg': '请选择要删除的日志'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            deleted_count, _ = ErrorLog.objects.filter(id__in=ids).delete()
            return Response({'code': 200, 'msg': f'成功删除 {deleted_count} 条日志'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'code': 500, 'msg': f'删除失败：{str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# 统计分析接口
class StatisticsViewSet(viewsets.ViewSet):
    permission_classes = [IsJudgeOrAdmin]

    @action(detail=False, methods=['get'], url_path='visit-trend')
    def visit_trend(self, request):
        """近7天访问趋势：从 OperationLog 聚合统计每日请求量"""
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=6)

        # 使用聚合查询一次性获取所有操作日志数据
        operations = OperationLog.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        ).annotate(
            view_date=TruncDate('created_at')
        ).values('view_date').annotate(
            count=Count('id')
        ).order_by('view_date')

        # 将结果转为字典便于查找
        view_dict = {str(op['view_date']): op['count'] for op in operations}

        # 构建完整的7天数据，没有数据的天数补0
        data = []
        for i in range(6, -1, -1):
            target_date = end_date - timedelta(days=i)
            date_str = str(target_date)
            count = view_dict.get(date_str, 0)
            data.append({
                'date': target_date.strftime('%m-%d'),
                'count': count
            })

        return Response(data)

    @action(detail=False, methods=['get'], url_path='hot-competition')
    def hot_competition(self, request):
        # 热门赛事排行 - 按浏览次数排序
        competitions = Competition.objects.all().order_by('-view_count')[:10]
        data = [{'title': item.title, 'view_count': item.view_count} for item in competitions]
        return Response(data)

    @action(detail=False, methods=['get'], url_path='category-ratio')
    def category_ratio(self, request):
        """分类赛事数量占比 — 按每个分类下的赛事个数统计"""
        categories = Category.objects.annotate(competition_count=Count('competition'))
        data = [{'name': item.name, 'value': item.competition_count} for item in categories]
        return Response(data)


# 系统信息接口
class SystemInfoViewSet(viewsets.ViewSet):
    permission_classes = [IsAdminUser]

    @action(detail=False, methods=['get'])
    def info(self, request):
        """系统信息接口 — 返回服务器操作系统、CPU、内存、MySQL版本等运行状态"""
        import psutil

        system_info = {
            'system_name': '校园赛事管理系统',
            'version': '1.0.0',
            'os': platform.system(),
            'platform': platform.platform(),
            'cpu_core': psutil.cpu_count(),
            'cpu_processor': platform.processor(),
            'cpu_load': f'{psutil.cpu_percent()}%',
            'total_memory': f'{round(psutil.virtual_memory().total / 1024 / 1024 / 1024, 2)} GB',
            'used_memory': f'{round(psutil.virtual_memory().used / 1024 / 1024 / 1024, 2)} GB',
            'memory_usage': psutil.virtual_memory().percent,
            'system_language': os.getenv('LANG', 'zh_CN.UTF-8'),
            'timezone': os.getenv('TZ', 'Asia/Shanghai'),
            'mysql_version': '',
            'nginx_version': '未知'
        }
        # 获取MySQL版本
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT VERSION()")
                system_info['mysql_version'] = cursor.fetchone()[0]
        except:
            system_info['mysql_version'] = '未知'
        return Response(system_info)


@api_view(['POST'])
@permission_classes([AllowAny])  # 不需要登录
def add_competition_view(request, pk):
    try:
        competition = Competition.objects.get(pk=pk)

        # 增加浏览计数
        competition.view_count += 1
        competition.save()

        # 记录到 UserCompetitionView 用于统计分析
        user = request.user if request.user.is_authenticated else None
        UserCompetitionView.objects.create(
            user=user,
            competition=competition
        )

        return Response({'code': 200, 'message': '成功'})
    except Competition.DoesNotExist:
        return Response({'code': 404}, status=404)


# ==================== 评分管理视图集 ====================
class ScoreViewSet(viewsets.ModelViewSet):
    queryset = Score.objects.all().order_by('-created_at')
    serializer_class = ScoreSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['registration__name', 'registration__competition__title', 'judge__username']
    pagination_class = CustomPageNumberPagination

    def get_permissions(self):
        return [IsJudgeOrAdmin()]

    def get_queryset(self):
        queryset = super().get_queryset()
        # 按赛事筛选
        competition_id = self.request.query_params.get('competition')
        if competition_id:
            queryset = queryset.filter(registration__competition_id=competition_id)
        return queryset

    def perform_create(self, serializer):
        # 检查是否是评委自己的评分
        user = self.request.user
        judge = serializer.validated_data.get('judge')
        # 确保类型一致再比较
        if user.role == 'judge' and judge.id != user.id:
            raise serializers.ValidationError({'detail': '您只能为自己评分'})
        # 保存评分时自动更新报名记录的最终评分和状态
        score = serializer.save()
        registration = score.registration
        final_score = registration.calculate_final_score()
        if final_score is not None:
            registration.score = str(round(final_score, 2))
            registration.status = 'finished'
            registration.save()

    def perform_update(self, serializer):
        # 检查是否是评委自己的评分且未锁定
        user = self.request.user
        score = self.get_object()
        if user.role == 'judge':
            if score.judge != user:
                raise serializers.ValidationError({'detail': '您只能修改自己的评分'})
            if score.is_locked:
                raise serializers.ValidationError({'detail': '该评分已锁定，无法修改'})
        # 更新评分时自动更新报名记录的最终评分
        score = serializer.save()
        registration = score.registration
        final_score = registration.calculate_final_score()
        if final_score is not None:
            registration.score = str(round(final_score, 2))
            registration.status = 'finished'
            registration.save()

    @action(detail=True, methods=['post'], url_path='lock')
    def lock_score(self, request, pk=None):
        """锁定评分"""
        score = self.get_object()
        user = request.user
        # 检查权限：只有管理员或评分的评委可以锁定
        if user.role != 'admin' and score.judge != user:
            return Response({'code': 403, 'msg': '您没有权限锁定该评分'}, status=403)
        score.is_locked = True
        score.save()
        return Response({'code': 200, 'msg': '评分锁定成功'})

    @action(detail=False, methods=['get'], url_path='list-for-management')
    def list_for_management(self, request):
        """获取评分管理列表数据"""
        # 获取所有有评委的赛事的报名记录
        registrations = Registration.objects.filter(
            competition__judges__isnull=False
        ).distinct().order_by('-created_at')

        # 按赛事筛选
        competition_id = request.query_params.get('competition')
        if competition_id:
            registrations = registrations.filter(competition_id=competition_id)

        # 分页
        paginator = CustomPageNumberPagination()
        page = paginator.paginate_queryset(registrations, request)

        data = []
        for reg in page:
            # 获取该报名的所有评委评分
            scores = reg.scores.all()
            # 获取该赛事的所有评委
            judges = reg.competition.judges.all()

            # 构建评委评分信息
            judge_scores = {}
            for score in scores:
                judge_scores[score.judge.id] = {
                    'id': score.id,
                    'nickname': score.judge.nickname or score.judge.username,
                    'score': float(score.score),
                    'is_locked': score.is_locked
                }

            # 对于没有评分的评委，显示空
            for judge in judges:
                if judge.id not in judge_scores:
                    judge_scores[judge.id] = {
                        'nickname': judge.nickname or judge.username,
                        'score': None
                    }

            data.append({
                'id': reg.id,
                'competition_title': reg.competition.title,
                'competition_id': reg.competition.id,
                'user_name': reg.name,
                'judge_scores': judge_scores,
                'final_score': reg.calculate_final_score(),
                'status': reg.status
            })

        return paginator.get_paginated_response(data)
