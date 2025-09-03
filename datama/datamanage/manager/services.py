# services.py
import copy
import json
from datetime import datetime
from django.db import transaction
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.utils import timezone

from deepdiff import DeepDiff  # pip install deepdiff

from db.models import (
    Map, Layer, MapLayer,
    BaseNode, BaseEdge, Node, MechanismRelationship, Edge, IntraEdge,
    Configuration, Technique, TargetNode, Diagram,
    Condition, Record, Execution, AnalysisAlgorithm,
    FormatConversion, Result, Simulation, Project,
)
from .models import ResourceImportJob, AuditLog, MapArchive, MapVersionSnapshot, LayerVersion

def _serialize_instance(obj):
    data = {}
    for field in obj._meta.fields:
        name = field.name
        value = getattr(obj, name)
        if field.is_relation and value is not None:
            data[name] = getattr(value, 'id', value)
        else:
            if hasattr(value, 'isoformat'):
                data[name] = value.isoformat()
            else:
                data[name] = value
    return data

def compute_diff_deep(old: dict, new: dict) -> dict:
    """
    使用 deepdiff 提供更精细的差异结果（可 JSON 序列化）。
    """
    dd = DeepDiff(old, new, ignore_order=True, verbose_level=2)
    # deepdiff 返回的是特殊对象，转成原生 dict/JSON
    return json.loads(dd.to_json())

def export_map(map_id, version_number=None):
    """
    导出 Map（当前实现导出当前 Map + 其包含的最新 Layer）。
    若传 version_number，将尝试从 MapArchive 获取历史快照（真正固定版本）。
    """
    if version_number is not None:
        archive = MapArchive.objects.filter(map_id=map_id, version_number=version_number).first()
        if not archive:
            raise ObjectDoesNotExist(f"No archived snapshot for map {map_id} version {version_number}")
        return {
            'map': archive.snapshot.get('map'),
            'layers': archive.snapshot.get('layers', []),
            'exported_at': timezone.now().isoformat(),
            'archived_version': version_number
        }

    try:
        m = Map.objects.get(id=map_id)
    except Map.DoesNotExist:
        raise ObjectDoesNotExist(f"Map {map_id} not found")

    map_obj = _serialize_instance(m)
    layers = []
    for ml in m.map_layers.select_related('layer').all():
        layer = ml.layer
        layers.append(_serialize_instance(layer))

    return {
        'map': map_obj,
        'layers': layers,
        'exported_at': timezone.now().isoformat()
    }

def export_layer(layer_id, include_related=True):
    try:
        layer = Layer.objects.get(id=layer_id)
    except Layer.DoesNotExist:
        raise ObjectDoesNotExist(f"Layer {layer_id} not found")

    layer_data = _serialize_instance(layer)
    if not include_related:
        return {'layer': layer_data, 'exported_at': timezone.now().isoformat()}

    nodes = [_serialize_instance(n.base_node) for n in layer.nodes.select_related('base_node').all()]
    intra_edges = []
    for ie in layer.intra_edges.select_related('edge__base_edge').all():
        edge = ie.edge
        base_edge = edge.base_edge
        d = {
            'intraedge': _serialize_instance(ie),
            'edge': {'edge_fields': _serialize_instance(edge), 'base_edge': _serialize_instance(base_edge)}
        }
        intra_edges.append(d)

    configurations = [_serialize_instance(cfg) for cfg in layer.configurations.all()]
    diagrams = [_serialize_instance(dg) for dg in layer.diagrams.all()]

    return {
        'layer': layer_data,
        'nodes': nodes,
        'intra_edges': intra_edges,
        'configurations': configurations,
        'diagrams': diagrams,
        'exported_at': timezone.now().isoformat()
    }

@transaction.atomic
def _archive_map_snapshot(map_obj, author='', message=''):
    """
    将当前 Map + 最新 Layers 导出并存为 MapArchive 固定版本。
    """
    snapshot = export_map(map_obj.id)  # 当前版本
    MapArchive.objects.create(
        map=map_obj,
        version_number=map_obj.version_number,
        snapshot=snapshot,
        author=author or (map_obj.author or ''),
        message=message or (map_obj.message or '')
    )
    return snapshot

@transaction.atomic
def create_layer_version(layer_instance, changed_by=None, change_message=None):
    old_snapshot = _serialize_instance(layer_instance)
    layer_instance.version_number = (layer_instance.version_number or 1) + 1
    if change_message:
        layer_instance.message = change_message
    layer_instance.updated_at = timezone.now()
    layer_instance.save()
    LayerVersion.objects.create(
        layer=layer_instance,
        version=layer_instance.version_number,
        data=new_snapshot
    )
    new_snapshot = _serialize_instance(layer_instance)
    diff = compute_diff_deep(old_snapshot, new_snapshot)
    # 审计
    AuditLog.objects.create(
        user=None, action='VERSION', resource_type='Layer', resource_id=layer_instance.id,
        meta={'diff': diff, 'new_version': layer_instance.version_number, 'by': changed_by, 'message': change_message}
    )
    return {'layer_id': layer_instance.id, 'new_version': layer_instance.version_number, 'diff': diff}

@transaction.atomic
def create_map_version(map_instance, changed_by=None, change_message=None):
    old_snapshot = _serialize_instance(map_instance)
    old_version = map_instance.version_number or 1
    map_instance.version_number = old_version + 1
    if change_message:
        map_instance.message = change_message
    map_instance.updated_at = timezone.now()
    map_instance.save()
    MapVersionSnapshot.objects.create(from_map=map_instance, to_map=map_instance)
    new_snapshot = _serialize_instance(map_instance)
    diff = compute_diff_deep(old_snapshot, new_snapshot)
    # 归档固定版本快照
    _archive_map_snapshot(map_instance, author=map_instance.author, message=change_message or '')
    # 审计
    AuditLog.objects.create(
        user=None, action='VERSION', resource_type='Map', resource_id=map_instance.id,
        meta={'diff': diff, 'new_version': map_instance.version_number, 'by': changed_by, 'message': change_message}
    )
    return {'map_id': map_instance.id, 'new_version': map_instance.version_number, 'diff': diff}

def _validate_and_prepare_import_payload(payload: dict):
    errors = []
    if 'import_type' not in payload:
        errors.append('import_type required (MAP / LAYER)')
    if 'data' not in payload:
        errors.append('data required')
    return (len(errors) == 0, errors)

@transaction.atomic
def import_json_payload(payload: dict, performed_by=None):
    ok, errors = _validate_and_prepare_import_payload(payload)
    if not ok:
        return {'status': 'FAILED', 'errors': errors}

    import_type = payload['import_type']
    data = payload['data']
    bind_map = payload.get('bind_map')
    bind_layer = payload.get('bind_layer')
    message = payload.get('message', '')

    results = {'created': [], 'updated': [], 'conflicts': [], 'errors': [], 'version_changes': []}

    job = ResourceImportJob.objects.create(
        import_type=import_type,
        target_map=Map.objects.filter(id=bind_map).first() if bind_map else None,
        target_layer=Layer.objects.filter(id=bind_layer).first() if bind_layer else None,
        imported_data=data,
        status='PENDING',
        user=None,  # 调用方可在视图层传入 request.user
        logs={}
    )

    try:
        if import_type == 'MAP':
            map_info = data.get('map')
            layers = data.get('layers', [])
            if not map_info:
                raise ValidationError("MAP import requires top-level 'map' object")

            # upsert map
            map_obj = Map.objects.filter(id=map_info.get('id')).first() if map_info.get('id') else None
            if map_obj:
                before = _serialize_instance(map_obj)
                for k, v in map_info.items():
                    if k in ['id', 'created_at', 'updated_at']: continue
                    setattr(map_obj, k, v)
                map_obj.full_clean(); map_obj.save()
                after = _serialize_instance(map_obj)
                results['updated'].append({'map': map_obj.id})
                diff = compute_diff_deep(before, after)
                results['version_changes'].append(create_map_version(map_obj, performed_by, message))
                job.logs['map_diff'] = diff
            else:
                map_obj = Map.objects.create(
                    version_number=map_info.get('version_number', 1),
                    author=map_info.get('author', ''),
                    message=map_info.get('message', '')
                )
                results['created'].append({'map': map_obj.id})
                # 初次创建也做归档
                _archive_map_snapshot(map_obj, author=map_obj.author, message=map_obj.message)

            # layers
            job.logs['layer_diffs'] = []
            for l in layers:
                layer_obj = Layer.objects.filter(id=l.get('id')).first() if l.get('id') else None
                if layer_obj:
                    incoming_version = l.get('version_number', 1)
                    if incoming_version <= (layer_obj.version_number or 1):
                        results['conflicts'].append({'layer': layer_obj.id, 'reason': 'incoming version not newer'})
                        continue
                    before = _serialize_instance(layer_obj)
                    for k, v in l.items():
                        if k in ['id', 'created_at', 'updated_at']: continue
                        setattr(layer_obj, k, v)
                    layer_obj.full_clean(); layer_obj.save()
                    after = _serialize_instance(layer_obj)
                    results['updated'].append({'layer': layer_obj.id})
                    vc = create_layer_version(layer_obj, performed_by, message)
                    results['version_changes'].append(vc)
                    job.logs['layer_diffs'].append({'layer_id': layer_obj.id, 'diff': compute_diff_deep(before, after)})
                else:
                    new_layer = Layer.objects.create(
                        type=l.get('type'),
                        version_number=l.get('version_number', 1),
                        author=l.get('author', ''),
                        message=l.get('message', '')
                    )
                    MapLayer.objects.get_or_create(map=map_obj, layer=new_layer)
                    results['created'].append({'layer': new_layer.id})
                    results['version_changes'].append({
                        'layer_id': new_layer.id, 'new_version': new_layer.version_number, 'diff': {'created': True}
                    })

        elif import_type == 'LAYER':
            l = data.get('layer')
            if not l:
                raise ValidationError("LAYER import requires top-level 'layer' object")
            layer_obj = Layer.objects.filter(id=l.get('id')).first() if l.get('id') else None
            if layer_obj:
                incoming_version = l.get('version_number', 1)
                if incoming_version <= (layer_obj.version_number or 1):
                    results['conflicts'].append({'layer': layer_obj.id, 'reason': 'incoming version not newer'})
                else:
                    before = _serialize_instance(layer_obj)
                    for k, v in l.items():
                        if k in ['id', 'created_at', 'updated_at']: continue
                        setattr(layer_obj, k, v)
                    layer_obj.full_clean(); layer_obj.save()
                    after = _serialize_instance(layer_obj)
                    results['updated'].append({'layer': layer_obj.id})
                    vc = create_layer_version(layer_obj, performed_by, message)
                    results['version_changes'].append(vc)
                    job.logs['layer_diff'] = compute_diff_deep(before, after)
            else:
                new_layer = Layer.objects.create(
                    type=l.get('type'),
                    version_number=l.get('version_number', 1),
                    author=l.get('author', ''),
                    message=l.get('message', '')
                )
                results['created'].append({'layer': new_layer.id})
                results['version_changes'].append({'layer_id': new_layer.id, 'new_version': new_layer.version_number, 'diff': {'created': True}})
                layer_obj = new_layer

            if payload.get('bind_map'):
                map_obj = Map.objects.filter(id=payload['bind_map']).first()
                if map_obj:
                    MapLayer.objects.get_or_create(map=map_obj, layer=layer_obj)

        else:
            raise ValidationError("Unsupported import_type (must be MAP or LAYER)")

        job.status = 'SUCCESS'
        job.completed_at = timezone.now()
        job.save()

        AuditLog.objects.create(
            user=job.user, action='IMPORT',
            resource_type=import_type, resource_id=job.id,
            meta={'results': results, 'logs': job.logs}
        )
        return {'status': 'SUCCESS', 'results': results}
    except Exception as exc:
        job.status = 'FAILED'
        job.completed_at = timezone.now()
        job.logs['error'] = str(exc)
        job.save()
        AuditLog.objects.create(
            user=job.user, action='IMPORT', resource_type=import_type, resource_id=job.id,
            meta={'error': str(exc)}
        )
        return {'status': 'FAILED', 'error': str(exc), 'partial_results': results}

@transaction.atomic
def rollback_map_to_version(map_id: int, version_number: int, performed_by=None, message: str = '') -> dict:
    """
    根据 MapArchive 快照将 Map 回滚到历史版本：
    - 用快照覆盖 Map 当前元信息
    - 重新同步 MapLayer（以快照中的 layers 为准）
    注意：此示例回滚的是 Map 及 Layer 元数据（不含 Layer 内更深层资源）。
    """
    archive = MapArchive.objects.filter(map_id=map_id, version_number=version_number).first()
    if not archive:
        raise ObjectDoesNotExist(f"No archived snapshot for map {map_id} version {version_number}")

    # 读取快照
    snap = archive.snapshot
    snap_map = snap.get('map') or {}
    snap_layers = snap.get('layers', [])

    m = Map.objects.get(id=map_id)

    before = _serialize_instance(m)
    # 覆盖 Map 基元字段（避免覆盖 id/时间）
    for k, v in snap_map.items():
        if k in ['id', 'created_at', 'updated_at']: continue
        setattr(m, k, v)
    m.updated_at = timezone.now()
    m.save()

    # 重建 MapLayer 关联（保持 Layer 表元信息为快照中内容）
    # 1) 清除现有关联
    MapLayer.objects.filter(map=m).delete()

    # 2) 将快照中的 layer upsert 并绑定
    for l in snap_layers:
        lay = Layer.objects.filter(id=l.get('id')).first() if l.get('id') else None
        if lay:
            for k, v in l.items():
                if k in ['id', 'created_at', 'updated_at']: continue
                setattr(lay, k, v)
            lay.save()
        else:
            lay = Layer.objects.create(
                type=l.get('type'),
                version_number=l.get('version_number', 1),
                author=l.get('author', ''),
                message=l.get('message', '')
            )
            # 如果快照里有 id，你也可以在迁移时允许手动设置 pk，但 Django 默认不建议直接改 pk
        MapLayer.objects.get_or_create(map=m, layer=lay)

    after = _serialize_instance(m)
    diff = compute_diff_deep(before, after)

    # 回滚后创建新版本（保持版本线性推进）
    vc = create_map_version(m, changed_by=performed_by, change_message=message or f"Rollback to v{version_number}")

    AuditLog.objects.create(
        user=None, action='ROLLBACK', resource_type='Map', resource_id=m.id,
        meta={'rolled_to': version_number, 'map_diff': diff, 'new_version': vc['new_version']}
    )

    return {'rolled_to': version_number, 'map_id': m.id, 'version_after_rollback': vc['new_version'], 'map_diff': diff}
