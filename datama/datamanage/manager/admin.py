# admin.py
from django.contrib import admin
from .models import MapArchive, ResourceImportJob, AuditLog, MapVersionSnapshot, LayerVersion


@admin.register(MapArchive)
class MapArchiveAdmin(admin.ModelAdmin):
    list_display = ("id", "map", "version_number", "author", "created_at")
    list_filter = ("created_at", "author")
    search_fields = ("map__name", "author", "message")
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)

    fieldsets = (
        ("基本信息", {
            "fields": ("map", "version_number", "author", "message")
        }),
        ("快照", {
            "fields": ("snapshot",),
        }),
        ("时间", {
            "fields": ("created_at",),
        }),
    )


@admin.register(ResourceImportJob)
class ResourceImportJobAdmin(admin.ModelAdmin):
    list_display = ("id", "import_type", "target_map", "target_layer",
                    "status", "user", "created_at", "completed_at")
    list_filter = ("status", "import_type", "created_at", "completed_at")
    search_fields = ("target_map__name", "target_layer__name", "user__username")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "completed_at")

    fieldsets = (
        ("基本信息", {
            "fields": ("import_type", "target_map", "target_layer", "user", "status")
        }),
        ("导入数据", {
            "fields": ("imported_data", "logs"),
        }),
        ("时间", {
            "fields": ("created_at", "completed_at"),
        }),
    )


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "action", "resource_type",
                    "resource_id", "created_at")
    list_filter = ("action", "resource_type", "created_at")
    search_fields = ("user__username", "resource_type", "resource_id")
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)

    fieldsets = (
        ("操作信息", {
            "fields": ("user", "action", "resource_type", "resource_id")
        }),
        ("详情", {
            "fields": ("meta",),
        }),
        ("时间", {
            "fields": ("created_at",),
        }),
    )

# 新增MapVersionSnapshot模型的admin配置
@admin.register(MapVersionSnapshot)
class MapVersionSnapshotAdmin(admin.ModelAdmin):
    list_display = ("id", "from_map", "to_map", "created_at")
    list_filter = ("created_at",)
    search_fields = ("from_map_id", "to_map_id")
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)
    raw_id_fields = ("from_map", "to_map")

    fieldsets = (
        ("版本快照信息", {
            "fields": ("from_map", "to_map")
        }),
        ("时间", {
            "fields": ("created_at",),
        }),
    )

# 新增LayerVersion模型的admin配置
@admin.register(LayerVersion)
class LayerVersionAdmin(admin.ModelAdmin):
    list_display = ("id", "layer", "version", "user", "created_at")
    list_filter = ("created_at", "user")
    search_fields = ("layer_id", "user__username")
    ordering = ("-layer_id", "-version")
    readonly_fields = ("created_at",)
    raw_id_fields = ("layer", "user")

    fieldsets = (
        ("图层版本信息", {
            "fields": ("layer", "version", "user")
        }),
        ("版本数据", {
            "fields": ("data",),
            "classes": ("collapse",)
        }),
        ("时间", {
            "fields": ("created_at",),
        }),
    )
