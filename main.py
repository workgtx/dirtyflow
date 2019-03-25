# coding=utf-8
import asyncio
import ssl

from aiohttp import web
import keyboards
from aiogram import Bot
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import Dispatcher
from aiogram.dispatcher.webhook import get_new_configured_app
from aiogram.dispatcher.webhook import SendMessage
from aiogram.types import ChatType
from aiogram.types import ParseMode
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram import types
from aiogram.dispatcher import FSMContext
from config import TOKEN, WEBHOOK_SSL_CERT, WEBHOOK_SSL_PRIV, WEBHOOK_URL, WEBAPP_HOST, WEBAPP_PORT, DELAY
from db import *
from aiogram.types import ReplyKeyboardRemove
import sender as snd


loop = asyncio.get_event_loop()
bot = Bot(TOKEN, loop=loop)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


class UserDialog(StatesGroup):
    adding_subscription = State()
    deleting_subscription = State()


# Функция обновления списка постов, в случае если есть обновления, запускает мессенджер
async def post_update():
    await Del().post_cache_tables()
    domain_list = await Get().traced_domains()
    updated_domains = []
    for domain in domain_list:
        if await Update().domain_new_posts(domain_prefix=domain):
            updated_domains.append(domain)
    sender = snd.Prepare(updated_domains)
    await sender.start()
#    await sender.iterate_domains()


def repeat(coro, l):
    asyncio.ensure_future(coro(), loop=l)
    l.call_later(DELAY, repeat, coro, l)


# Пишет в бд юзера, если его там еще нет
async def db_user_check_and_add(chat, target):
    if not await IsExist().user(chat.id):
        await Set().user(
            chat_id=chat.id,
            chat_type=chat.type,
            firstname=target.first_name,
            lastname=target.last_name,
            username=target.mention)


# Добавляет подписку на подсайт для юзера и обновляет таблицу отслеживаемых
async def db_user_add_subscribtion(chat, domain):
    already_subscribed_message = (
        f'Вы уже подписаны на подсайт {domain}, если вы считаете это ошибкой, свяжитесь с разработчиком')
    subscribe_sucscess_message = (
        f'Подписка на подсайт {domain} успешно оформлена')

    if not await IsExist().user_subscribe(chat_id=chat.id, domain_prefix=domain):
        await Set().subscribe(chat_id=chat.id, domain_prefix=domain)
        await bot.send_message(chat_id=chat.id, text=subscribe_sucscess_message)
    else:
        await bot.send_message(chat_id=chat.id, text=already_subscribed_message)
    if not await IsExist().traced_domain(domain_prefix=domain):
        await Set().tracking(domain_prefix=domain)


# Извлекает необходимую информацию о юезре
async def get_information(message):
    if message.reply_to_message:
        target = message.reply_to_message.from_user
        chat = message.chat
    elif message.forward_from and message.chat.type == ChatType.PRIVATE:
        target = message.forward_from
        chat = message.forward_from or message.chat
    else:
        target = message.from_user
        chat = message.chat
    return chat, target


# Удаляет подписку пользователя на домен
async def delete_relation(chat_id, domain):
    if await IsExist().user_subscribe(chat_id=chat_id, domain_prefix=domain):
        if await Del().subscribe(chat_id=chat_id, domain_prefix=domain):
            if not await IsExist().domain_subscribes(domain_prefix=domain):
                if await Del().tracking(domain_prefix=domain):
                    return True
    else:
        return False


# Отрабатывает выход из этапа удаления подсайта
@dp.message_handler(state=UserDialog.deleting_subscription, commands=['stop', 'cancel'])
async def stop_interaction(message: types.Message, state: FSMContext):
    subscribe_stop = (
        'Удаление подсайтов завершено, выход из диалога удаления')
    await bot.send_message(chat_id=message.chat.id, text=subscribe_stop,
                           reply_markup=ReplyKeyboardRemove())
    await state.finish()


# Отрабатывает этап удаления подсайтов
@dp.message_handler(state=UserDialog.deleting_subscription)
async def process_podsite(message: types.Message, state: FSMContext):
    del state
    unsub_sucscess = f'Подписка на {message.text.lower()} отменена'
    unsub_unsucscess = f'Подписка на {message.text.lower()} не обнаружена, никаких действий не предпринято'
    if await delete_relation(message.chat.id, message.text.lower()):
        return SendMessage(chat_id=message.chat.id,
                           text=unsub_sucscess,
                           reply_markup=await keyboards.unsub_keyboard(message.chat.id))
    else:
        return SendMessage(chat_id=message.chat.id,
                           text=unsub_unsucscess,
                           reply_markup=await keyboards.unsub_keyboard(message.chat.id))


# Отрабатывает выход из этапа добавления подсайта
@dp.message_handler(state=UserDialog.adding_subscription, commands=['stop', 'cancel'])
async def stop_interaction(message: types.Message, state: FSMContext):
    subscribe_stop = (
        'Добавление подсайтов завершено, выход из диалога добавления')
    await bot.send_message(chat_id=message.chat.id, text=subscribe_stop,
                           reply_markup=ReplyKeyboardRemove())
    await state.finish()


# Отрабатывает этап добавления подсайта
@dp.message_handler(state=UserDialog.adding_subscription)
async def process_podsite(message: types.Message, state: FSMContext):
    del state
    domain = message.text.lower()
    subscribe_unsucscess = (
        f'Подсайт {domain} не обнаружен в базе данных, если вы считаете это ошибкой, свяжитесь с разработчиком')
    chat, target = await get_information(message)

    if await IsExist().domain(domain_prefix=domain):
        await db_user_check_and_add(chat, target)
        await db_user_add_subscribtion(chat, domain)
    else:
        await bot.send_message(chat_id=chat.id, text=subscribe_unsucscess)


# Отрабатывает стартовые команды
@dp.message_handler(commands=['start', 'help', 'about'])
async def process_start_command(message: types.Message):
    start_message = (
        'Привет, я транслирующий посты с D3 бот.\n'
        'Вышиваю крестиком, обновляюсь раз в 5 минут\n'
        '\nСписок доступных команд:\n/start и '
        '/help вызывают это сообщение.\n/sub - начать диалог подписки\n''/unsub - начать диалог отписки\n')
    return SendMessage(
        chat_id=message.chat.id, text=start_message, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboards.greet_kb)


# Переводит в режим добавления подсайта
@dp.message_handler(commands=['sub'])
async def process_subsctiption(message: types.Message):
    await UserDialog.adding_subscription.set()
    subscribe_start_message = (
        'Вход в режим оформления подписки. Введите префикс подсайта латиницей без кавычек. Пример: «cyberpunk»'
        'По окончании введите /stop или жамкайте на кнопку ниже')
    return SendMessage(chat_id=message.chat.id, text=subscribe_start_message, reply_markup=keyboards.sub_kb)


@dp.message_handler(commands=['unsub'])
async def process_unsubsctiption(message: types.Message):
    unsub_start_message = (
        'Вот список твоих подписок, введи имя подсайта, или просто жмакай на кнопочку с его именем'
    )
    await UserDialog.deleting_subscription.set()
    return SendMessage(chat_id=message.chat.id, text=unsub_start_message,
                       reply_markup=await keyboards.unsub_keyboard(message.chat.id))


# Выполняется на старте
async def on_startup(application):
    del application
    # Статус вебхука
    webhook = await bot.get_webhook_info()

    # Проверка правильности url
    if webhook.url != WEBHOOK_URL:
        # Удалить вебхук, если url кривой
        if not webhook.url:
            await bot.delete_webhook()

        # Установить новый вебхук
        await bot.set_webhook(WEBHOOK_URL, certificate=open(WEBHOOK_SSL_CERT, 'rb'))

    # Запуск обновления и рассылки сообщений в отдельном потоке


# Выполняется по завершении
async def on_shutdown(application):
    del application
    # Удалить вебхук
    await bot.delete_webhook()

    # Закрыть хранилище в памяти
    await dp.storage.close()
    await dp.storage.wait_closed()


if __name__ == '__main__':

    # Создает объект класса веб-приложениe
    app = get_new_configured_app(dispatcher=dp, path='/' + TOKEN)

    # Задает эвенты на старте и окончании работы бота
    app.on_startup.append(on_startup)
    # Устанавливает SSL
    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
    context.load_cert_chain(WEBHOOK_SSL_CERT, WEBHOOK_SSL_PRIV)

    # Стартует веб-приложение
    loop.call_later(0, repeat, post_update, loop)
    web.run_app(app, host=WEBAPP_HOST, port=WEBAPP_PORT, ssl_context=context)
