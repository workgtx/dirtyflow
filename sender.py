from db import *
import asyncio
import keyboards
from aiogram.types import ParseMode
from aiogram.types import MediaGroup
from aiogram.utils.markdown import hbold
from aiogram.utils.markdown import hlink
from aiogram.utils.exceptions import BadRequest
from aiogram.utils.exceptions import InvalidHTTPUrlContent
from aiogram.utils.exceptions import WrongFileIdentifier
from main import bot
from pdb import set_trace


class Prepare:
    def __init__(self, updated_domains):
        self.updated_domains = updated_domains
        self.block = False
        self.domain_users = {}
        self.timers = {}
        self.uniq_users = set()

    # 0 Заполняет domain_users, uniq_users и timers
    async def start(self):
        for domain in self.updated_domains:
            self.domain_users[domain] = await Get().domain_subscribers(domain_prefix=domain)
            for user in self.domain_users[domain]:
                self.uniq_users.add(user)
        for user in self.uniq_users:
            self.timers.update({user: 0})
        await self.iter_updated_domains()

    # 1 уровень - Итерируется по доменам
    async def iter_updated_domains(self):
        for domain in self.updated_domains:
            await self.iter_new_domain_posts(domain=domain)
            last_timestamp, last_id = await Get().last_timestamp_and_id(domain_prefix=domain)
            await Update().last_timestamp(domain_prefix=domain, last_timestamp=last_timestamp, last_id=last_id)

    # 2 уровень - Итерируется по новым постам домена
    async def iter_new_domain_posts(self, domain):
        for post_1, post_2 in Get().domain_new_posts(domain_prefix=domain):
            message_obj = Message()
            await message_obj.generate(post_1=post_1, post_2=post_2)
            await self.sender(
                message_obj=message_obj,
                domain_users=self.domain_users[domain])

    # 3 уровень - Передает в класс рассылающий сообщения по чатам
    @staticmethod
    async def sender(message_obj, domain_users):
        await asyncio.sleep(1)
        try:
            await Send(message_obj=message_obj, domain_users=domain_users).now()
        except Exception as e:
            print(e)


# noinspection PyUnresolvedReferences
class Message:
    def __init__(self):
        self.message = ''
        self.media = ''
        self.type = ''
        self.link = ''
        self.title = ''

    # Генерирует шапку сообщения
    async def generate(self, post_1, post_2):
        self.title = post_1.title
        self.link = f'https://d3.ru/{post_1.id}'
        user_link = f'https://d3.ru/user/{post_1.author}'

        self.message = f'Новый пост на «{hbold(post_1.domain_prefix)}» ' \
            f'от {hlink(post_1.author, user_link)}\n'
        self.message += await self.message_divider()
        return await self.process_to_message(post_1=post_1, post_2=post_2)

    # Добавляет разделитель между шапкой и телом сообщения
    async def message_divider(self):
        divider = ''
        for x in range(int(len(self.message) * 0.11)):
            divider += '&#8886;&#8887;'
        return divider + '\n'

    # Передает сообщение на обработку соответствующему классу
    async def process_to_message(self, post_1, post_2):
        tp = {'link': Link, 'gallery': Gallery, 'article': Article, 'stream': Stream}
        obj = tp[post_1.type](self.message)
        try:
            self.message, self.type, self.media = await obj.start(post_1=post_1, post_2=post_2)
        except Exception as e:
            print(e)


class Link:
    def __init__(self, message):
        self.message = message

    async def start(self, post_1, post_2):
        del post_1
        self.message += post_2.body + ' '
        link = post_2.link
        media = post_2.media

        if link is not None and media is not None:
            return await self.external_both(li=link, m=media)
        if link is not None and media is None:
            return await self.external_link(li=link)
        if link is None and media is not None:
            return await self.external_media(m=media)
        if link is None and media is None:
            return self.message, 'nomedia', ''

    @staticmethod
    async def replace(url):
        return url.replace('.gifv', '.mp4').replace('.webm', '.mp4')

    async def external_both(self, li, m):
        l_message, l_type, l_url = await self.external_link(li)
        m_message, m_type, m_url = await self.external_media(m)

        if l_type != 'animation':
            if m_type == 'animation':
                return m_message, m_type, m_url
            else:
                if l_type == 'video' or l_type == 'vs':
                    return l_message, l_type, l_url
                elif l_type == 'weblink':
                    return m_message, m_type, m_url
                elif l_type == 'embed':
                    return l_message, l_type, l_url
        else:
            return l_message, l_type, l_url

    async def external_link(self, li):
        async def image():
            if li['is_animated'] is True:
                li['url'] = li['video']
                return self.message, 'animation', li['url']
            else:
                pass
                return self.message, 'image', li['url']

        async def embed():
            if li['embed']['is_animated'] is True:
                li['url'] = await self.replace(li['url'])
                if li['url'][-4:] != '.mp4':
                    li['url'] += '.mp4'
                return self.message, 'animation', li['url']
            else:
                return self.message, 'image', li['url']

        if li['type'] == 'image':
            return await image()

        elif li['type'] == 'video':
            li['url'] = await self.replace(li['url'])
            return self.message, 'video', li['url']

        elif li['type'] == 'embed':
            try:
                return await embed()
            except KeyError:
                return self.message, 'embed', [li['url'], li['embed']['provider']]

        elif li['type'] == 'web':
            return self.message, 'weblink', [li['url'], li['info']['title']]

    async def external_media(self, m):
        if m['is_animated'] is False:
            return self.message, 'image', m['url']

        elif m['is_animated'] is True:
            return self.message, 'animation', m['url']


class Gallery:
    def __init__(self, message):
        self.message = message

    async def start(self, post_1, post_2):
        del post_1
        self.message += f'{hbold(post_2.subtitle)}\n'
        return self.message, 'mediagroup', post_2.urls


class Article:
    def __init__(self, message):
        self.message = message

    async def start(self, post_1, post_2):
        del post_1, post_2
        return self.message, 'article', 1


class Stream:
    def __init__(self, message):
        self.message = message

    @staticmethod
    async def start(post_1, post_2):
        del post_1, post_2
        return 1, 'stream', 1


class Send:
    def __init__(self, message_obj, domain_users):
        self.message_obj = message_obj
        self.domain_users = domain_users

    async def now(self):
        send_map = {
            'image': self.image,
            'mediagroup': self.mediagroup,
            'animation': self.animation,
            'video': self.video,
            'embed': self.embed,
            'weblink': self.weblink,
            'article': self.article,
            'stream': self.stream,
            'nomedia': self.nomedia}
        await send_map[self.message_obj.type]()

    async def image(self):
        try:
            for chat_id in self.domain_users:
                print(chat_id, self.message_obj.title, 'type image')
                await bot.send_photo(
                    chat_id=chat_id,
                    photo=self.message_obj.media,
                    caption=self.message_obj.message[0:900] + hlink(
                        '...', self.message_obj.link) if len(
                        self.message_obj.message) > 1024 else self.message_obj.message,
                    parse_mode=ParseMode.HTML,
                    reply_markup=await keyboards.post_keyboard(
                        self.message_obj.title, self.message_obj.link))
        except WrongFileIdentifier:
            try:
                await self.animation()
            except InvalidHTTPUrlContent:
                await self.nomedia()

    async def mediagroup(self):
        sizes = ['', '?w=700', '?w=500', '?w=330', '?w=120']
        for chat_id in self.domain_users:
            print(chat_id, self.message_obj.title, 'type mediagroup')

            async def images(size):
                media = MediaGroup()
                for i, image in enumerate(self.message_obj.media):
                    if i < 10:
                        media.attach_photo(f'{image[0]}{size}', image[1])
                return media

            async def send_main():
                await bot.send_message(
                    chat_id=chat_id, text=self.message_obj.message,
                    parse_mode=ParseMode.HTML,
                    reply_markup=await keyboards.post_keyboard(
                        self.message_obj.title, self.message_obj.link))

            async def send_media(size):
                media = await images(size)
                await bot.send_media_group(
                    chat_id=chat_id, media=media)

            async def send_until_complete():
                try:
                    await send_media(next(sizes_iter))
                except BadRequest:
                    await send_until_complete()

            sizes_iter = iter(sizes)
            await send_until_complete()
            await send_main()

    async def animation(self):
        try:
            for chat_id in self.domain_users:
                print(chat_id, self.message_obj.title, 'type animation')
                await bot.send_animation(
                    chat_id=chat_id,
                    animation=self.message_obj.media,
                    caption=self.message_obj.message[0:900] + hlink(
                        '...', self.message_obj.link) if len(
                        self.message_obj.message) > 1024 else self.message_obj.message,
                    parse_mode=ParseMode.HTML,
                    reply_markup=await keyboards.post_keyboard(
                        self.message_obj.title, self.message_obj.link))
        except InvalidHTTPUrlContent:
            await self.weblink()

    async def video(self):
        try:
            for chat_id in self.domain_users:
                print(chat_id, self.message_obj.title, 'type video')
                await bot.send_video(
                    chat_id=chat_id,
                    video=self.message_obj.media,
                    caption=self.message_obj.message[0:900] + hlink(
                        '...', self.message_obj.link) if len(
                        self.message_obj.message) > 1024 else self.message_obj.message,
                    parse_mode=ParseMode.HTML,
                    reply_markup=await keyboards.post_keyboard(
                        self.message_obj.title, self.message_obj.link))
        except InvalidHTTPUrlContent:
            await self.weblink()

    async def embed(self):
        for chat_id in self.domain_users:
            print(chat_id, self.message_obj.title, 'type embed')
            self.message_obj.message += '\n' + hlink(
                self.message_obj.media[1],
                self.message_obj.media[0])
            await bot.send_message(
                chat_id=chat_id,
                text=self.message_obj.message[0:3900] + hlink(
                    '...', self.message_obj.link) if len(
                    self.message_obj.message) > 4096 else self.message_obj.message,
                parse_mode=ParseMode.HTML,
                reply_markup=await keyboards.post_keyboard(
                    self.message_obj.title, self.message_obj.link))

    async def weblink(self):
        for chat_id in self.domain_users:
            print(chat_id, self.message_obj.title, 'type weblink')
            self.message_obj.message += '\n' + hlink(
                self.message_obj.media[1],
                self.message_obj.media[0])
            await bot.send_message(
                chat_id=chat_id, text=self.message_obj.message[0:3900] + hlink(
                    '...', self.message_obj.link) if len(
                    self.message_obj.message) > 4096 else self.message_obj.message,
                parse_mode=ParseMode.HTML,
                reply_markup=await keyboards.post_keyboard(
                    self.message_obj.title, self.message_obj.link))

    async def article(self):
        for chat_id in self.domain_users:
            print(chat_id, self.message_obj.title, 'type article')
            await bot.send_message(
                chat_id=chat_id, text=self.message_obj.message[0:3900]+hlink(
                    '...', self.message_obj.link) if len(
                    self.message_obj.message) > 4096 else self.message_obj.message,
                parse_mode=ParseMode.HTML,
                reply_markup=await keyboards.post_keyboard(
                    self.message_obj.title, self.message_obj.link))

    async def stream(self):
        for chat_id in self.domain_users:
            print(chat_id, self.message_obj.title, 'type stream')
            await bot.send_message(
                chat_id=chat_id, text=self.message_obj.message[0:3900]+hlink(
                    '...', self.message_obj.link) if len(
                    self.message_obj.message) > 4096 else self.message_obj.message,
                parse_mode=ParseMode.HTML,
                reply_markup=await keyboards.post_keyboard(
                    self.message_obj.title, self.message_obj.link))

    async def nomedia(self):
        for chat_id in self.domain_users:
            print(chat_id, self.message_obj.title, 'type nomedia')
            await bot.send_message(
                chat_id=chat_id, text=self.message_obj.message[0:3900] + hlink(
                    '...', self.message_obj.link) if len(
                    self.message_obj.message) > 4096 else self.message_obj.message,
                parse_mode=ParseMode.HTML,
                reply_markup=await keyboards.post_keyboard(
                    self.message_obj.title, self.message_obj.link))
#some
