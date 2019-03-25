from db_map import *
from scrubber import DomainScrubber, PostScrubber
from psycopg2 import IntegrityError
from collections import namedtuple

session = start_session()
cachetab = {'link': PostsLinkType,
            'gallery': PostsGalleryType,
            'article': PostsArticleType,
            'stream': PostsStreamType,
            'main': Posts}


# Устанавливает значения в базе данных
class Set:
    @staticmethod
    async def user(chat_id, chat_type, firstname, lastname, username):
        try:
            set_user = Users(
                chat_id=chat_id,
                type=chat_type,
                firstname=firstname,
                lastname=lastname,
                username=username)
            session.add(set_user)
            session.commit()
            return True
        except Exception as e:
            print(e)
            return False

    @staticmethod
    async def subscribe(chat_id, domain_prefix):
        try:
            domain_id = await Get().domain_id(
                domain_prefix=domain_prefix)
            set_subscribe = UsersToDomains(
                chat_id=chat_id,
                domain_id=domain_id,
                domain_prefix=domain_prefix)
            session.add(set_subscribe)
            session.commit()
            return True
        except Exception as e:
            print(e)
            return False

    @staticmethod
    async def tracking(domain_prefix):
        try:
            await Update().domain_new_posts(domain_prefix=domain_prefix)
            last_timestamp, last_id = await Get().last_timestamp_and_id(domain_prefix=domain_prefix)
            set_domain = TracedDomains(
                prefix=domain_prefix,
                last_timestamp=last_timestamp,
                last_id=last_id)
            session.close()
            session.add(set_domain)
            session.commit()
            return True
        except Exception as e:
            print(e)
            return False


# Удаляет знчения в базе данных
class Del:
    @staticmethod
    async def subscribe(chat_id, domain_prefix):
        try:
            session.query(UsersToDomains).\
                filter_by(chat_id=chat_id,
                          domain_prefix=domain_prefix).\
                delete(synchronize_session=False)
            session.commit()
            return True
        except Exception as e:
            print(e)
            return False

    @staticmethod
    async def tracking(domain_prefix):
        try:
            if await IsExist().domain_subscribes(domain_prefix=domain_prefix):
                session.query(TracedDomains).\
                    filter_by(prefix=domain_prefix).\
                    delete(synchronize_session=False)
                session.commit()
            return True
        except Exception as e:
            print(e)
            return False

    @staticmethod
    async def post_cache_tables():
        try:
            for table in cachetab.values():
                session.query(table).delete(synchronize_session=False)
                session.commit()
            return True
        except Exception as e:
            print(e)
            return False


# Получает значения из базы данных
class Get:
    @staticmethod
    async def user_subscribes(chat_id):
        return [subscribe.domain_prefix for subscribe in session.query(UsersToDomains).filter_by(chat_id=chat_id)]

    @staticmethod
    async def last_timestamp_and_id(domain_prefix):
        last = session.query(Posts). \
            filter_by(domain_prefix=domain_prefix). \
            order_by(Posts.timestamp.desc()). \
            first()
        return last.timestamp, last.id

    @staticmethod
    async def domain_subscribers(domain_prefix):
        user_list = []
        for user_domain in session.query(UsersToDomains).\
                filter_by(domain_prefix=domain_prefix):
            user_list.append(user_domain.chat_id)
        return user_list

    @staticmethod
    def domain_new_posts(domain_prefix):
        def additional(pid, post_type):
            for post_additional in session.query(post_type).filter_by(post_id=pid):
                return post_additional

        for post in session.query(Posts).\
                filter_by(domain_prefix=domain_prefix).\
                order_by(Posts.id):
            post2 = additional(post.id, cachetab[post.type])
            yield post, post2

    @staticmethod
    async def domain_id(domain_prefix):
        domain = session.query(Domains).\
            filter_by(prefix=domain_prefix).\
            first()
        return getattr(domain, 'id', None)

    @staticmethod
    async def traced_domains():
        domain_list = []
        for domain in session.query(TracedDomains):
            domain_list.append(domain.prefix)
        return domain_list


# Обновляет значения в бд
class Update:
    @staticmethod
    async def last_timestamp(domain_prefix, last_timestamp, last_id):
        try:
            domain = session.query(TracedDomains).\
                filter_by(prefix=domain_prefix).\
                first()
            domain.last_timestamp = last_timestamp
            if domain.id < last_id:
                domain.last_id = last_id
            session.commit()
            return True
        except Exception as e:
            print(e)
            return False

    @staticmethod
    async def domain_new_posts(domain_prefix):
        has_updates = False

        def additional_data(data, p_type):
            additional = p_type(data)
            session.add(additional)

        # Получает для выбранного подсайта посты с сервера d3
        posts = PostScrubber(domain_prefix).data
        # Получает последний поста для выбранного подсайта
        last = session.query(TracedDomains).\
            filter_by(prefix=domain_prefix).\
            first()
        try:
            last.last_timestamp
        except AttributeError:
            Last = namedtuple('Last', 'last_timestamp')
            last = Last(0)

        # Цикл прохода по постам, запускает функцию main записи в базу если один из id старше последнего
        for post in reversed(posts):
            post_type = post[1]['type']
            post_timestamp = int(post[1]['timestamp'])
            post_main = post[1]
            post_additional = post[2]
            if post_timestamp > last.last_timestamp:
                has_updates = True
                p = Posts(post=post_main)
                session.add(p)
                session.commit()
                additional_data(post_additional, cachetab[post_type])
        # Транзакция в базу
        session.commit()
        return has_updates

    @staticmethod
    async def domains():
        try:
            domains = DomainScrubber().data
            for domain in domains:
                try:
                    newdomain = Domains(domain)
                    session.add(newdomain)
                    session.commit()
                except IntegrityError:
                    session.close()
            return True
        except Exception as e:
            print(e)
            return False


#
class IsExist:
    @staticmethod
    async def user(chat_id):
        user = session.query(Users).\
            filter_by(chat_id=chat_id).\
            first()
        return True if getattr(user, 'chat_id', None) else False

    @staticmethod
    async def user_subscribe(chat_id, domain_prefix):
        subscribe = session.query(UsersToDomains).\
            filter_by(chat_id=chat_id, domain_prefix=domain_prefix).\
            first()
        return True if getattr(subscribe, 'chat_id', None) else False

    @staticmethod
    async def domain_subscribes(domain_prefix):
        subscribe = session.query(UsersToDomains).\
            filter_by(domain_prefix=domain_prefix).\
            first()
        return True if getattr(subscribe, 'chat_id', None) else False

    @staticmethod
    async def domain(domain_prefix):
        domain = session.query(Domains).\
            filter_by(prefix=domain_prefix).\
            first()
        return True if getattr(domain, 'prefix', None) else False

    @staticmethod
    async def traced_domain(domain_prefix):
        domain = session.query(TracedDomains). \
            filter_by(prefix=domain_prefix). \
            first()
        return True if getattr(domain, 'prefix', None) else False
#some
