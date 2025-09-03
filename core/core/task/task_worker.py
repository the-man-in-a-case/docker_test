from celery import shared_task
import time
import json
import logging
from django.db import connection
from core.models import Task, TaskResult

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@shared_task(bind=True)
def process_task(self, task_id, task_type, input_data):
    """处理任务的Celery工作函数"""
    logger.info(f'Start processing task: {task_id}, type: {task_type}')

    try:
        # 确保数据库连接正常
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")

        # 获取任务对象
        task = Task.objects.get(id=task_id)
        task.status = 'PROCESSING'
        task.save()

        # 根据任务类型执行不同的处理逻辑
        result_data = None
        if task_type == 'data_processing':
            # 模拟数据处理任务
            result_data = process_data(input_data)
        elif task_type == 'calculation':
            # 模拟计算任务
            result_data = perform_calculation(input_data)
        else:
            # 默认处理逻辑
            result_data = {'result': f'Default processing for {task_type}', 'input': input_data}

        # 创建任务结果
        TaskResult.objects.create(
            task=task,
            result_data=result_data
        )

        # 更新任务状态
        task.status = 'COMPLETED'
        task.save()

        logger.info(f'Task {task_id} completed successfully')
        return {'success': True, 'result_data': result_data}

    except Exception as e:
        # 处理异常
        logger.error(f'Error processing task {task_id}: {str(e)}')
        try:
            task = Task.objects.get(id=task_id)
            task.status = 'FAILED'
            task.save()

            # 创建错误结果
            TaskResult.objects.create(
                task=task,
                error_message=str(e)
            )
        except Task.DoesNotExist:
            logger.error(f'Task {task_id} not found when updating error status')

        return {'success': False, 'error': str(e)}

def process_data(input_data):
    """模拟数据处理逻辑"""
    # 模拟处理时间
    time.sleep(2)
    # 简单的数据处理示例
    processed_data = {k: v * 2 for k, v in input_data.items() if isinstance(v, (int, float))}
    return {'processed_data': processed_data, 'original_data': input_data}

def perform_calculation(input_data):
    """模拟计算逻辑"""
    # 模拟处理时间
    time.sleep(3)
    # 简单的计算示例
    result = sum(input_data.values()) if isinstance(input_data, dict) else 0
    return {'result': result, 'input_data': input_data}