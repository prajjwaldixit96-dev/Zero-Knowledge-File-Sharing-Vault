from django.urls import path
from . import views

urlpatterns = [
    # Main app routes
    path('', views.dashboard, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('upload/', views.upload_view, name='upload'),
    path('files/', views.files_view, name='files'),
    path('share/', views.share_view, name='share'),
    path('access/', views.access_view, name='access'),
    path('logs/', views.logs_view, name='logs'),
    path('settings/', views.settings_view, name='settings'),
    path('admin-panel/', views.admin_panel_view, name='admin_panel'),

    # File operations
    path('files/<int:file_id>/download/', views.file_download, name='file_download'),
    path('files/<int:file_id>/delete/', views.file_delete, name='file_delete'),
    path('files/<int:file_id>/rename/', views.file_rename, name='file_rename'),

    # Share links
    path('api/share/generate/', views.generate_share_link, name='generate_share_link'),
    path('api/share/<int:link_id>/revoke/', views.revoke_share_link, name='revoke_share_link'),
    path('s/<str:token>/', views.public_share_view, name='public_share'),

    # Access control
    path('api/access/grant/', views.grant_access, name='grant_access'),
    path('api/access/<int:rule_id>/revoke/', views.revoke_access, name='revoke_access'),

    # Admin
    path('api/admin/users/<int:user_id>/toggle/', views.admin_toggle_user, name='admin_toggle_user'),
    path('api/admin/users/<int:user_id>/delete/', views.admin_delete_user, name='admin_delete_user'),

    # APIs
    path('api/files/', views.api_files_list, name='api_files'),
    path('api/storage/', views.api_storage_info, name='api_storage'),
]
