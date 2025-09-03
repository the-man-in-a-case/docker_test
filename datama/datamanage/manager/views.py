from django.shortcuts import render

# Create your views here.
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from django.shortcuts import get_object_or_404
from django.db import transaction
from db.models import Map, Layer, MapLayer
from . import services
from .models import MapVersionSnapshot
from .serializers import MapSerializer, LayerSerializer, MapArchiveSerializer
import json
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from .permissions import IsAdminOrReadOnly
from .utils.data_migration import migrate_resource


class DataMigrationAPIView(APIView):
    """
    接收请求，执行数据迁移
    """

    def post(self, request, *args, **kwargs):
        resource_type = request.data.get("resource_type")
        resource_id = request.data.get("resource_id")
        version = request.data.get("version")
        target_db_config = request.data.get("target_db_config")

        try:
            new_id = migrate_resource(resource_type, resource_id, version, target_db_config)
            return Response({"status": "success", "new_id": new_id}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class MapExportView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]
    def get(self, request, map_id):
        mode = request.query_params.get('mode', 'latest')
        version = request.query_params.get('version')
        try:
            payload = services.export_map(map_id, version_number=version if mode == 'fixed' else None)
            return Response(payload)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)

class LayerExportView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]
    def get(self, request, layer_id):
        try:
            payload = services.export_layer(layer_id, include_related=True)
            return Response(payload)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)

class MapDetailView(generics.RetrieveAPIView):
    queryset = Map.objects.all()
    serializer_class = MapSerializer
    lookup_field = 'id'
    lookup_url_kwarg = 'map_id'
    permission_classes = [IsAuthenticatedOrReadOnly]

class LayerDetailView(generics.RetrieveAPIView):
    queryset = Layer.objects.all()
    serializer_class = LayerSerializer
    lookup_field = 'id'
    lookup_url_kwarg = 'layer_id'
    permission_classes = [IsAuthenticatedOrReadOnly]

class MapLayersListView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]
    def get(self, request, map_id):
        map_obj = get_object_or_404(Map, id=map_id)
        map_layers = map_obj.map_layers.select_related('layer').all()
        layers = [ LayerSerializer(ml.layer).data for ml in map_layers ]
        return Response({'map': MapSerializer(map_obj).data, 'layers': layers})

class VersionListView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]
    def get(self, request, resource_type, resource_id):
        if resource_type == 'map':
            m = get_object_or_404(Map, id=resource_id)
            archives = MapArchive.objects.filter(map=m).order_by('version_number')
            return Response({
                'map': MapSerializer(m).data,
                'current_version': m.version_number,
                'archives': MapArchiveSerializer(archives, many=True).data
            })
        elif resource_type == 'layer':
            l = get_object_or_404(Layer, id=resource_id)
            return Response({
                'layer': LayerSerializer(l).data,
                'version_number': l.version_number
            })
        return Response({'error': 'resource_type must be map or layer'}, status=status.HTTP_400_BAD_REQUEST)

class ImportJSONView(APIView):
    permission_classes = [IsAdminOrReadOnly]
    def post(self, request):
        payload = request.data
        res = services.import_json_payload(payload, performed_by=str(request.user) if request.user.is_authenticated else None)
        return Response(res, status=status.HTTP_200_OK if res.get('status') == 'SUCCESS' else status.HTTP_400_BAD_REQUEST)

class MapRollbackView(APIView):
    """
    POST /api/maps/{id}/rollback/
    body: {"version_number": <int>, "message": "optional"}
    """
    permission_classes = [IsAdminOrReadOnly]
    def post(self, request, map_id):
        version_number = request.data.get('version_number')
        message = request.data.get('message', '')
        if version_number is None:
            return Response({'error': 'version_number required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            result = services.rollback_map_to_version(map_id, int(version_number),
                                                      performed_by=str(request.user) if request.user.is_authenticated else None,
                                                      message=message)
            return Response(result)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)