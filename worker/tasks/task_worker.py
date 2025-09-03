import json
from celery import shared_task  # 使用 shared_task 装饰器
from config.models import Task, TaskResult
from django.db import transaction
import time
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@shared_task(name='process_task')  # 添加名称
def process_task(task_id, task_type, input_data):
    """处理任务的Celery工作函数"""
    logger.info(f'开始处理任务: {task_id}, 类型: {task_type}')
    
    try:
        # 更新任务状态为处理中
        with transaction.atomic():
            task = Task.objects.get(id=task_id)
            task.status = 'PROCESSING'
            task.save()

        # 模拟不同类型任务的处理逻辑
        if task_type == 'data_processing':
            result = process_data(input_data)
        elif task_type == 'calculation':
            result = perform_calculation(input_data)
        else:
            result = default_processing(input_data)

        # 更新任务状态和结果
        with transaction.atomic():
            task = Task.objects.get(id=task_id)
            task.status = 'COMPLETED'
            task.save()

            # 创建任务结果
            TaskResult.objects.create(
                task=task,
                result_data=result
            )

        logger.info(f'任务 {task_id} 处理完成')
        return result

    except Exception as e:
        logger.error(f'任务 {task_id} 处理失败: {str(e)}')

        # 更新任务状态为失败
        with transaction.atomic():
            try:
                task = Task.objects.get(id=task_id)
                task.status = 'FAILED'
                task.save()

                # 创建任务结果（包含错误信息）
                TaskResult.objects.create(
                    task=task,
                    error_message=str(e)
                )
            except Task.DoesNotExist:
                logger.error(f'任务 {task_id} 不存在')

        return {'error': str(e)}

# 任务处理函数示例

def process_data(input_data):
    """数据处理任务示例"""
    logger.info(f'执行数据处理: {input_data}')
    # 模拟处理时间
    time.sleep(2)
    # 简单处理示例
    result = {'processed': True, 'data': input_data, 'timestamp': time.time()}
    return result

def perform_calculation(input_data):
    """计算任务示例"""
    logger.info(f'执行计算任务: {input_data}')
    # 模拟处理时间
    time.sleep(1)
    # 简单计算示例
    if isinstance(input_data, dict) and 'numbers' in input_data:
        numbers = input_data['numbers']
        result = {
            'sum': sum(numbers),
            'average': sum(numbers) / len(numbers) if numbers else 0,
            'count': len(numbers)
        }
    else:
        result = {'error': 'Invalid input format for calculation'}
    return result

def default_processing(input_data):
    """默认处理函数"""
    logger.info(f'执行默认处理: {input_data}')
    # 模拟处理时间
    time.sleep(0.5)
    return {'processed': True, 'original_data': input_data}