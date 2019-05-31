import asyncio
import ssl
import sys

from aiohttp import web

import aiogram
from aiogram import Bot, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import Dispatcher
from aiogram.dispatcher.webhook import get_new_configured_app, SendMessage
from aiogram.types import ChatType, ParseMode, ContentTypes
from aiogram.utils.markdown import hbold, bold, text, link


TOKEN = ''
WEBHOOK_HOST = ''
WEBHOOK_PORT = 8443
WEBHOOK_SSL_CERT = ''
WEBHOOK_SSL_PRIV = ''
WEBHOOK_URL_PATH = '/webhook'
WEBHOOK_URL = f'https://{WEBHOOK_HOST}:{WEBHOOK_PORT}{WEBHOOK_URL_PATH}'
WEBAPP_HOST = ''
WEBAPP_PORT = 8443
BAD_CONTENT = ContentTypes.PHOTO & ContentTypes.DOCUMENT & ContentTypes.STICKER & ContentTypes.AUDIO

loop = asyncio.get_event_loop()
bot = Bot(TOKEN, loop=loop)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

class Subscribe(StatesGroup):
    subdomain = State()

async def cmd_start(message: types.Message):
    return SendMessage(chat_id=message.chat.id, text='Hi from webhook!',
                       reply_to_message_id=message.message_id)

@dp.message_handler(commands=['subscribe'])
async def cmd_subscribe(message: types.Message):
    await Subscribe.podsite.set()
    await message.reply('Введите название подсайта')


async def cmd_about(message: types.Message):
    # In this function markdown utils are userd for formatting message text
    return SendMessage(message.chat.id, text(
        bold('Hi! I\'m just a simple telegram bot.'),
        '',
        text('With', link(text, 'https://github.com/aiogram/aiogram')),
        sep='\n'
    ), parse_mode=ParseMode.MARKDOWN)


async def cancel(message: types.Message):
    # Get current state context
    state = dp.current_state(chat=message.chat.id, user=message.from_user.id)

    # If current user in any state - cancel it.
    if await state.get_state() is not None:
        await state.set_state(state=None)
        return SendMessage(message.chat.id, 'Current action is canceled.')
        # Otherwise do nothing


async def unknown(message: types.Message):
    """
    Handler for unknown messages.
    """
    return SendMessage(message.chat.id, f"I don\'t know what to do with content type `{message.content_type()}`. Sorry :c")


async def cmd_id(message: types.Message):
    """
    Return info about user.
    """
    if message.reply_to_message:
        target = message.reply_to_message.from_user
        chat = message.chat
    elif message.forward_from and message.chat.type == ChatType.PRIVATE:
        target = message.forward_from
        chat = message.forward_from or message.chat
    else:
        target = message.from_user
        chat = message.chat

    result_msg = [hbold('Info about user:'),
                  f"First name: {target.first_name}"]
    if target.last_name:
        result_msg.append(f"Last name: {target.last_name}")
    if target.username:
        result_msg.append(f"Username: {target.mention}")
    result_msg.append(f"User ID: {target.id}")

    result_msg.extend([hbold('Chat:'),
                       f"Type: {chat.type}",
                       f"Chat ID: {chat.id}"])
    if chat.type != ChatType.PRIVATE:
        result_msg.append(f"Title: {chat.title}")
    else:
        result_msg.append(f"Title: {chat.full_name}")
    return SendMessage(message.chat.id, '\n'.join(result_msg), reply_to_message_id=message.message_id,
                       parse_mode=ParseMode.HTML)


async def on_startup(app):
    # Demonstrate one of the available methods for registering handlers
    # This command available only in main state (state=None)
    dp.register_message_handler(cmd_start, commands=['start'])
    dp.register_message_handler(cmd_subscribe, commands=['subscribe'])
    dp.register_message_handler(cmd_unsubscribe, commands=['unsubscribe'])
    dp.register_message_handler(cmd_mysubscriprions, commands=['mysubscriptions'])

    dp.register_message_handler(unknown, content_types=BAD_CONTENT,
                                func=lambda message: message.chat.type == ChatType.PRIVATE)


    # Get current webhook status
    webhook = await bot.get_webhook_info()

    # If URL is bad
    if webhook.url != WEBHOOK_URL:
        # If URL doesnt match current - remove webhook
        if not webhook.url:
            await bot.delete_webhook()

        # Set new URL for webhook
        await bot.set_webhook(WEBHOOK_URL, certificate=open(WEBHOOK_SSL_CERT, 'rb'))
        # If you want to use free certificate signed by LetsEncrypt you need to set only URL without sending certificate.


async def on_shutdown(app):
    # Remove webhook.
    await bot.delete_webhook()

    # Close Redis connection.
    await dp.storage.close()
    await dp.storage.wait_closed()


if __name__ == '__main__':
    # Get instance of :class:`aiohttp.web.Application` with configured router.
    app = get_new_configured_app(dispatcher=dp, path=WEBHOOK_URL_PATH)

    # Setup event handlers.
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    # Generate SSL context
    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
    context.load_cert_chain(WEBHOOK_SSL_CERT, WEBHOOK_SSL_PRIV)

    # Start web-application.
    web.run_app(app, host=WEBAPP_HOST, port=WEBAPP_PORT, ssl_context=context)
