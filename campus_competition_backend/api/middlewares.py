import time
import logging
import traceback
from django.http import JsonResponse
from .models import OperationLog, ErrorLog

logger = logging.getLogger(__name__)


class OperationLogMiddleware:
    """
    操作日志中间件 — 自动记录所有 API 请求到 OperationLog 表。

    注意：以下路径会被排除，不记录日志：
    - /media/  静态媒体文件
    - /static/ 静态资源
    - /favicon.ico 浏览器图标请求
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.start_time = time.time()
        response = self.get_response(request)

        # 排除静态文件和媒体文件的请求，减少无意义的日志记录
        exclude_paths = ['/media/', '/static/', '/favicon.ico']
        for path in exclude_paths:
            if request.path.startswith(path):
                return response

        # 计算请求耗时（毫秒）
        duration = int((time.time() - request.start_time) * 1000)
        request_method = request.method
        request_url = request.path
        ip_address = request.META.get('REMOTE_ADDR', '127.0.0.1')
        user_agent = request.META.get('HTTP_USER_AGENT', '未知')
        user = request.user if request.user.is_authenticated else None

        # 异步写入操作日志（不阻塞请求响应）
        OperationLog.objects.create(
            user=user,
            request_method=request_method,
            request_url=request_url,
            ip_address=ip_address,
            user_agent=user_agent,
            duration=duration
        )

        return response


class GlobalExceptionMiddleware:
    """
    全局异常处理中间件 — 捕获所有未处理的异常，记录到 ErrorLog 表并返回 JSON 错误响应。

    注意：
    1. 此中间件必须放在 MIDDLEWARE 列表的最前面，才能捕获后续所有中间件和视图的异常。
    2. 异常会被拦截并返回统一格式的 JSON 响应，不会传播到 Django 默认的错误页面。
    3. 异常信息同时写入数据库 ErrorLog 表和控制台日志（便于开发调试）。
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            return self.get_response(request)
        except Exception as exception:
            return self.process_exception(request, exception)

    def process_exception(self, request, exception):
        request_method = request.method
        request_url = request.path
        ip_address = request.META.get('REMOTE_ADDR', '127.0.0.1')
        user_agent = request.META.get('HTTP_USER_AGENT', '未知')
        user = request.user if request.user.is_authenticated else None
        error_message = str(exception)
        error_traceback = traceback.format_exc()

        # 输出到控制台，便于开发调试（生产环境可配合日志收集系统）
        logger.error(
            f"[全局异常] {request_method} {request_url} | "
            f"IP: {ip_address} | 用户: {user} | "
            f"错误: {error_message}\n{error_traceback}"
        )

        # 持久化到数据库 ErrorLog 表
        ErrorLog.objects.create(
            user=user,
            request_method=request_method,
            request_url=request_url,
            ip_address=ip_address,
            user_agent=user_agent,
            error_message=error_message,
            error_traceback=error_traceback
        )

        # 返回统一格式的错误响应，不暴露敏感的错误堆栈给前端
        return JsonResponse({
            'code': 500,
            'message': f'服务器内部错误：{error_message}'
        }, status=500)