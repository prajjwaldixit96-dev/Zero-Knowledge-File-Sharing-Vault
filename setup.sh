#!/bin/bash
# ZK Vault — Quick Setup Script
set -e

echo "⚡ ZK Vault — Django Setup"
echo "================================="

# Create virtual environment
if [ ! -d "venv" ]; then
  echo "→ Creating virtual environment..."
  python3 -m venv venv
fi

# Activate
source venv/bin/activate

# Install dependencies
echo "→ Installing dependencies..."
pip install -r requirements.txt -q

# Migrate
echo "→ Running database migrations..."
python manage.py migrate

# Collect static files
echo "→ Collecting static files..."
python manage.py collectstatic --noinput -v 0

echo ""
echo "✅ Setup complete!"
echo ""
echo "Demo accounts:"
echo "  Admin:  admin@zkvault.io / Admin@1234"
echo "  User:   demo@zkvault.io  / Demo@1234"
echo ""
echo "Start server with:"
echo "  source venv/bin/activate"
echo "  python manage.py runserver"
echo ""
echo "Open: http://127.0.0.1:8000/"
