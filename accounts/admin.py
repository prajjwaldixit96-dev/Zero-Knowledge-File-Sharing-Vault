from django.contrib import admin
from .models import UserProfile, PasswordResetToken

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'plan', 'storage_used_gb', 'is_admin', 'is_suspended', 'created_at']
    list_filter = ['plan', 'is_admin', 'is_suspended']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']

@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = ['user', 'created_at', 'used']
    list_filter = ['used']
