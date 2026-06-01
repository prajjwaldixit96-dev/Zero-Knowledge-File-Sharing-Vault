import os
import mimetypes


def get_file_type(filename, mime_type=''):
    ext = os.path.splitext(filename)[1].lower()
    mime = mime_type.lower()

    if ext in ['.pdf'] or 'pdf' in mime:
        return 'pdf'
    elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp', '.tiff'] or 'image' in mime:
        return 'img'
    elif ext in ['.doc', '.docx', '.txt', '.rtf', '.odt', '.xls', '.xlsx', '.ppt', '.pptx', '.csv'] \
            or 'document' in mime or 'spreadsheet' in mime or 'presentation' in mime:
        return 'doc'
    elif ext in ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz'] \
            or 'zip' in mime or 'archive' in mime or 'compressed' in mime:
        return 'zip'
    elif ext in ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv'] or 'video' in mime:
        return 'vid'
    return 'other'


def get_client_ip(request):
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def format_file_size(size_bytes):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            if unit == 'B':
                return f"{int(size_bytes)} {unit}"
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def get_dashboard_stats(user):
    from vault.models import VaultFile, ShareLink, ActivityLog
    from django.utils import timezone
    from datetime import timedelta

    files = VaultFile.objects.filter(owner=user, is_deleted=False)
    total_files = files.count()
    storage_used = user.profile.storage_used
    shared_files = files.filter(share_links__isnull=False).distinct().count()

    # Weekly upload activity (last 7 days)
    week_ago = timezone.now() - timedelta(days=7)
    weekly_uploads = []
    for i in range(6, -1, -1):
        day = timezone.now() - timedelta(days=i)
        count = files.filter(
            uploaded_at__date=day.date()
        ).count()
        weekly_uploads.append(count)

    # Recent activity
    recent_logs = ActivityLog.objects.filter(user=user).select_related('file')[:5]

    # Recent files (quick access)
    recent_files = files.order_by('-updated_at')[:6]

    return {
        'total_files': total_files,
        'storage_used': format_file_size(storage_used),
        'storage_used_gb': round(storage_used / (1024 ** 3), 2),
        'storage_quota_gb': user.profile.storage_quota_gb(),
        'storage_percent': user.profile.storage_percent(),
        'shared_files': shared_files,
        'weekly_uploads': weekly_uploads,
        'weekly_total': sum(weekly_uploads),
        'recent_logs': recent_logs,
        'recent_files': recent_files,
    }
