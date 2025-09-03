from django.urls import path
from .views import (
    MapExportView, LayerExportView, MapDetailView, LayerDetailView,
    MapLayersListView, VersionListView, ImportJSONView, DataMigrationAPIView, MapRollbackView
)

urlpatterns = [
    path('maps/<int:map_id>/export/', MapExportView.as_view(), name='map-export'),
    path('layers/<int:layer_id>/export/', LayerExportView.as_view(), name='layer-export'),
    path('maps/<int:map_id>/', MapDetailView.as_view(), name='map-detail'),
    path('layers/<int:layer_id>/', LayerDetailView.as_view(), name='layer-detail'),
    path('maps/<int:map_id>/layers/', MapLayersListView.as_view(), name='map-layers'),
    path('versions/<str:resource_type>/<int:resource_id>/', VersionListView.as_view(), name='versions'),
    path('import/', ImportJSONView.as_view(), name='import-json'),
    path('migration/', DataMigrationAPIView.as_view(), name='data-migration'),
    path('maps/<int:map_id>/rollback/', MapRollbackView.as_view(), name='map-rollback'),
]
