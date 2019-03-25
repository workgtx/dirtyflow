# coding=utf-8
from aiogram.types import ContentTypes

# Настройки бота
TOKEN = ''
WEBHOOK_HOST = ''
WEBHOOK_PORT = 8443
WEBHOOK_SSL_CERT = ''
WEBHOOK_SSL_PRIV = ''
WEBHOOK_URL = f'https://{WEBHOOK_HOST}:{WEBHOOK_PORT}/{TOKEN}'
WEBAPP_HOST = ''
WEBAPP_PORT = 8443
BAD_CONTENT = ContentTypes.PHOTO & ContentTypes.DOCUMENT & ContentTypes.STICKER & ContentTypes.AUDIO


# Настройки БД
ADDRES = ''
PORT = 5432
USERNAME = ''
PASSWORD = ''
BASENAME = ''

# Таймер автообновления и рассылки
DELAY = 300
#some
