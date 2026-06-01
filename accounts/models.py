from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    PLAN_CHOICES = [
        ('free', 'Free'),
        ('pro', 'Pro'),
        ('enterprise', 'Enterprise'),
    ]
    THEME_CHOICES = [('dark', 'Dark'), ('light', 'Light')]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    storage_used = models.BigIntegerField(default=0)        # bytes
    storage_quota = models.BigIntegerField(default=10737418240)  # 10 GB
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='free')
    theme = models.CharField(max_length=10, choices=THEME_CHOICES, default='dark')
    two_fa_enabled = models.BooleanField(default=False)
    login_notifications = models.BooleanField(default=True)
    share_notifications = models.BooleanField(default=True)
    session_timeout = models.BooleanField(default=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    is_admin = models.BooleanField(default=False)
    is_suspended = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def storage_used_gb(self):
        return round(self.storage_used / (1024 ** 3), 2)

    def storage_quota_gb(self):
        return round(self.storage_quota / (1024 ** 3), 1)

    def storage_percent(self):
        if self.storage_quota == 0:
            return 0
        return round((self.storage_used / self.storage_quota) * 100, 1)

    def __str__(self):
        return f"{self.user.username} — {self.plan}"


class PasswordResetToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    used = models.BooleanField(default=False)

    def is_valid(self):
        from django.utils import timezone
        from datetime import timedelta
        return not self.used and (timezone.now() - self.created_at) < timedelta(hours=1)

    def __str__(self):
        return f"Reset token for {self.user.email}"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()
