"""
Django settings for sarakste project.

Generated by 'django-admin startproject' using Django 4.2.7.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.2/ref/settings/
"""

from pathlib import Path
import environ
import os

env = environ.Env()
environ.Env.read_env(overwrite=True)
# Get the IP address of this host
DEBUG = env.bool('debug', default=False)
import socket
hostname = socket.gethostname()
IP = socket.gethostbyname(hostname)
HOSTED = env.bool('HOSTED', default=False)
print('HOSTED:',HOSTED)
RUN_REMOTE = env.bool('RUN_REMOTE', default=False)
print('RUN_REMOTE:',RUN_REMOTE)
REMOTE_IP = env.str('REMOTE_IP')

if HOSTED:
    if RUN_REMOTE == True:
        host_ip = '212.7.207.88'
    else:
        host_ip = IP
    db_name = env.str('MYSQL_PROD_DB_NAME')
    db_user = env.str('MYSQL_PROD_DB_USER')
    db_pwd = env.str('MYSQL_PROD_PWD')
else:
    host_ip = '127.0.0.1'
    db_name = env.str('MYSQL_LOCAL_DB_NAME')
    db_user = env.str('MYSQL_LOCAL_DB_USER')
    db_pwd = env.str('MYSQL_LOCAL_PWD')

print('host_ip:',host_ip)
print('db_name:',db_name)
print('db_user:',db_user)
print('db_pwd:',db_pwd)


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-0fe6tyuu9ztxq(gmo!d6c#86$o_91hfj799nu6cgwy0*gqlnl2'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool('DEBUG', default=False)

ALLOWED_HOSTS = env('ALLOWED_HOSTS', cast=[str])


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'sarakste_app.apps.SaraksteAppConfig',

]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'sarakste.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'sarakste.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': db_name,
        'USER': db_user,
        'PASSWORD': db_pwd,
        'HOST': host_ip,
        'PORT': '3306',
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'"
        }
    }
}



# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/


# Define the directory where static files will be collected during deployment
STATIC_URL = '/sarakste_app/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')  # Adjust the path as needed
STATICFILES_DIRS = [
os.path.join(BASE_DIR, 'sarakste_app', 'static'),
]

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
