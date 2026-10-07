import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'ems-super-secret-key-tesla-powerwall-2026')
DEBUG = os.getenv('DJANGO_DEBUG', 'True') == 'True'
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'daphne',  # ASGI 伺服器整合 (需置於最前)
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # 第三方擴充
    'rest_framework',
    'corsheaders',
    'channels',
    
    # EMS 業務應用模組
    'apps.sites',
    'apps.telemetry',
    'apps.fleet_control',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'ems_core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'ems_core.wsgi.application'
ASGI_APPLICATION = 'ems_core.asgi.application'

# 資料庫設定：支援 Docker TimescaleDB (PostgreSQL) 與本機開發輕量 SQLite 自動相容
USE_POSTGRES = os.getenv('USE_POSTGRES', 'False').lower() in ('true', '1')

if USE_POSTGRES:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DB_NAME', 'ems_db'),
            'USER': os.getenv('DB_USER', 'ems_user'),
            'PASSWORD': os.getenv('DB_PASSWORD', 'ems_password_secure123'),
            'HOST': os.getenv('DB_HOST', '127.0.0.1'),
            'PORT': os.getenv('DB_PORT', '5432'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Django Channels 傳輸層 (Redis 或 記憶體通道)
REDIS_HOST = os.getenv('REDIS_HOST', '127.0.0.1')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
USE_REDIS_CHANNEL = os.getenv('USE_REDIS_CHANNEL', 'False').lower() in ('true', '1')

if USE_REDIS_CHANNEL:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                "hosts": [(REDIS_HOST, REDIS_PORT)],
            },
        },
    }
else:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer'
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'zh-hant'
TIME_ZONE = 'Asia/Taipei'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static'] if (BASE_DIR / 'static').exists() else []

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework 設定
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ]
}

# CORS 跨域設定 (支援獨立前端 SPA 存取)
CORS_ALLOW_ALL_ORIGINS = True

# Tesla Fleet API 官方連線設定
TESLA_FLEET_CONFIG = {
    'CLIENT_ID': os.getenv('TESLA_CLIENT_ID', 'mock_tesla_client_id'),
    'CLIENT_SECRET': os.getenv('TESLA_CLIENT_SECRET', 'mock_tesla_client_secret'),
    'BASE_URL': os.getenv('TESLA_FLEET_BASE_URL', 'https://fleet-api.prd.na.vn.cloud.tesla.com'),
    'TOKEN_URL': 'https://auth.tesla.com/oauth2/v3/token',
    'MOCK_MODE': os.getenv('TESLA_MOCK_MODE', 'True').lower() in ('true', '1'),
}
