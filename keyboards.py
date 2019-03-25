from aiogram.types import ReplyKeyboardMarkup
from aiogram.types import KeyboardButton
from aiogram.types import InlineKeyboardMarkup
from aiogram.types import InlineKeyboardButton
from db import Get

# ------------Приветственная клава-----------------
button_sub = KeyboardButton('/sub')
button_unsub = KeyboardButton('/unsub')


greet_kb = ReplyKeyboardMarkup(
    resize_keyboard=True, one_time_keyboard=True)
greet_kb.add(button_sub, button_unsub)
# -------------------------------------------------

# ------------Клавиатура подписки------------------
button_stop = KeyboardButton('/stop')
sub_kb = ReplyKeyboardMarkup(
    resize_keyboard=True, one_time_keyboard=True)
sub_kb.add(button_stop)
# -------------------------------------------------


# -------------Клавиатура отписки------------------
async def unsub_keyboard(chat_id):
    parent = []
    unsub_kb = ReplyKeyboardMarkup(resize_keyboard=True)
    for k, v in enumerate(await Get().user_subscribes(chat_id=chat_id)):
        parent.append(KeyboardButton(v))
        unsub_kb.add(parent[k])
    stop = (KeyboardButton('/stop'))
    unsub_kb.add(stop)
    return unsub_kb
# -------------------------------------------------


async def post_keyboard(name, link):
    inline_kb = InlineKeyboardMarkup()
    inline_kb.add(InlineKeyboardButton(name, url=link))
    return inline_kb
#some