import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured
from psycopg import ProgrammingError
from psycopg.conninfo import conninfo_to_dict

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv()
ON_VERCEL = os.getenv('VERCEL') == '1'
DEBUG = os.getenv('DJANGO_DEBUG', 'False' if ON_VERCEL else 'True').lower() == 'true'
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', '')
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured('DJANGO_SECRET_KEY must be configured in production')
    SECRET_KEY = 'development-only-key-not-for-production-change-this-value'
ALLOWED_HOSTS = [x.strip() for x in os.getenv('DJANGO_ALLOWED_HOSTS', '*' if DEBUG else '').split(',') if x.strip()]
VERCEL_HOSTS = [
    os.environ[name] for name in ('VERCEL_URL', 'VERCEL_BRANCH_URL', 'VERCEL_PROJECT_PRODUCTION_URL')
    if ON_VERCEL and os.getenv(name)
]
ALLOWED_HOSTS.extend(VERCEL_HOSTS)
if not DEBUG and not ALLOWED_HOSTS:
    raise ImproperlyConfigured('DJANGO_ALLOWED_HOSTS must be configured in production')
INSTALLED_APPS = [
    'django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes',
    'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles',
    'rest_framework', 'rest_framework_simplejwt.token_blacklist', 'corsheaders',
    'django_filters', 'drf_spectacular', 'apps.accounts', 'apps.catalog',
    'apps.orders', 'apps.marketing', 'apps.core',
]
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware', 'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', 'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware', 'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware', 'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
ROOT_URLCONF = 'config.urls'
TEMPLATES = [{'BACKEND':'django.template.backends.django.DjangoTemplates','DIRS':[], 'APP_DIRS':True,
              'OPTIONS':{'context_processors':['django.template.context_processors.request',
              'django.contrib.auth.context_processors.auth','django.contrib.messages.context_processors.messages']}}]
WSGI_APPLICATION = 'config.wsgi.application'
DATABASES = {'default': {'ENGINE':'django.db.backends.postgresql', 'NAME':os.getenv('POSTGRES_DB','elvaa'),
    'USER':os.getenv('POSTGRES_USER','elvaa'), 'PASSWORD':os.getenv('POSTGRES_PASSWORD',''),
    'HOST':os.getenv('POSTGRES_HOST','db'), 'PORT':os.getenv('POSTGRES_PORT','5432'),
    'CONN_MAX_AGE':0 if ON_VERCEL else 60}}
if sslmode := os.getenv('POSTGRES_SSLMODE'):
    DATABASES['default']['OPTIONS'] = {'sslmode': sslmode}
if os.getenv('USE_SQLITE', 'False').lower() == 'true':
    DATABASES = {'default': {'ENGINE':'django.db.backends.sqlite3', 'NAME':BASE_DIR/'db.sqlite3'}}
elif database_url := os.getenv('DATABASE_URL'):
    try:
        connection = conninfo_to_dict(database_url)
    except ProgrammingError:
        raise ImproperlyConfigured('DATABASE_URL must be a valid PostgreSQL connection string') from None
    if not all(connection.get(key) for key in ('dbname', 'host', 'user')):
        raise ImproperlyConfigured('DATABASE_URL must include a PostgreSQL host, database and user')

    database = DATABASES['default']
    for setting, parameter in (
        ('NAME', 'dbname'), ('USER', 'user'), ('PASSWORD', 'password'),
        ('HOST', 'host'), ('PORT', 'port'),
    ):
        database[setting] = connection.pop(parameter, '')
    database['OPTIONS'] = connection
    if '-pooler.' in database['HOST']:
        database['DISABLE_SERVER_SIDE_CURSORS'] = True
AUTH_USER_MODEL = 'accounts.User'
AUTH_PASSWORD_VALIDATORS = [
    {'NAME':'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME':'django.contrib.auth.password_validation.MinimumLengthValidator','OPTIONS':{'min_length':10}},
    {'NAME':'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME':'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
LANGUAGE_CODE='en-us'; TIME_ZONE='UTC'; USE_I18N=True; USE_TZ=True
STATIC_URL='/static/'; STATIC_ROOT=BASE_DIR/'staticfiles'
MEDIA_URL='/media/'; MEDIA_ROOT=BASE_DIR/'media'
if media_bucket := os.getenv('MEDIA_S3_BUCKET'):
    STORAGES = {
        'default': {
            'BACKEND': 'storages.backends.s3.S3Storage',
            'OPTIONS': {
                'bucket_name': media_bucket,
                'region_name': os.getenv('MEDIA_S3_REGION'),
                'endpoint_url': os.getenv('MEDIA_S3_ENDPOINT_URL') or None,
                'access_key': os.getenv('MEDIA_S3_ACCESS_KEY_ID') or None,
                'secret_key': os.getenv('MEDIA_S3_SECRET_ACCESS_KEY') or None,
                'signature_version': 's3v4',
                'file_overwrite': False,
            },
        },
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    }
DEFAULT_AUTO_FIELD='django.db.models.BigAutoField'
CORS_ALLOWED_ORIGINS=[x.strip() for x in os.getenv('CORS_ALLOWED_ORIGINS','http://localhost:3000').split(',') if x.strip()]
CSRF_TRUSTED_ORIGINS=[x.strip() for x in os.getenv('CSRF_TRUSTED_ORIGINS','http://localhost:3000,https://*.e2b.app' if DEBUG else '').split(',') if x.strip()]
CSRF_TRUSTED_ORIGINS.extend(f'https://{host}' for host in VERCEL_HOSTS)
CORS_ALLOW_CREDENTIALS=True
REDIS_URL=os.getenv('REDIS_URL','')
CACHES={'default': {'BACKEND':'django.core.cache.backends.redis.RedisCache','LOCATION':REDIS_URL}} if REDIS_URL else {'default': {'BACKEND':'django.core.cache.backends.locmem.LocMemCache','LOCATION':'elvaa-dev'}}
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES':['apps.accounts.authentication.VersionedJWTAuthentication'],
    'DEFAULT_PERMISSION_CLASSES':['rest_framework.permissions.IsAuthenticatedOrReadOnly'],
    'DEFAULT_FILTER_BACKENDS':['django_filters.rest_framework.DjangoFilterBackend','rest_framework.filters.SearchFilter','rest_framework.filters.OrderingFilter'],
    'DEFAULT_PAGINATION_CLASS':'rest_framework.pagination.PageNumberPagination', 'PAGE_SIZE':24,
    'DEFAULT_SCHEMA_CLASS':'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_THROTTLE_CLASSES':['rest_framework.throttling.AnonRateThrottle','rest_framework.throttling.UserRateThrottle'],
    'DEFAULT_THROTTLE_RATES':{'anon':'300/hour','user':'2000/hour','auth':'12/min','checkout':'30/min','contact':'6/hour','newsletter':'20/hour'},
}
SIMPLE_JWT={'ACCESS_TOKEN_LIFETIME':timedelta(minutes=15), 'REFRESH_TOKEN_LIFETIME':timedelta(days=7),
    'ROTATE_REFRESH_TOKENS':True, 'BLACKLIST_AFTER_ROTATION':True, 'UPDATE_LAST_LOGIN':True}
JWT_COOKIE_NAME='elvaa_refresh'
JWT_COOKIE_PATH='/api/v1/auth/'
JWT_COOKIE_SECURE=not DEBUG
CSRF_COOKIE_SECURE=not DEBUG
SESSION_COOKIE_SECURE=not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF=True
SECURE_REFERRER_POLICY='same-origin'
if not DEBUG:
    SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO','https')
    SECURE_SSL_REDIRECT=os.getenv('SECURE_SSL_REDIRECT','True').lower() == 'true'
    SECURE_HSTS_SECONDS=int(os.getenv('SECURE_HSTS_SECONDS','31536000'))
    SECURE_HSTS_INCLUDE_SUBDOMAINS=True
    SECURE_HSTS_PRELOAD=False
CELERY_BROKER_URL=os.getenv('CELERY_BROKER_URL','redis://redis:6379/0')
CELERY_RESULT_BACKEND=os.getenv('CELERY_RESULT_BACKEND',CELERY_BROKER_URL)
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP=True
# Run exactly one Celery beat scheduler alongside workers in a deployed environment.
CELERY_BEAT_SCHEDULE={'reconcile-stale-stripe-payments':{'task':'apps.orders.tasks.reconcile_stale_payments','schedule':300.0}}
EMAIL_BACKEND=os.getenv('EMAIL_BACKEND','django.core.mail.backends.console.EmailBackend' if DEBUG else 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST=os.getenv('EMAIL_HOST','localhost'); EMAIL_PORT=int(os.getenv('EMAIL_PORT','25'))
EMAIL_HOST_USER=os.getenv('EMAIL_HOST_USER',''); EMAIL_HOST_PASSWORD=os.getenv('EMAIL_HOST_PASSWORD','')
EMAIL_USE_TLS=os.getenv('EMAIL_USE_TLS','False').lower() == 'true'
EMAIL_TIMEOUT=int(os.getenv('EMAIL_TIMEOUT','10'))
DEFAULT_FROM_EMAIL=os.getenv('DEFAULT_FROM_EMAIL','ELVAA <hello@example.com>')
FRONTEND_URL=os.getenv('FRONTEND_URL','http://localhost:3000').rstrip('/')
SPECTACULAR_SETTINGS={'TITLE':'ELVAA API','DESCRIPTION':'Storefront and administrative API','VERSION':'1.0.0','SERVE_INCLUDE_SCHEMA':False,
    'ENUM_NAME_OVERRIDES':{'OrderStatusEnum':'apps.orders.choices.ORDER_STATUSES','CheckoutCancellationStatusEnum':[('cancelled','cancelled')]}}

# Demo-only, unpaid order creation. Disable in production until a real provider is integrated.
ALLOW_DEMO_CHECKOUT=os.getenv('ALLOW_DEMO_CHECKOUT','False').lower() == 'true'

# Optional Stripe hosted checkout. Never expose these values to the frontend.
STRIPE_SECRET_KEY=os.getenv('STRIPE_SECRET_KEY','')
STRIPE_WEBHOOK_SECRET=os.getenv('STRIPE_WEBHOOK_SECRET','')
STRIPE_ENABLED=bool(STRIPE_SECRET_KEY and STRIPE_WEBHOOK_SECRET)

if STRIPE_ENABLED and not DEBUG and not FRONTEND_URL.startswith('https://'):
    raise ImproperlyConfigured('FRONTEND_URL must use HTTPS for production Stripe checkout')
