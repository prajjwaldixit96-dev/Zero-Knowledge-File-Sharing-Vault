# ZK Vault — Django Backend

A full-featured Django backend for the **ZK Vault** zero-knowledge file sharing application.

---

## 🗂 Project Structure

```
zkvault_django/
├── manage.py
├── requirements.txt
├── README.md
├── db.sqlite3                  ← Created after migrate
├── zkvault/                    ← Django project config
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── accounts/                   ← Authentication app
│   ├── models.py               ← UserProfile, PasswordResetToken
│   ├── views.py                ← Login, Register, Logout, Forgot/Reset password
│   ├── forms.py
│   ├── urls.py
│   └── admin.py
├── vault/                      ← Core vault app
│   ├── models.py               ← VaultFile, ShareLink, FileAccess, ActivityLog
│   ├── views.py                ← All vault views + REST API endpoints
│   ├── forms.py
│   ├── urls.py
│   ├── utils.py
│   └── admin.py
├── templates/
│   ├── base.html               ← Global base (CSS/JS)
│   ├── app_base.html           ← App shell (sidebar + topbar)
│   ├── accounts/               ← Login, Register, Forgot Password
│   ├── vault/                  ← Dashboard, Files, Upload, Share, Access, Logs, Settings, Admin
│   └── public/                 ← Public share view (no login required)
├── static/
│   ├── css/zkvault.css         ← Full design system (50KB)
│   └── js/zkvault.js
└── media/                      ← User-uploaded files
```

---

## ⚡ Quick Start

### 1. Clone / Extract the project
```bash
cd zkvault_django
```

### 2. Create a virtual environment
```bash
python -m venv venv
source venv/bin/activate        # Linux/macOS
venv\Scripts\activate           # Windows
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Run migrations
```bash
python manage.py migrate
```

### 5. Create a superuser
```bash
python manage.py createsuperuser
```

Or use the built-in demo accounts (created if you ran the seed):
| Email | Password | Role |
|-------|----------|------|
| `admin@zkvault.io` | `Admin@1234` | Super Admin |
| `demo@zkvault.io` | `Demo@1234` | Regular User |

### 6. Start the development server
```bash
python manage.py runserver
```

Open **http://127.0.0.1:8000/** in your browser.

---

## 🗺 URL Map

| URL | Page |
|-----|------|
| `/login/` | Login |
| `/register/` | Register |
| `/forgot-password/` | Forgot Password |
| `/dashboard/` | Dashboard |
| `/upload/` | Upload Files |
| `/files/` | My Files |
| `/share/` | Secure Sharing |
| `/access/` | Access Control |
| `/logs/` | Activity Logs |
| `/settings/` | Settings |
| `/admin-panel/` | Admin Panel (staff only) |
| `/s/<token>/` | Public Share Link |
| `/admin/` | Django Admin |

---

## 🔌 REST API Endpoints

All endpoints return JSON and require login (except public share).

| Method | URL | Action |
|--------|-----|--------|
| `POST` | `/upload/` | Upload files (multipart/form-data, field: `files`) |
| `GET` | `/api/files/` | List all files (JSON) |
| `GET` | `/api/storage/` | Get storage quota info |
| `GET` | `/files/<id>/download/` | Download a file |
| `POST` | `/files/<id>/delete/` | Soft-delete a file |
| `POST` | `/files/<id>/rename/` | Rename a file (JSON: `{name}`) |
| `POST` | `/api/share/generate/` | Generate share link (JSON body) |
| `POST` | `/api/share/<id>/revoke/` | Revoke share link |
| `POST` | `/api/access/grant/` | Grant file access (JSON body) |
| `POST` | `/api/access/<id>/revoke/` | Revoke access rule |
| `POST` | `/api/profile/update/` | Update profile |
| `POST` | `/api/password/change/` | Change password |
| `POST` | `/api/security/update/` | Update security settings |
| `POST` | `/api/admin/users/<id>/toggle/` | Toggle user suspension |
| `POST` | `/api/admin/users/<id>/delete/` | Delete user |

---

## 🏗 Models

### `accounts.UserProfile`
- Storage used/quota tracking
- Plan (free / pro / enterprise)
- Theme preference, 2FA toggle, notifications
- Admin & suspension flags

### `vault.VaultFile`
- Owner, name, file type, size, MIME type
- Encryption metadata (AES-256 flag)
- Soft-delete support

### `vault.ShareLink`
- Token-based public share links
- Optional expiry, password protection, download limits
- Download counter

### `vault.FileAccess`
- Per-file access grants (view / download / manage)
- Optional expiry, status tracking

### `vault.ActivityLog`
- Full audit trail: upload, download, share, delete, login, etc.
- IP address, timestamp, linked file

---

## ⚙️ Configuration

Key settings in `zkvault/settings.py`:

```python
# Change before production!
SECRET_KEY = '...'

# Set to False in production
DEBUG = True

# Add your domain
ALLOWED_HOSTS = ['*']

# File upload limit (500 MB)
DATA_UPLOAD_MAX_MEMORY_SIZE = 524288000

# Email (switch to SMTP in production)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
```

---

## 🔒 Production Checklist

- [ ] Set `DEBUG = False`
- [ ] Generate a new `SECRET_KEY`
- [ ] Set `ALLOWED_HOSTS` to your domain
- [ ] Configure SMTP email backend
- [ ] Use PostgreSQL instead of SQLite
- [ ] Set up Nginx + Gunicorn
- [ ] Enable HTTPS and set `SECURE_SSL_REDIRECT = True`
- [ ] Run `python manage.py collectstatic`
- [ ] Consider Celery for async file processing

---

## 📦 Dependencies

```
Django >= 5.0
Pillow >= 10.0  (avatar image handling)
```
