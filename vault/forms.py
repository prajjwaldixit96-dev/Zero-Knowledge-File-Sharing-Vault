from django import forms
from .models import VaultFile, ShareLink, FileAccess



class FileRenameForm(forms.ModelForm):
    class Meta:
        model = VaultFile
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input no-icon', 'placeholder': 'Enter new name'})
        }


class ShareLinkForm(forms.Form):
    EXPIRY_CHOICES = [
        ('', 'Never expires'),
        ('1h', '1 Hour'),
        ('24h', '24 Hours'),
        ('7d', '7 Days'),
        ('30d', '30 Days'),
    ]
    DOWNLOAD_CHOICES = [
        (0, 'Unlimited'),
        (1, '1 download'),
        (5, '5 downloads'),
        (10, '10 downloads'),
        (25, '25 downloads'),
    ]

    file_id = forms.IntegerField(widget=forms.HiddenInput())
    expiry = forms.ChoiceField(
        choices=EXPIRY_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'filter-select w-100'})
    )
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-input no-icon', 'placeholder': 'Set a password (optional)'})
    )
    max_downloads = forms.ChoiceField(
        choices=DOWNLOAD_CHOICES,
        widget=forms.Select(attrs={'class': 'filter-select w-100'})
    )
    allow_preview = forms.BooleanField(required=False, initial=True)


class FileAccessForm(forms.ModelForm):
    class Meta:
        model = FileAccess
        fields = ['shared_with_email', 'permission', 'expires_at']
        widgets = {
            'shared_with_email': forms.EmailInput(attrs={
                'class': 'form-input',
                'placeholder': 'colleague@example.com'
            }),
            'permission': forms.Select(attrs={'class': 'filter-select w-100'}),
            'expires_at': forms.DateTimeInput(attrs={
                'class': 'form-input no-icon',
                'type': 'datetime-local'
            }),
        }
