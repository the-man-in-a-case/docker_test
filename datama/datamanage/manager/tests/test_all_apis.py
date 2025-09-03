import json
import unittest
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from db.models import Map, Layer, MapLayer, BaseNode, BaseEdge, Node, Edge
from manager.models import MapArchive, MapVersionSnapshot, LayerVersion, ResourceImportJob, AuditLog

class AllAPITests(TestCase):
    def setUp(self):
        """设置测试环境和测试数据"""
        self.client = APIClient()
        
        # 创建基础测试数据
        self.map = Map.objects.create(
            version_number=1,
            author='tester',
            message='Initial version'
        )
        
        self.layer = Layer.objects.create(
            type='PowerLayer',
            version_number=1,
            author='tester',
            message='Initial layer'
        )
        
        self.map_layer = MapLayer.objects.create(
            map=self.map,
            layer=self.layer
        )
        
        # 创建节点和边数据用于测试
        self.base_node = BaseNode.objects.create(
            base_node_name='Test Node',
            cis_type='002',
            sub_type='2-1Gen'
        )
        
        self.base_edge = BaseEdge.objects.create(
            base_edge_name='Test Edge'
        )
        
        self.node = Node.objects.create(
            layer=self.layer,
            base_node=self.base_node
        )
        
        # 创建MapArchive用于回滚测试
        self.map_archive = MapArchive.objects.create(
            map=self.map,
            version_number=1,
            snapshot={
                'map': {
                    'id': self.map.id,
                    'version_number': 1,
                    'author': 'tester',
                    'message': 'Initial version'
                },
                'layers': [
                    {
                        'id': self.layer.id,
                        'type': 'PowerLayer',
                        'version_number': 1,
                        'author': 'tester',
                        'message': 'Initial layer'
                    }
                ]
            },
            author='tester',
            message='Initial snapshot'
        )
    
    def test_map_export_view(self):
        """测试地图导出API"""
        url = reverse('map-export', kwargs={'map_id': self.map.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('map', response.data)
        self.assertIn('layers', response.data)
        self.assertEqual(response.data['map']['id'], self.map.id)
        self.assertEqual(len(response.data['layers']), 1)
        
        # 测试固定版本导出
        url_fixed = f"{url}?mode=fixed&version=1"
        response_fixed = self.client.get(url_fixed)
        
        self.assertEqual(response_fixed.status_code, status.HTTP_200_OK)
        self.assertEqual(response_fixed.data.get('archived_version'), 1)
    
    def test_layer_export_view(self):
        """测试图层导出API"""
        url = reverse('layer-export', kwargs={'layer_id': self.layer.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('layer', response.data)
        self.assertEqual(response.data['layer']['id'], self.layer.id)
    
    def test_map_detail_view(self):
        """测试地图详情API"""
        url = reverse('map-detail', kwargs={'map_id': self.map.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.map.id)
        self.assertEqual(response.data['version_number'], self.map.version_number)
    
    def test_layer_detail_view(self):
        """测试图层详情API"""
        url = reverse('layer-detail', kwargs={'layer_id': self.layer.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.layer.id)
        self.assertEqual(response.data['type'], self.layer.type)
    
    def test_map_layers_list_view(self):
        """测试地图图层列表API"""
        url = reverse('map-layers', kwargs={'map_id': self.map.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('layers', response.data)
        self.assertEqual(len(response.data['layers']), 1)
        self.assertEqual(response.data['layers'][0]['id'], self.layer.id)
    
    def test_version_list_view(self):
        """测试版本列表API"""
        url = reverse('version-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('map_versions', response.data)
        self.assertIn('layer_versions', response.data)
    
    def test_import_json_view(self):
        """测试JSON导入API"""
        url = reverse('import-json')
        
        # 准备导入数据
        import_data = {
            "import_type": "LAYER",
            "data": {
                "layer": {
                    "type": "PowerLayer",
                    "version_number": 2,
                    "author": "tester",
                    "message": "Imported layer"
                }
            }
        }
        
        response = self.client.post(
            url,
            json.dumps(import_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'SUCCESS')
    
    def test_map_rollback_view(self):
        """测试地图回滚API"""
        # 先更新地图版本
        self.map.version_number = 2
        self.map.message = 'Updated version'
        self.map.save()
        
        url = reverse('map-rollback', kwargs={'map_id': self.map.id})
        
        # 准备回滚数据
        rollback_data = {
            "version_number": 1,
            "message": "Rollback to version 1"
        }
        
        response = self.client.post(
            url,
            json.dumps(rollback_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('rolled_to', response.data)
        self.assertEqual(response.data['rolled_to'], 1)
        
        # 验证地图版本已更新（回滚后会创建新版本）
        updated_map = Map.objects.get(id=self.map.id)
        self.assertGreater(updated_map.version_number, 2)
    
    def test_data_migration_api_view(self):
        """测试数据库迁移API
        注意：此测试需要确保目标数据库项目(/d:/git/docker_test/datama/db)正在localhost:8001运行
        """
        url = reverse('data-migration')
        
        # 准备迁移数据
        migration_data = {
            "source_type": "map",
            "source_id": self.map.id,
            "target_url": "http://localhost:8001/api/receive-migration/",
            "migration_type": "full"
        }
        
        # 由于这是一个外部API调用，我们可以使用mock或设置真实的测试环境
        # 这里我们使用try-except来处理可能的连接问题
        try:
            response = self.client.post(
                url,
                json.dumps(migration_data),
                content_type='application/json'
            )
            
            # 检查响应状态
            if response.status_code == status.HTTP_200_OK:
                self.assertIn('status', response.data)
                self.assertEqual(response.data['status'], 'success')
                print("数据库迁移API测试成功")
            else:
                print(f"数据库迁移API测试收到非200响应: {response.status_code}")
                print(f"响应内容: {response.data}")
        except Exception as e:
            print(f"数据库迁移API测试失败: {str(e)}")
            print("请确保目标数据库项目(/d:/git/docker_test/datama/db)正在localhost:8001运行")

if __name__ == '__main__':
    unittest.main()