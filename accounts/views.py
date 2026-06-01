import secrets
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone

from .forms import LoginForm, RegisterForm, ForgotPasswordForm, ResetPasswordForm, ProfileUpdateForm, ChangePasswordForm
from .models import PasswordResetToken, UserProfile
from vault.models import ActivityLog


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            user = form.get_user()
            remember = form.cleaned_data.get('remember_me', False)
            login(request, user)
            if not remember:
                request.session.set_expiry(0)
            # Log activity
            ActivityLog.objects.create(
                user=user,
                action='login',
                description=f'Login from {request.META.get("HTTP_USER_AGENT", "Unknown")[:100]}',
                ip_address=get_client_ip(request),
            )
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid email or password.')
    return render(request, 'accounts/login.html', {'form': form})


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = RegisterForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            user = form.save()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            ActivityLog.objects.create(
                user=user,
                action='login',
                description='Account created and first login',
                ip_address=get_client_ip(request),
            )
            messages.success(request, 'Welcome to ZK Vault! Your encrypted vault is ready.')
            return redirect('dashboard')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
    return render(request, 'accounts/register.html', {'form': form})


def logout_view(request):
    if request.user.is_authenticated:
        ActivityLog.objects.create(
            user=request.user,
            action='logout',
            description='User logged out',
            ip_address=get_client_ip(request),
        )
    logout(request)
    return redirect('index')


def forgot_password_view(request):
    form = ForgotPasswordForm(request.POST or None)
    sent = False
    if request.method == 'POST' and form.is_valid():
        email = form.cleaned_data['email']
        try:
            user = User.objects.get(email=email)
            token_str = secrets.token_urlsafe(48)
            PasswordResetToken.objects.create(user=user, token=token_str)
            # In production: send email with reset link
            # send_reset_email(user, token_str)
            print(f"[DEV] Reset link: http://localhost:8000/reset-password/{token_str}/")
        except User.DoesNotExist:
            pass  # Don't reveal if email exists
        sent = True
    return render(request, 'accounts/forgot_password.html', {'form': form, 'sent': sent})


def reset_password_view(request, token):
    token_obj = get_object_or_404(PasswordResetToken, token=token)
    if not token_obj.is_valid():
        messages.error(request, 'This reset link has expired or already been used.')
        return redirect('forgot_password')
    form = ResetPasswordForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = token_obj.user
        user.set_password(form.cleaned_data['new_password'])
        user.save()
        token_obj.used = True
        token_obj.save()
        messages.success(request, 'Password updated successfully. Please log in.')
        return redirect('login')
    return render(request, 'accounts/reset_password.html', {'form': form, 'token': token})


@login_required
@require_POST
def update_profile(request):
    form = ProfileUpdateForm(request.POST, instance=request.user)
    if form.is_valid():
        user = form.save(commit=False)
        # Update email → username sync
        user.username = form.cleaned_data['email']
        user.save()
        ActivityLog.objects.create(
            user=request.user,
            action='settings_update',
            description='Profile information updated',
            ip_address=get_client_ip(request),
        )
        return JsonResponse({'status': 'ok', 'message': 'Profile updated successfully'})
    return JsonResponse({'status': 'error', 'message': str(form.errors)}, status=400)


@login_required
@require_POST
def change_password(request):
    form = ChangePasswordForm(request.user, request.POST)
    if form.is_valid():
        request.user.set_password(form.cleaned_data['new_password'])
        request.user.save()
        update_session_auth_hash(request, request.user)
        ActivityLog.objects.create(
            user=request.user,
            action='settings_update',
            description='Master password changed',
            ip_address=get_client_ip(request),
        )
        return JsonResponse({'status': 'ok', 'message': 'Password changed successfully'})
    return JsonResponse({'status': 'error', 'message': str(form.errors)}, status=400)


@login_required
@require_POST
def update_security_settings(request):
    profile = request.user.profile
    profile.two_fa_enabled = request.POST.get('two_fa_enabled') == 'true'
    profile.login_notifications = request.POST.get('login_notifications') == 'true'
    profile.session_timeout = request.POST.get('session_timeout') == 'true'
    profile.save()
    ActivityLog.objects.create(
        user=request.user,
        action='settings_update',
        description='Security settings updated',
        ip_address=get_client_ip(request),
    )
    return JsonResponse({'status': 'ok', 'message': 'Security settings saved'})


@login_required
@require_POST
def update_avatar(request):
    if 'avatar' in request.FILES:
        profile = request.user.profile
        profile.avatar = request.FILES['avatar']
        profile.save()
        return JsonResponse({'status': 'ok', 'url': profile.avatar.url})
    return JsonResponse({'status': 'error', 'message': 'No file provided'}, status=400)


def get_client_ip(request):
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def index(request):
    return render(request, 'index.html')
