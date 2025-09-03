from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.db import transaction
from .models import Map, Layer
import json

@csrf_exempt
def receive_alert(request):
    if request.method == 'POST':
        try:
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                data = request.POST.dict()

            alert_text = data.get('text', '')
            print(f"接收到告警信息: {alert_text}")
            return JsonResponse({'status': 'success', 'message': '告警信息已接收'})
        except Exception as e:
            print(f"处理告警信息时出错: {str(e)}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'error', 'message': '只支持POST请求'}, status=405)

@csrf_exempt
def receive_migration(request):
    """
    接收来自datamanage项目的数据迁移请求
    请求格式: POST http://localhost:8001/api/receive-migration/
    请求体: {
        "resource_type": "map" 或 "layer",
        "data": {迁移的数据}
    }
    """
    if request.method == 'POST':
        try:
            if request.content_type == 'application/json':
                request_data = json.loads(request.body)
            else:
                return JsonResponse({'status': 'error', 'message': 'Content-Type必须为application/json'}, status=400)

            resource_type = request_data.get('resource_type')
            data = request_data.get('data')

            if not resource_type or not data:
                return JsonResponse({'status': 'error', 'message': '缺少必要参数resource_type或data'}, status=400)

            # 使用事务保证数据完整性
            with transaction.atomic():
                if resource_type == 'map':
                    # 处理地图数据迁移
                    map_obj = Map.objects.create(
                        version_number=data.get('version_number', 1),
                        author=data.get('author', ''),
                        message=data.get('message', ''),
                    )
                    return JsonResponse({'status': 'success', 'new_id': map_obj.id}, status=201)
                elif resource_type == 'layer':
                    # 处理图层数据迁移
                    layer_obj = Layer.objects.create(
                        type=data.get('type'),
                        version_number=data.get('version_number', 1),
                        author=data.get('author', ''),
                        message=data.get('message', ''),
                    )
                    return JsonResponse({'status': 'success', 'new_id': layer_obj.id}, status=201)
                else:
                    return JsonResponse({'status': 'error', 'message': 'resource_type必须是map或layer'}, status=400)
        except Exception as e:
            print(f"处理数据迁移时出错: {str(e)}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'error', 'message': '只支持POST请求'}, status=405)
