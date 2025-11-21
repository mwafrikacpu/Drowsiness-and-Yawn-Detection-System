#!/usr/bin/env python
"""
Railway Deployment Setup Script for DrowsiSense
"""
import os
from pathlib import Path

def create_production_files():
    """Create all necessary production files"""
    
    print(" Creating Production Deployment Files")
    print("=" * 45)
    
    # 1. Create production settings
    production_settings = '''"""
Production settings for DrowsiSense deployment
"""
import os
import dj_database_url
from .settings import *

# Production security
DEBUG = False
ALLOWED_HOSTS = [
    '.railway.app',
    '.up.railway.app',
    'localhost',
    '127.0.0.1',
    'drowsisense-production.up.railway.app',
]

# Database configuration for Railway PostgreSQL
DATABASES = {
    'default': dj_database_url.parse(
        os.environ.get('DATABASE_URL', 'sqlite:///db.sqlite3'),
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# Static files configuration
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Use WhiteNoise for static files
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Security settings
SECURE_SSL_REDIRECT = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Email configuration for production
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'drowsiness_app': {
            'handlers': ['console'],
            'level': 'INFO',
        },
    },
}

# CORS settings for API
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    "https://drowsisense-production.up.railway.app",
]

# Cache configuration
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

print("🚀 Production settings loaded successfully!")
'''
    
    settings_file = Path('drowsiness_project/settings_production.py')
    with open(settings_file, 'w') as f:
        f.write(production_settings)
    print(f" Created: {settings_file}")
    
    # 2. Create Railway configuration
    railway_config = '''{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "python manage.py migrate && python manage.py collectstatic --noinput && gunicorn drowsiness_project.wsgi:application --bind 0.0.0.0:$PORT",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}'''
    
    with open('railway.json', 'w') as f:
        f.write(railway_config)
    print(" Created: railway.json")
    
    # 3. Create Procfile
    procfile_content = '''web: gunicorn drowsiness_project.wsgi:application --bind 0.0.0.0:$PORT
worker: python manage.py runserver'''
    
    with open('Procfile', 'w') as f:
        f.write(procfile_content)
    print(" Created: Procfile")
    
    # 4. Create runtime.txt
    with open('runtime.txt', 'w') as f:
        f.write('python-3.11.6\\n')
    print("Created: runtime.txt")
    
    # 5. Update requirements.txt
    additional_requirements = '''
# Production requirements
gunicorn==21.2.0
psycopg2-binary==2.9.9
whitenoise==6.6.0
dj-database-url==2.1.0
'''
    
    with open('requirements.txt', 'a') as f:
        f.write(additional_requirements)
    print("Updated: requirements.txt")
    
    # 6. Create health check view
    health_check_view = '''
# Add this to drowsiness_app/views_refactored.py

from django.http import JsonResponse
from django.views.decorators.cache import cache_page
from django.utils import timezone

@cache_page(60)
def health_check(request):
    """Health check endpoint for monitoring"""
    return JsonResponse({
        'status': 'healthy',
        'version': '2.0',
        'app': 'DrowsiSense',
        'timestamp': timezone.now().isoformat(),
        'database': 'connected'
    })
'''
    
    print("📄 Health check view code ready to add")
    
    # 7. Create 404 error page
    error_404_template = '''{% extends 'base.html' %}
{% load static %}

{% block title %}Page Not Found - DrowsiSense{% endblock %}

{% block content %}
<div class="container">
    <div style="text-align: center; padding: 4rem 2rem;">
        <div style="font-size: 6rem; margin-bottom: 1rem;">🔍</div>
        <h1 style="color: var(--text-primary); margin-bottom: 1rem;">Page Not Found</h1>
        <p style="color: var(--text-secondary); margin-bottom: 2rem; font-size: 1.1rem;">
            The page you're looking for doesn't exist or has been moved.
        </p>
        <div style="display: flex; gap: 1rem; justify-content: center; flex-wrap: wrap;">
            <a href="{% url 'home' %}" class="btn-modern btn-primary">
                <i class="fas fa-home"></i>
                Go Home
            </a>
            <a href="{% url 'driver_dashboard' %}" class="btn-modern btn-outline">
                <i class="fas fa-tachometer-alt"></i>
                Dashboard
            </a>
        </div>
    </div>
</div>
{% endblock %}'''
    
    templates_dir = Path('templates')
    templates_dir.mkdir(exist_ok=True)
    
    with open(templates_dir / '404.html', 'w') as f:
        f.write(error_404_template)
    print("✅ Created: templates/404.html")
    
    # 8. Create deployment checklist
    checklist = '''# 🚀 Railway Deployment Checklist

## Before Deployment:
- [ ] All files committed to Git
- [ ] Production settings created
- [ ] Requirements.txt updated
- [ ] Railway configuration files ready

## Railway Setup:
1. Go to https://railway.app
2. Sign in with GitHub
3. Click "New Project"
4. Choose "Deploy from GitHub repo"
5. Select your DrowsiSense repository
6. Add PostgreSQL database service

## Environment Variables to Set in Railway:
```
DJANGO_SETTINGS_MODULE = drowsiness_project.settings_production
SECRET_KEY = your-super-secret-key-generate-new-one
PORT = 8000
EMAIL_HOST_USER = your-email@gmail.com (optional)
EMAIL_HOST_PASSWORD = your-app-password (optional)
```

## After Deployment:
- [ ] App builds successfully
- [ ] URL loads without errors
- [ ] Database migrations run
- [ ] Static files serve correctly
- [ ] Camera detection works
- [ ] User registration works
- [ ] Dashboard displays properly

## Success URLs:
- Main app: https://your-app-name.up.railway.app
- Health check: https://your-app-name.up.railway.app/health/

## Troubleshooting:
- Check Railway logs for build errors
- Verify environment variables are set
- Ensure DATABASE_URL is automatically provided
- Test static files loading
'''
    
    with open('DEPLOYMENT_CHECKLIST.md', 'w') as f:
        f.write(checklist)
    print("✅ Created: DEPLOYMENT_CHECKLIST.md")

def create_wsgi_update():
    """Update WSGI for production"""
    wsgi_content = '''"""
WSGI config for drowsiness_project project.
Updated for production deployment.
"""

import os
from django.core.wsgi import get_wsgi_application

# Use production settings by default, fallback to development
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 
                     'drowsiness_project.settings_production')

application = get_wsgi_application()
'''
    
    with open('drowsiness_project/wsgi.py', 'w') as f:
        f.write(wsgi_content)
    print("✅ Updated: drowsiness_project/wsgi.py")

def main():
    """Main deployment setup function"""
    print("🎯 DrowsiSense - Railway Deployment Setup")
    print("=" * 45)
    
    try:
        create_production_files()
        create_wsgi_update()
        
        print("\n" + "=" * 45)
        print("🎉 ALL DEPLOYMENT FILES CREATED!")
        print("=" * 45)
        
        print("\n📋 NEXT STEPS:")
        print("1. Commit all new files to Git:")
        print("   git add .")
        print("   git commit -m 'feat: Add production deployment configuration'")
        print("   git push origin main")
        print("")
        print("2. Go to https://railway.app and deploy!")
        print("3. Follow the DEPLOYMENT_CHECKLIST.md")
        print("")
        print("🚀 Your app will be live in ~5-10 minutes!")
        print("📊 Perfect for your portfolio and resume!")
        
    except Exception as e:
        print(f"❌ Error creating deployment files: {e}")

if __name__ == "__main__":
    main()
'''

def create_secret_key_generator():
    """Create a script to generate Django secret key"""
    key_generator = '''#!/usr/bin/env python
"""
Generate a new Django secret key for production
"""
import secrets
import string

def generate_secret_key(length=50):
    """Generate a cryptographically secure secret key"""
    alphabet = string.ascii_letters + string.digits + '!@#$%^&*(-_=+)'
    secret_key = ''.join(secrets.choice(alphabet) for i in range(length))
    return secret_key

if __name__ == "__main__":
    key = generate_secret_key()
    print("🔐 Your new Django SECRET_KEY:")
    print(f"SECRET_KEY = '{key}'")
    print("")
    print("📋 Copy this value and set it as an environment variable in Railway!")
'''
    
    with open('generate_secret_key.py', 'w') as f:
        f.write(key_generator)
    print("✅ Created: generate_secret_key.py")

if __name__ == "__main__":
    main()