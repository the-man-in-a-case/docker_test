import logging

class HealthCheckLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.logger = logging.getLogger('gunicorn.access')

    def __call__(self, request):
        # 检查是否是健康检查请求
        if request.path == '/health' and request.method == 'GET':
            # 临时关闭访问日志
            original_level = self.logger.level
            self.logger.setLevel(logging.CRITICAL)

        response = self.get_response(request)

        # 恢复日志级别
        if request.path == '/health' and request.method == 'GET':
            self.logger.setLevel(original_level)

        return response