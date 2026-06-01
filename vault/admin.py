from django.contrib import admin
from .models import VaultFile, ShareLink, FileAccess, ActivityLog


@admin.register(VaultFile)
class VaultFileAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'file_type', 'size', 'is_encrypted', 'uploaded_at', 'is_deleted']
    list_filter = ['file_type', 'is_encrypted', 'is_deleted']
    search_fields = ['name', 'owner__email']
    readonly_fields = ['uploaded_at', 'updated_at']


@admin.register(ShareLink)
class ShareLinkAdmin(admin.ModelAdmin):
    list_display = ['file', 'created_by', 'token', 'is_active', 'download_count', 'expires_at', 'created_at']
    list_filter = ['is_active']
    search_fields = ['file__name', 'created_by__email', 'token']


@admin.register(FileAccess)
class FileAccessAdmin(admin.ModelAdmin):
    list_display = ['file', 'shared_with_email', 'permission', 'status', 'granted_by', 'granted_at']
    list_filter = ['permission', 'status']
    search_fields = ['shared_with_email', 'file__name']


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'file', 'description', 'ip_address', 'created_at']
    list_filter = ['action']
    search_fields = ['user__email', 'description', 'file__name']
    readonly_fields = ['created_at']
