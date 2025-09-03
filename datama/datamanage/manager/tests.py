# maps/tests/test_versioning.py
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from db.models import Map, Layer, MapLayer
from .models import MapArchive

class VersioningFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.map = Map.objects.create(version_number=1, author='tester', message='init')
        self.layer = Layer.objects.create(type='PowerLayer', version_number=1, author='tester', message='init')
        MapLayer.objects.create(map=self.map, layer=self.layer)

    def test_export_latest_map(self):
        url = reverse('map-export', kwargs={'map_id': self.map.id})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('map', resp.data)
        self.assertIn('layers', resp.data)

    def test_import_layer_conflict(self):
        # 先将当前 layer 版本设为2
        self.layer.version_number = 2
        self.layer.save()
        url = reverse('import-json')
        payload = {
            "import_type": "LAYER",
            "data": {
                "layer": {
                    "id": self.layer.id,
                    "type": "PowerLayer",
                    "version_number": 2,  # 与现有相同 => 冲突
                    "author": "user",
                    "message": "same version"
                }
            }
        }
        resp = self.client.post(url, payload, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('conflicts', resp.data.get('partial_results', {}))

    def test_map_archive_and_fixed_export(self):
        # 创建新版本（触发归档）
        self.map.version_number = 2
        self.map.save()
        # 手工归档一次（正常流程在 create_map_version 里自动完成）
        MapArchive.objects.create(map=self.map, version_number=2,
                                  snapshot={"map":{"id": self.map.id, "version_number":2}, "layers":[]},
                                  author='tester', message='archived')
        url_fixed = reverse('map-export', kwargs={'map_id': self.map.id}) + '?mode=fixed&version=2'
        resp = self.client.get(url_fixed)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data.get('archived_version'), '2' if isinstance(resp.data.get('archived_version'), str) else 2)

    def test_rollback_map(self):
        # 先创建归档 v1
        MapArchive.objects.create(map=self.map, version_number=1,
                                  snapshot={"map":{"id": self.map.id, "version_number":1, "author":"tester","message":"init"},
                                            "layers":[{"id": self.layer.id, "type":"PowerLayer", "version_number":1, "author":"tester", "message":"init"}]},
                                  author='tester', message='init snapshot')
        # 提升当前 map 到 v2
        self.map.version_number = 2
        self.map.message = 'changed'
        self.map.save()

        url = reverse('map-rollback', kwargs={'map_id': self.map.id})
        resp = self.client.post(url, {"version_number": 1, "message": "rollback to v1"}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.map.refresh_from_db()
        self.assertGreaterEqual(self.map.version_number, 2)  # 回滚后仍会产生新版本（线性前进）
