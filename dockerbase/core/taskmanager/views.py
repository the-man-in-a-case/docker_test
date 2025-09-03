from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Task
import json
from celery import current_app
import os

@csrf_exempt
def create_task(request):
    """创建新任务API"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            task_name = data.get('task_name', 'Unnamed Task')
            task_type = data.get('task_type', 'default')
            input_data = data.get('input_data', {})

            # 创建任务记录
            task = Task.objects.create(
                task_name=task_name,
                task_type=task_type,
                input_data=input_data
            )

            # 使用 Celery 的延迟调用
            celery_app = current_app
            celery_task = celery_app.send_task(
                # 'worker.tasks.task_worker.process_task',
                'process_task',
                args=[str(task.id), task_type, input_data]
            )

            # 更新任务记录的Celery任务ID
            task.celery_task_id = celery_task.id
            task.status = 'PROCESSING'
            task.save()

            return JsonResponse({
                'success': True,
                'task_id': str(task.id),
                'celery_task_id': celery_task.id
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)
    return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)


def get_task_status(request, task_id):
    """获取任务状态API"""
    try:
        task = Task.objects.get(id=task_id)
        result = None
        if hasattr(task, 'result'):
            result = {
                'result_data': task.result.result_data,
                'error_message': task.result.error_message,
                'completed_at': task.result.completed_at.isoformat() if task.result.completed_at else None
            }

        return JsonResponse({
            'success': True,
            'task': {
                'id': str(task.id),
                'task_name': task.task_name,
                'task_type': task.task_type,
                'status': task.status,
                'status_display': task.get_status_display(),
                'created_at': task.created_at.isoformat(),
                'updated_at': task.updated_at.isoformat(),
                'celery_task_id': task.celery_task_id,
                'result': result
            }
        })
    except Task.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Task not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)