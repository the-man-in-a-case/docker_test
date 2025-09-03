# data_migration.py
from django.db import transaction
from db.models import Map, Layer
from manager.models import MapVersionSnapshot, LayerVersion
from .db_router import setup_target_db

def migrate_resource(resource_type: str, resource_id: int, version: int, target_db_config: dict):
    """
    迁移 Map 或 Layer 的指定版本到目标数据库
    """
    alias = "target_db"
    setup_target_db(alias, target_db_config)

    if resource_type == "map":
        snapshot = MapVersionSnapshot.objects.get(map_id=resource_id, version=version)
        data = snapshot.snapshot_data
        model_cls = Map
    elif resource_type == "layer":
        snapshot = LayerVersion.objects.get(layer_id=resource_id, version=version)
        data = snapshot.data
        model_cls = Layer
    else:
        raise ValueError("resource_type 必须是 map 或 layer")

    # 使用事务保证目标数据库写入完整性
    with transaction.atomic(using=alias):
        obj = model_cls.objects.using(alias).create(**data)
        return obj.id
