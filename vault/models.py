import secrets
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


def get_file_upload_path(instance, filename):
    return f'vault/{instance.owner.id}/{filename}'


class VaultFile(models.Model):
    FILE_TYPE_CHOICES = [
        ('pdf', 'PDF'),
        ('img', 'Image'),
        ('doc', 'Document'),
        ('zip', 'Archive'),
        ('vid', 'Video'),
        ('other', 'Other'),
    ]

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vault_files')
    name = models.CharField(max_length=255)                     # display name (can be renamed)
    original_name = models.CharField(max_length=255)            # original filename
    file = models.FileField(upload_to=get_file_upload_path)
    file_type = models.CharField(max_length=10, choices=FILE_TYPE_CHOICES, default='other')
    size = models.BigIntegerField(default=0)                    # bytes
    mime_type = models.CharField(max_length=120, blank=True)
    is_encrypted = models.BooleanField(default=True)
    encryption_algo = models.CharField(max_length=20, default='AES-256')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-uploaded_at']

    def size_display(self):
        size = self.size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}" if unit != 'B' else f"{size} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def type_icon_class(self):
        return {
            'pdf': 'fa-file-pdf',
            'img': 'fa-file-image',
            'doc': 'fa-file-word',
            'zip': 'fa-file-zipper',
            'vid': 'fa-file-video',
        }.get(self.file_type, 'fa-file')

    def type_badge_color(self):
        return {
            'pdf': 'danger',
            'img': 'cyan',
            'doc': 'blue',
            'zip': 'amber',
            'vid': 'purple',
            'other': 'muted',
        }.get(self.file_type, 'muted')

    def __str__(self):
        return f"{self.name} ({self.owner.email})"

    def soft_delete(self):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()
        # Free up storage
        self.owner.profile.storage_used = max(0, self.owner.profile.storage_used - self.size)
        self.owner.profile.save()


class ShareLink(models.Model):
    file = models.ForeignKey(VaultFile, on_delete=models.CASCADE, related_name='share_links')
    token = models.CharField(max_length=64, unique=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_links')
    expires_at = models.DateTimeField(null=True, blank=True)
    password_hash = models.CharField(max_length=255, blank=True)   # hashed password
    max_downloads = models.IntegerField(default=0)                  # 0 = unlimited
    download_count = models.IntegerField(default=0)
    allow_preview = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    @classmethod
    def generate_token(cls):
        chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789'
        return ''.join(secrets.choice(chars) for _ in range(32))

    def is_valid(self):
        if not self.is_active:
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        if self.max_downloads > 0 and self.download_count >= self.max_downloads:
            return False
        return True

    def has_password(self):
        return bool(self.password_hash)

    def check_password(self, raw_password):
        from django.contrib.auth.hashers import check_password
        return check_password(raw_password, self.password_hash)

    def set_password(self, raw_password):
        from django.contrib.auth.hashers import make_password
        self.password_hash = make_password(raw_password) if raw_password else ''

    def public_url(self):
        return f"/s/{self.token}/"

    def __str__(self):
        return f"Share: {self.file.name} → {self.token[:8]}..."


class FileAccess(models.Model):
    PERMISSION_CHOICES = [
        ('view', 'View Only'),
        ('download', 'Download'),
        ('manage', 'Manage'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('revoked', 'Revoked'),
    ]

    file = models.ForeignKey(VaultFile, on_delete=models.CASCADE, related_name='access_rules')
    shared_with_email = models.EmailField()
    shared_with = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='file_access'
    )
    permission = models.CharField(max_length=20, choices=PERMISSION_CHOICES, default='view')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    granted_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='granted_access')
    granted_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    last_accessed = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-granted_at']
        unique_together = ['file', 'shared_with_email']

    def is_expired(self):
        return self.expires_at and timezone.now() > self.expires_at

    def __str__(self):
        return f"{self.shared_with_email} → {self.file.name} ({self.permission})"


class ActivityLog(models.Model):
    ACTION_CHOICES = [
        ('upload', 'Upload'),
        ('download', 'Download'),
        ('share', 'Share'),
        ('delete', 'Delete'),
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('view', 'View'),
        ('rename', 'Rename'),
        ('access_grant', 'Access Grant'),
        ('access_revoke', 'Access Revoke'),
        ('settings_update', 'Settings Update'),
        ('link_generate', 'Link Generate'),
        ('link_revoke', 'Link Revoke'),
        ('link_access', 'Link Access'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activity_logs')
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    file = models.ForeignKey(
        VaultFile, on_delete=models.SET_NULL, null=True, blank=True, related_name='logs'
    )
    description = models.CharField(max_length=500)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def action_icon(self):
        return {
            'upload': ('fa-cloud-arrow-up', 'blue'),
            'download': ('fa-cloud-arrow-down', 'cyan'),
            'share': ('fa-share-nodes', 'purple'),
            'delete': ('fa-trash', 'danger'),
            'login': ('fa-right-to-bracket', 'green'),
            'logout': ('fa-right-from-bracket', 'muted'),
            'view': ('fa-eye', 'muted'),
            'rename': ('fa-pencil', 'amber'),
            'access_grant': ('fa-user-plus', 'green'),
            'access_revoke': ('fa-user-minus', 'danger'),
            'settings_update': ('fa-gear', 'amber'),
            'link_generate': ('fa-link', 'blue'),
            'link_revoke': ('fa-link-slash', 'danger'),
            'link_access': ('fa-unlock', 'cyan'),
        }.get(self.action, ('fa-circle-info', 'muted'))

    def time_ago(self):
        delta = timezone.now() - self.created_at
        seconds = int(delta.total_seconds())
        if seconds < 60:
            return f"{seconds}s ago"
        elif seconds < 3600:
            return f"{seconds // 60}m ago"
        elif seconds < 86400:
            return f"{seconds // 3600}h ago"
        elif seconds < 604800:
            return f"{seconds // 86400}d ago"
        return self.created_at.strftime('%b %d, %Y')

    def __str__(self):
        return f"{self.user.email} — {self.action} — {self.created_at.strftime('%Y-%m-%d %H:%M')}"
