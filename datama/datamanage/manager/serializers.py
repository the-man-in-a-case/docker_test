from rest_framework import serializers
from db.models import Map, Layer, MapLayer

class LayerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Layer
        fields = '__all__'

class MapSerializer(serializers.ModelSerializer):
    class Meta:
        model = Map
        fields = '__all__'

class MapLayerSerializer(serializers.ModelSerializer):
    class Meta:
        model = MapLayer
        fields = '__all__'

from .models import MapArchive, ResourceImportJob, AuditLog

class MapArchiveSerializer(serializers.ModelSerializer):
    class Meta:
        model = MapArchive
        fields = '__all__'

class ResourceImportJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResourceImportJob
        fields = '__all__'

class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = '__all__'