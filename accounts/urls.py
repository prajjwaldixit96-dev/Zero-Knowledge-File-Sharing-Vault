from django.urls import path
from . import views

urlpatterns = [
    path('',views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('reset-password/<str:token>/', views.reset_password_view, name='reset_password'),
    # API
    path('api/profile/update/', views.update_profile, name='update_profile'),
    path('api/password/change/', views.change_password, name='change_password'),
    path('api/security/update/', views.update_security_settings, name='update_security'),
    path('api/avatar/update/', views.update_avatar, name='update_avatar'),
]
