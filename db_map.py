# coding=utf-8
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import Text
from sqlalchemy import VARCHAR
from sqlalchemy import create_engine
from sqlalchemy import ForeignKey
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.schema import DropTable
from sqlalchemy.ext.compiler import compiles
from config import USERNAME, PASSWORD, ADDRES, PORT, BASENAME

Base = declarative_base()
engine = create_engine(
    f'postgresql+psycopg2://{USERNAME}:{PASSWORD}@{ADDRES}:{PORT}/{BASENAME}', echo=False)


def start_session():
    session = sessionmaker()
    session.configure(bind=engine)
    Base.metadata.create_all(engine)
    return session()


# Переопределяем метод drop() чтобы он поддерживал каскадное удаление
@compiles(DropTable, "postgresql")
def _compile_drop_table(element, compiler):
    return compiler.visit_drop_table(element) + " CASCADE"


class Users(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    chat_id = Column(Integer, index=True, unique=True)
    type = Column(VARCHAR(10))
    firstname = Column(VARCHAR(128))
    lastname = Column(VARCHAR(128))
    username = Column(VARCHAR(256), unique=True, index=True)

    def __init__(self, **user):
        for k, v in user.items():
            setattr(self, k, v)

    def __repr__(self):
        return f"<User(" \
               f"'{self.chat_id}'," \
               f"'{self.type}'," \
               f"'{self.firstname}'," \
               f"'{self.lastname}'," \
               f"'{self.username}')>"


class Domains(Base):
    __tablename__ = 'domains'
    id = Column(Integer)
    prefix = Column(VARCHAR(1024), unique=True, primary_key=True)
    name = Column(Text)
    title = Column(Text)
    description = Column(Text)

    def __init__(self, domain):
        for k, v in domain.items():
            setattr(self, k, v)

    def __repr__(self):
        return f"<Domain(" \
               f"'{self.id}', " \
               f"'{self.prefix}', " \
               f"'{self.name}', " \
               f"'{self.title}', " \
               f"'{self.description}')>"


class UsersToDomains(Base):
    __tablename__ = 'subscribes'
    id = Column(Integer, primary_key=True)
    chat_id = Column(Integer, ForeignKey('users.chat_id'), nullable=False)
    domain_prefix = Column(VARCHAR(1024), ForeignKey('domains.prefix'), index=True)

    def __init__(self, **ud_relation):
        for k, v in ud_relation.items():
            setattr(self, k, v)

    def __repr__(self):
        return "<UserDomain(" \
               f"'{self.chat_id}', " \
               f"'{self.domain_prefix}')>"


class TracedDomains(Base):
    __tablename__ = 'traced_domains'
    id = Column(Integer, primary_key=True)
    prefix = Column(VARCHAR(1024), ForeignKey('domains.prefix'), index=True)
    last_id = Column(Integer)
    last_timestamp = Column(Integer)

    def __init__(self, **domain):
        for k, v in domain.items():
            setattr(self, k, v)

    def __repr__(self):
        return "<TracedDomains(" \
               f"'{self.prefix}'," \
               f"'{self.last_timestamp}'," \
               f"'{self.last_id}')>"


class Posts(Base):
    __tablename__ = 'posts'
    id = Column(Integer, primary_key=True)
    timestamp = Column(Integer, index=True)
    domain_prefix = Column(VARCHAR(1024), ForeignKey('domains.prefix'), index=True)
    author = Column(VARCHAR(256))
    title = Column(Text)
    type = Column(VARCHAR(10))

    def __init__(self, post):
        for k, v in post.items():
            setattr(self, k, v)

    def __repr__(self):
        return "<Posts(" \
               f"'{self.id}'," \
               f"'{self.timestamp}," \
               f"'{self.domain_prefix}', " \
               f"'{self.author}', " \
               f"'{self.title}'," \
               f"'{self.type}')>"


class PostsArticleType(Base):
    __tablename__ = 'post_article'
    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey('posts.id'))
    subtitle = Column(Text)
    main_image = Column(VARCHAR(1024))

    def __init__(self, additional):
        for k, v in additional.items():
            setattr(self, k, v)

    def __repr__(self):
        return "<PostArticle(" \
               f"'{self.post_id}', " \
               f"'{self.subtitle}', " \
               f"'{self.main_image}')>"


class PostsLinkType(Base):
    __tablename__ = 'post_link'
    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey('posts.id'))
    body = Column(Text)
    link = Column(postgresql.JSONB)
    media = Column(postgresql.JSONB)

    def __init__(self, additional):
        for k, v in additional.items():
            setattr(self, k, v)

    def __repr__(self):
        return "<PostLink(" \
               f"'{self.post_id}', " \
               f"'{self.body}', " \
               f"'{self.link}', " \
               f"'{self.media}')>"


class PostsGalleryType(Base):
    __tablename__ = 'post_gallery'
    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey('posts.id'))
    subtitle = Column(Text)
    urls = Column(postgresql.ARRAY(Text, dimensions=2))

    def __init__(self, additional):
        for k, v in additional.items():
            setattr(self, k, v)

    def __repr__(self):
        return "<PostGallery(" \
               f"'{self.post_id}', " \
               f"'{self.subtitle}', " \
               f"'{self.urls}')>"


class PostsStreamType(Base):
    __tablename__ = 'post_stream'
    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey('posts.id'))
    body = Column(Text)

    def __init__(self, additional):
        for k, v in additional.items():
            setattr(self, k, v)

    def __repr__(self):
        return "<PostStream(" \
               f"'{self.post_id}', " \
               f"'{self.body}')>"
#some
