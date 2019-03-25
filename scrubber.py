# coding=utf-8
import requests
import ujson
from re import sub
import bleach


# Возвращает ответ от сервера в словаре
def request(url, params):
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return False, ujson.loads(response.content)
    else:
        return True, None


# Удаляет все html тэги, кроме тех что поддерживаются тележкой
def cleaner(text):
    valid_tags = ['a']
    attr = {'a': ['href']}
    proto = ['http', 'https', 'tg']
    text = sub(r'&nbsp;', ' ', text)
    text = bleach.clean(text=text, tags=valid_tags, attributes=attr, protocols=proto, strip=True)
    return text


def image_text_cleaner(text):
    valid_tags = ['']
    attr = {'': ''}
    return bleach.clean(text=text, tags=valid_tags, attributes=attr, strip=True)


# Производит сбор данных о подсайтах одним махом
class DomainScrubber:
    def __init__(self):
        self.url = 'https://d3.ru/api/domains'
        self.params = {'page': 1, 'per_page': 42}
        self.num_of_pages = int()
        self.num_of_items = int()
        self.parsed = []
        error, pre = request(self.url, self.params)
        self.get_page_item(pre)
        self.data = self.parse_pages(pre)

    # Итерируется по страницам
    def parse_pages(self, pre):
        self.parse_domains(pre['domains'], 0)
        itemnumber = 42
        for i in range(2, self.num_of_pages + 1):
            error, response = request(self.url, {'page': i, 'per_page': 42})
            self.parse_domains(response['domains'], itemnumber)
            itemnumber += 42
        return self.parsed

    # Итерируется по доментам на страниуе
    def parse_domains(self, domains, itemnumber):
        for domain in domains:
            if itemnumber <= self.num_of_items - 1:
                self.parsed.append(self.domain(domain))
                itemnumber += 1

    # Извлекает значения количества страниц и элементов
    def get_page_item(self, response):
        self.num_of_pages = response['page_count']
        self.num_of_items = response['item_count']

    # Парсит каждый отдельный домен по шаблону
    @staticmethod
    def domain(r):
        domain_main = {
            'id': f'''{r['id']}''',
            'prefix': f'''{r['prefix']}''',
            'name': f'''{r['name']}''',
            'title': f'''{r['title']}''',
            'description': f'''{r['description']}'''}
        return domain_main


# Класс принимает называние подсайта и производит сбор данных
class PostScrubber:
    # При создании экземпляра проводит все необходимые операции и выплевывыет
    # готовый объект типа dict с указанием ти
    def __init__(self, dname):
        self.dname = dname
        self.params = {'page': 1, 'per_page': 10, 'sotring': 'date_created'}
        self.url = f'https://d3.ru/api/domains/{self.dname}/posts'
        error, response = request(self.url, self.params)
        self.data = self.parse(response['posts'])

    # Возвращает объект типа dict с распарсеными по шаблону постами
    def parse(self, posts):
        parsed = []
        for post in posts:
            parsed.append(self.post(post))
        return parsed

    # Возвращает объект типа list с типом поста, основными и доп данными
    def post(self, r):
        post_type = {}
        post_main = {
            'id': f'''{r['id']}''',
            'timestamp': f'''{r['created']}''',
            'domain_prefix': self.dname,
            'author': f'''{r['user']['login']}''',
            'title': f'''{r['data']['title']}''',
            'type': f'''{r['data']['type']}'''}

        actions = {
            'article': self.post_article,
            'link': self.post_link,
            'gallery': self.post_gallery,
            'stream': self.post_stream}
        post_additional = actions[r['data']['type']](r)

        return [post_type, post_main, post_additional]

    # Возвращает дополнительные значения для поста-статьи
    @staticmethod
    def post_article(r):
        try:
            post_additional = {
                'post_id': f'''{r['id']}''',
                'subtitle': f'''{r['data']['subtitle']}''',
                'main_image': f'''{r['data']['preview_image']['thumbnails']['original']['url']}'''}
        except KeyError:
            # Messager(['cyberpunk', 'guns'])
            post_additional = {
                'post_id': f'''{r['id']}''',
                'subtitle': f'''{r['data']['subtitle']}'''}
        return post_additional

    @staticmethod
    # Возвращает дополнительные значения для поста-ссылки
    def post_link(r):
        # Проверяет наличие данных в полях link и media поста-ссылки
        def post_link_media(payload):
            if not None:
                return payload
            else:
                payload['type'] = None
                return payload
        post_additional = {
            'post_id': f'''{r['id']}''',
            'body': cleaner(r['data']['text']),
            'link': post_link_media(r['data']['link']),
            'media': post_link_media(r['data']['media'])}
        return post_additional

    # Возвращает дополнительные значения для поста-галереи
    @staticmethod
    def post_gallery(r):
        urls = []
        for i, image in enumerate(r['data']['gallery']):
            image_and_text = [
                image['url'],
                image_text_cleaner(image['text'] if len(image['text']) > 0 else r['data']['title'])]
            urls.append(image_and_text)

        post_additional = {
            'post_id': f'''{r['id']}''',
            'subtitle': f'''{r['data']['subtitle']}''',
            'urls': urls}
        return post_additional

    # Возвращает дополнительные значения для поста-трансляции
    @staticmethod
    def post_stream(r):
        post_additional = {
            'post_id': f'''{r['id']}''',
            'body': cleaner(r['data']['text'])}
        return post_additional
#some
