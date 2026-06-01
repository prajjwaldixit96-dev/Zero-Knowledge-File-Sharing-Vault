import os
import json
from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse, FileResponse, Http404, HttpResponse
from django.views.decorators.http import require_POST, require_GET
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count
from django.core.files.base import ContentFile
from django.conf import settings

# ── ENCRYPTION ──
from cryptography.fernet import Fernet

def get_fernet():
    """Return Fernet instance using key from settings."""
    key = settings.ENCRYPTION_KEY
    if isinstance(key, str):
        key = key.encode()
    return Fernet(key)

from .models import VaultFile, ShareLink, FileAccess, ActivityLog
from django.core.mail import send_mail
from django.template.loader import render_to_string
from .forms import ShareLinkForm, FileAccessForm
from .utils import get_file_type, get_client_ip, format_file_size, get_dashboard_stats




# ──────────────────────────────────────────────────────────────────────────────
# EMAIL HELPER — Access Grant Notification
# ──────────────────────────────────────────────────────────────────────────────
def _send_access_grant_email(granted_by, recipient_email, vault_file, permission, expires_at, request):
    from django.core.mail import send_mail

    granter_name  = granted_by.get_full_name().strip() or granted_by.email
    perm_label    = {'view': 'View Only', 'download': 'View & Download', 'manage': 'Full Manage'}.get(permission, permission.capitalize())
    access_url    = request.build_absolute_uri('/access/')
    register_url  = request.build_absolute_uri('/register/')
    expiry_text   = expires_at.strftime('%d %b %Y, %H:%M UTC') if expires_at else 'No expiry (permanent)'

    subject = f'[ZK Vault] {granter_name} has shared a file with you'

    plain_body = f"""Hello,

{granter_name} ({granted_by.email}) has granted you access to a file on ZK Vault.

File       : {vault_file.name}
Permission : {perm_label}
Expires    : {expiry_text}

To access this file, please log in to ZK Vault:
{access_url}

If you do not have a ZK Vault account, please register first using this email address ({recipient_email}):
{register_url}

— ZK Vault Security Team
"""

    html_body = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#0f1117;font-family:Arial,Helvetica,sans-serif;">
  <div style="max-width:540px;margin:40px auto;padding:0 16px;">
    <div style="background:linear-gradient(135deg,#3b82f6 0%,#8b5cf6 100%);border-radius:16px 16px 0 0;padding:36px 32px;text-align:center;">
      <div style="font-size:40px;margin-bottom:10px;">🛡️</div>
      <h1 style="margin:0;color:#ffffff;font-size:22px;font-weight:700;">File Access Granted</h1>
      <p style="margin:8px 0 0;color:rgba(255,255,255,0.75);font-size:13px;">via ZK Vault — Zero Knowledge File Sharing</p>
    </div>
    <div style="background:#1a1d27;border:1px solid rgba(255,255,255,0.07);border-top:none;border-radius:0 0 16px 16px;padding:32px;">
      <p style="margin:0 0 24px;color:#e2e8f0;font-size:15px;line-height:1.6;">
        <strong style="color:#ffffff;">{granter_name}</strong> has granted you access to a file.
      </p>
      <div style="background:#0f1117;border:1px solid rgba(255,255,255,0.06);border-radius:12px;padding:20px 24px;margin-bottom:28px;">
        <table style="width:100%;border-collapse:collapse;">
          <tr>
            <td style="color:#64748b;font-size:13px;padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.04);">📄 File</td>
            <td style="color:#e2e8f0;font-size:14px;font-weight:600;text-align:right;padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.04);">{vault_file.name}</td>
          </tr>
          <tr>
            <td style="color:#64748b;font-size:13px;padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.04);">🔒 Permission</td>
            <td style="text-align:right;padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.04);">
              <span style="background:rgba(16,185,129,0.15);color:#10b981;padding:3px 10px;border-radius:20px;font-size:12px;font-weight:600;">{perm_label}</span>
            </td>
          </tr>
          <tr>
            <td style="color:#64748b;font-size:13px;padding:8px 0;">⏰ Expiry</td>
            <td style="color:#94a3b8;font-size:13px;text-align:right;padding:8px 0;">{expiry_text}</td>
          </tr>
        </table>
      </div>
      <a href="{access_url}" style="display:block;background:linear-gradient(135deg,#3b82f6,#8b5cf6);color:#ffffff;text-align:center;padding:15px 24px;border-radius:10px;text-decoration:none;font-weight:700;font-size:15px;margin-bottom:20px;">
        🔐 Login to ZK Vault — Access Your File
      </a>
    </div>
    <p style="text-align:center;color:#374151;font-size:12px;margin:20px 0 40px;">
      ZK Vault &mdash; End-to-end encrypted file sharing
    </p>
  </div>
</body>
</html>"""

    try:
        send_mail(
            subject=subject,
            message=plain_body,
            from_email=None,
            recipient_list=[recipient_email],
            html_message=html_body,
            fail_silently=False,
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"[ZKVault] Access grant email failed to {recipient_email}: {e}")


# ──────────────────────────────────────────────────────────────────────────────
# DASHBOARD
# ──────────────────────────────────────────────────────────────────────────────
@login_required
def dashboard(request):
    stats = get_dashboard_stats(request.user)
    return render(request, 'vault/dashboard.html', {
        'active_view': 'dash',
        **stats,
    })


# ──────────────────────────────────────────────────────────────────────────────
# FILE UPLOAD — WITH AES-256 ENCRYPTION
# ──────────────────────────────────────────────────────────────────────────────
@login_required
def upload_view(request):
    if request.method == 'POST':
        uploaded_files = request.FILES.getlist('files')
        if not uploaded_files:
            return JsonResponse({'status': 'error', 'message': 'No files provided'}, status=400)

        fernet = get_fernet()
        results = []

        for f in uploaded_files:
            mime  = f.content_type or ''
            ftype = get_file_type(f.name, mime)
            size  = f.size

            # Check storage quota
            profile = request.user.profile
            if profile.storage_used + size > profile.storage_quota:
                results.append({'name': f.name, 'status': 'error', 'message': 'Storage quota exceeded'})
                continue

            # ── ENCRYPT file data ──
            original_data   = f.read()
            encrypted_data  = fernet.encrypt(original_data)
            encrypted_file  = ContentFile(encrypted_data, name=f.name + '.enc')

            vault_file = VaultFile.objects.create(
                owner          = request.user,
                name           = f.name,
                original_name  = f.name,
                file           = encrypted_file,
                file_type      = ftype,
                size           = size,          # store original size
                mime_type      = mime,
                is_encrypted   = True,
                encryption_algo= 'AES-256',
            )

            # Update storage used (original size)
            profile.storage_used += size
            profile.save()

            ActivityLog.objects.create(
                user        = request.user,
                action      = 'upload',
                file        = vault_file,
                description = f'Uploaded {f.name} ({format_file_size(size)}) · AES-256 Encrypted',
                ip_address  = get_client_ip(request),
            )

            results.append({
                'name'  : f.name,
                'status': 'ok',
                'id'    : vault_file.id,
                'size'  : format_file_size(size),
                'type'  : ftype,
            })

        return JsonResponse({'status': 'ok', 'files': results})

    return render(request, 'vault/upload.html', {'active_view': 'upload'})


# ──────────────────────────────────────────────────────────────────────────────
# FILES LIST
# ──────────────────────────────────────────────────────────────────────────────
@login_required
def files_view(request):
    qs = VaultFile.objects.filter(owner=request.user, is_deleted=False)

    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(name__icontains=q)

    ftype = request.GET.get('type', '')
    if ftype and ftype != 'all':
        qs = qs.filter(file_type=ftype)

    sort = request.GET.get('sort', '-uploaded_at')
    sort_map = {
        'name': 'name', '-name': '-name',
        'size': 'size', '-size': '-size',
        '-uploaded_at': '-uploaded_at', 'uploaded_at': 'uploaded_at',
    }
    qs = qs.order_by(sort_map.get(sort, '-uploaded_at'))

    paginator   = Paginator(qs, 20)
    files_page  = paginator.get_page(request.GET.get('page', 1))

    total_size = VaultFile.objects.filter(
        owner=request.user, is_deleted=False
    ).aggregate(total=Sum('size'))['total'] or 0

    return render(request, 'vault/files.html', {
        'active_view'  : 'files',
        'files'        : files_page,
        'total_files'  : qs.count(),
        'total_size'   : format_file_size(total_size),
        'search_query' : q,
        'selected_type': ftype,
        'selected_sort': sort,
    })


# ──────────────────────────────────────────────────────────────────────────────
# FILE DOWNLOAD — WITH AES-256 DECRYPTION
# ──────────────────────────────────────────────────────────────────────────────
@login_required
def file_download(request, file_id):
    vault_file = get_object_or_404(VaultFile, id=file_id, owner=request.user, is_deleted=False)

    try:
        # ── READ encrypted data ──
        encrypted_data = vault_file.file.read()

        # ── DECRYPT ──
        fernet         = get_fernet()
        decrypted_data = fernet.decrypt(encrypted_data)

        # ── Send as original file ──
        response = HttpResponse(decrypted_data, content_type='application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename="{vault_file.name}"'
        response['Content-Length']      = len(decrypted_data)

        ActivityLog.objects.create(
            user        = request.user,
            action      = 'download',
            file        = vault_file,
            description = f'Downloaded {vault_file.name} (decrypted)',
            ip_address  = get_client_ip(request),
        )
        return response

    except Exception as e:
        raise Http404(f"Could not decrypt file: {e}")


# ──────────────────────────────────────────────────────────────────────────────
# FILE DELETE
# ──────────────────────────────────────────────────────────────────────────────
@login_required
@require_POST
def file_delete(request, file_id):
    vault_file = get_object_or_404(VaultFile, id=file_id, owner=request.user, is_deleted=False)
    name = vault_file.name
    vault_file.soft_delete()
    ActivityLog.objects.create(
        user        = request.user,
        action      = 'delete',
        file        = vault_file,
        description = f'Permanently deleted {name}',
        ip_address  = get_client_ip(request),
    )
    return JsonResponse({'status': 'ok', 'message': f'"{name}" deleted successfully'})


# ──────────────────────────────────────────────────────────────────────────────
# FILE RENAME
# ──────────────────────────────────────────────────────────────────────────────
@login_required
@require_POST
def file_rename(request, file_id):
    vault_file = get_object_or_404(VaultFile, id=file_id, owner=request.user, is_deleted=False)
    data     = json.loads(request.body)
    new_name = data.get('name', '').strip()
    if not new_name:
        return JsonResponse({'status': 'error', 'message': 'Name cannot be empty'}, status=400)
    old_name       = vault_file.name
    vault_file.name = new_name
    vault_file.save()
    ActivityLog.objects.create(
        user        = request.user,
        action      = 'rename',
        file        = vault_file,
        description = f'Renamed "{old_name}" → "{new_name}"',
        ip_address  = get_client_ip(request),
    )
    return JsonResponse({'status': 'ok', 'name': new_name})


# ──────────────────────────────────────────────────────────────────────────────
# SHARE VIEW
# ──────────────────────────────────────────────────────────────────────────────
@login_required
def share_view(request):
    files            = VaultFile.objects.filter(owner=request.user, is_deleted=False).order_by('name')
    selected_file_id = request.GET.get('file')
    selected_file    = None
    if selected_file_id:
        try:
            selected_file = files.get(id=selected_file_id)
        except VaultFile.DoesNotExist:
            pass

    share_links = ShareLink.objects.filter(
        created_by=request.user
    ).select_related('file').order_by('-created_at')

    return render(request, 'vault/share.html', {
        'active_view'  : 'share',
        'files'        : files,
        'selected_file': selected_file,
        'share_links'  : share_links,
    })


@login_required
@require_POST
def generate_share_link(request):
    data          = json.loads(request.body)
    file_id       = data.get('file_id')
    expiry        = data.get('expiry', '')
    password      = data.get('password', '')
    max_downloads = int(data.get('max_downloads', 0))
    allow_preview = data.get('allow_preview', True)

    vault_file = get_object_or_404(VaultFile, id=file_id, owner=request.user, is_deleted=False)

    expires_at = None
    if expiry:
        delta_map = {
            '1h' : timedelta(hours=1),
            '24h': timedelta(hours=24),
            '7d' : timedelta(days=7),
            '30d': timedelta(days=30),
        }
        if expiry in delta_map:
            expires_at = timezone.now() + delta_map[expiry]

    link = ShareLink(
        file          = vault_file,
        token         = ShareLink.generate_token(),
        created_by    = request.user,
        expires_at    = expires_at,
        max_downloads = max_downloads,
        allow_preview = allow_preview,
    )
    link.set_password(password)
    link.save()

    ActivityLog.objects.create(
        user        = request.user,
        action      = 'link_generate',
        file        = vault_file,
        description = f'Generated secure share link for {vault_file.name}',
        ip_address  = get_client_ip(request),
    )

    return JsonResponse({
        'status'    : 'ok',
        'token'     : link.token,
        'url'       : request.build_absolute_uri(link.public_url()),
        'expires_at': link.expires_at.isoformat() if link.expires_at else None,
        'has_password': link.has_password(),
        'id'        : link.id,
    })


@login_required
@require_POST
def revoke_share_link(request, link_id):
    link          = get_object_or_404(ShareLink, id=link_id, created_by=request.user)
    link.is_active = False
    link.save()
    ActivityLog.objects.create(
        user        = request.user,
        action      = 'link_revoke',
        file        = link.file,
        description = f'Revoked share link for {link.file.name}',
        ip_address  = get_client_ip(request),
    )
    return JsonResponse({'status': 'ok'})


# ──────────────────────────────────────────────────────────────────────────────
# PUBLIC SHARE ACCESS — WITH DECRYPTION ON DOWNLOAD
# ──────────────────────────────────────────────────────────────────────────────
def public_share_view(request, token):
    link              = get_object_or_404(ShareLink, token=token, is_active=True)
    error             = None
    password_required = link.has_password()
    authenticated     = False

    if not link.is_valid():
        return render(request, 'public/share_expired.html', {'link': link})

    session_key = f'share_{token}_auth'
    if request.session.get(session_key):
        authenticated = True

    if request.method == 'POST':

        # Download button pressed
        if 'download' in request.POST and authenticated:
            if not link.is_valid():
                return render(request, 'public/share_expired.html', {'link': link})

            link.download_count += 1
            link.save()

            try:
                # ── READ encrypted & DECRYPT ──
                encrypted_data = link.file.file.read()
                fernet         = get_fernet()
                decrypted_data = fernet.decrypt(encrypted_data)

                response = HttpResponse(decrypted_data, content_type='application/octet-stream')
                response['Content-Disposition'] = f'attachment; filename="{link.file.name}"'
                response['Content-Length']      = len(decrypted_data)

                ActivityLog.objects.create(
                    user        = link.created_by,
                    action      = 'link_access',
                    file        = link.file,
                    description = f'Public download via share link · {get_client_ip(request)} (decrypted)',
                    ip_address  = get_client_ip(request),
                )
                return response

            except Exception as e:
                error = f'Could not decrypt file: {e}'

        # Password form
        elif 'password' in request.POST and not authenticated:
            pw = request.POST.get('password', '')
            if link.check_password(pw):
                authenticated              = True
                request.session[session_key] = True
                request.session.modified   = True
            else:
                error = 'Incorrect password. Please try again.'

    if not password_required:
        authenticated = True

    return render(request, 'public/share_view.html', {
        'link'             : link,
        'password_required': password_required,
        'authenticated'    : authenticated,
        'error'            : error,
    })


# ──────────────────────────────────────────────────────────────────────────────
# ACCESS CONTROL
# ──────────────────────────────────────────────────────────────────────────────
@login_required
def access_view(request):
    files = VaultFile.objects.filter(owner=request.user, is_deleted=False).order_by('name')
    access_rules = FileAccess.objects.filter(
        file__owner=request.user
    ).select_related('file', 'shared_with').order_by('-granted_at')

    selected_file_id = request.GET.get('file')
    selected_file    = None
    file_rules       = []
    if selected_file_id:
        try:
            selected_file = files.get(id=selected_file_id)
            file_rules    = FileAccess.objects.filter(file=selected_file).order_by('-granted_at')
        except VaultFile.DoesNotExist:
            pass

    form = FileAccessForm()

    return render(request, 'vault/access.html', {
        'active_view' : 'access',
        'files'       : files,
        'access_rules': access_rules,
        'selected_file': selected_file,
        'file_rules'  : file_rules,
        'form'        : form,
    })


@login_required
@require_POST
def grant_access(request):
    data        = json.loads(request.body)
    file_id     = data.get('file_id')
    email       = data.get('email', '').strip().lower()
    permission  = data.get('permission', 'view')
    expires_at_str = data.get('expires_at', '')

    if not email:
        return JsonResponse({'status': 'error', 'message': 'Email is required'}, status=400)

    vault_file = get_object_or_404(VaultFile, id=file_id, owner=request.user, is_deleted=False)

    expires_at = None
    if expires_at_str:
        from django.utils.dateparse import parse_datetime
        expires_at = parse_datetime(expires_at_str)

    rule, created = FileAccess.objects.get_or_create(
        file=vault_file,
        shared_with_email=email,
        defaults={
            'permission': permission,
            'granted_by': request.user,
            'expires_at': expires_at,
            'status'    : 'active',
        }
    )
    if not created:
        rule.permission = permission
        rule.status     = 'active'
        rule.expires_at = expires_at
        rule.save()

    try:
        shared_user      = User.objects.get(email=email)
        rule.shared_with = shared_user
        rule.save()
    except User.DoesNotExist:
        pass

    ActivityLog.objects.create(
        user        = request.user,
        action      = 'access_grant',
        file        = vault_file,
        description = f'Granted {permission} access to {email} for {vault_file.name}',
        ip_address  = get_client_ip(request),
    )

    _send_access_grant_email(
        granted_by    = request.user,
        recipient_email = email,
        vault_file    = vault_file,
        permission    = permission,
        expires_at    = expires_at,
        request       = request,
    )

    return JsonResponse({
        'status'    : 'ok',
        'id'        : rule.id,
        'email'     : email,
        'permission': permission,
        'message'   : f'Access granted to {email}'
    })


@login_required
@require_POST
def revoke_access(request, rule_id):
    rule  = get_object_or_404(FileAccess, id=rule_id, file__owner=request.user)
    email = rule.shared_with_email
    fname = rule.file.name
    rule.status = 'revoked'
    rule.save()
    ActivityLog.objects.create(
        user        = request.user,
        action      = 'access_revoke',
        file        = rule.file,
        description = f'Revoked access for {email} on {fname}',
        ip_address  = get_client_ip(request),
    )
    return JsonResponse({'status': 'ok', 'message': f'Access revoked for {email}'})


# ──────────────────────────────────────────────────────────────────────────────
# ACTIVITY LOGS
# ──────────────────────────────────────────────────────────────────────────────
@login_required
def logs_view(request):
    qs = ActivityLog.objects.filter(user=request.user).select_related('file')

    action_filter = request.GET.get('action', '')
    if action_filter:
        qs = qs.filter(action=action_filter)

    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(Q(description__icontains=q) | Q(file__name__icontains=q))

    paginator = Paginator(qs, 25)
    page      = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'vault/logs.html', {
        'active_view'   : 'logs',
        'logs'          : page,
        'action_choices': ActivityLog.ACTION_CHOICES,
        'action_filter' : action_filter,
        'search_query'  : q,
    })


# ──────────────────────────────────────────────────────────────────────────────
# SETTINGS
# ──────────────────────────────────────────────────────────────────────────────
@login_required
def settings_view(request):
    from accounts.forms import ProfileUpdateForm, ChangePasswordForm
    profile_form  = ProfileUpdateForm(instance=request.user)
    password_form = ChangePasswordForm(request.user)
    return render(request, 'vault/settings.html', {
        'active_view' : 'settings',
        'profile_form': profile_form,
        'password_form': password_form,
    })


# ──────────────────────────────────────────────────────────────────────────────
# ADMIN PANEL
# ──────────────────────────────────────────────────────────────────────────────
@login_required
def admin_panel_view(request):
    if not (request.user.is_staff or request.user.profile.is_admin):
        messages.error(request, 'Access denied. Admin only.')
        return redirect('dashboard')

    users = User.objects.select_related('profile').order_by('-date_joined')
    q     = request.GET.get('q', '').strip()
    if q:
        users = users.filter(
            Q(email__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q)
        )

    paginator  = Paginator(users, 20)
    users_page = paginator.get_page(request.GET.get('page', 1))

    total_users   = User.objects.count()
    total_files   = VaultFile.objects.filter(is_deleted=False).count()
    total_storage = sum(u.profile.storage_used for u in User.objects.select_related('profile').all())
    total_links   = ShareLink.objects.filter(is_active=True).count()

    return render(request, 'vault/admin_panel.html', {
        'active_view'  : 'admin',
        'users'        : users_page,
        'search_query' : q,
        'total_users'  : total_users,
        'total_files'  : total_files,
        'total_storage': format_file_size(total_storage),
        'total_links'  : total_links,
    })


@login_required
@require_POST
def admin_toggle_user(request, user_id):
    if not (request.user.is_staff or request.user.profile.is_admin):
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)
    target = get_object_or_404(User, id=user_id)
    if target == request.user:
        return JsonResponse({'status': 'error', 'message': 'Cannot suspend yourself'}, status=400)
    profile            = target.profile
    profile.is_suspended = not profile.is_suspended
    profile.save()
    return JsonResponse({
        'status'   : 'ok',
        'suspended': profile.is_suspended,
        'message'  : f'User {"suspended" if profile.is_suspended else "reactivated"}'
    })


@login_required
@require_POST
def admin_delete_user(request, user_id):
    if not (request.user.is_staff or request.user.profile.is_admin):
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)
    target = get_object_or_404(User, id=user_id)
    if target == request.user:
        return JsonResponse({'status': 'error', 'message': 'Cannot delete yourself'}, status=400)
    email = target.email
    target.delete()
    return JsonResponse({'status': 'ok', 'message': f'User {email} deleted'})


# ──────────────────────────────────────────────────────────────────────────────
# API: FILES LIST (JSON)
# ──────────────────────────────────────────────────────────────────────────────
@login_required
def api_files_list(request):
    files = VaultFile.objects.filter(owner=request.user, is_deleted=False).order_by('-uploaded_at')
    data  = [{
        'id'             : f.id,
        'name'           : f.name,
        'size'           : f.size_display(),
        'type'           : f.file_type,
        'icon'           : f.type_icon_class(),
        'uploaded_at'    : f.uploaded_at.isoformat(),
        'encryption_algo': f.encryption_algo,
    } for f in files]
    return JsonResponse({'files': data})


# ──────────────────────────────────────────────────────────────────────────────
# API: STORAGE INFO
# ──────────────────────────────────────────────────────────────────────────────
@login_required
def api_storage_info(request):
    profile = request.user.profile
    return JsonResponse({
        'used'        : profile.storage_used,
        'used_display': format_file_size(profile.storage_used),
        'quota'       : profile.storage_quota,
        'quota_display': format_file_size(profile.storage_quota),
        'percent'     : profile.storage_percent(),
    })