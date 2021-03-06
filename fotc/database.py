# -*- coding: utf8 -*-

import os
import logging
from typing import Text

import sqlalchemy as sqla
from sqlalchemy import Column, Integer, BigInteger, String, TIMESTAMP, MetaData, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

log = logging.getLogger("fotc")

Base = declarative_base(metadata=MetaData(schema='fotc'))


class ChatUser(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    last_active = Column(TIMESTAMP, nullable=True)
    timezone = Column(String, nullable=True)


class ChatGroup(Base):
    __tablename__ = "groups"
    id = Column(Integer, primary_key=True)


class GroupUser(Base):
    __tablename__ = "group_users"
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey(ChatUser.id), nullable=False)
    group_id = Column(BigInteger, ForeignKey(ChatGroup.id), nullable=False)

    user = relationship(ChatUser)
    group = relationship(ChatGroup)


class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True)
    group_user_id = Column(Integer, ForeignKey(GroupUser.id))
    message_ref = Column(String, nullable=True)
    scheduled_for = Column(TIMESTAMP, nullable=False)
    sent_on = Column(TIMESTAMP, nullable=True)

    group_user = relationship(GroupUser)


class ChatGroupUserQuote(Base):
    __tablename__ = "group_user_quotes"

    id = Column(Integer, primary_key=True)
    group_user_id = Column(Integer, ForeignKey(GroupUser.id))
    message_ref = Column(String, nullable=True, unique=True)
    last_sent_on = Column(TIMESTAMP, nullable=True)

    group_user = relationship(GroupUser)

def _get_env_default(name: Text, default_val: Text):
    val = os.environ.get(name)
    if val is None:
        log.warning("Variable %s undefined, fall-backing to default value", name)
        return default_val
    return val


def get_default_engine() -> sqla.engine.Engine:
    """
    Creates a database engine object from environment variables

    Environment variables:
        DATABASE_HOST: server hostname
        DATABASE_NAME: name of the database
        DATABASE_USER, DATABASE_PASS: credentials
    """
    host = _get_env_default("DATABASE_HOST", "postgres")
    name = _get_env_default("DATABASE_NAME", "fotc")
    user = _get_env_default("DATABASE_USER", "fotc")
    password = _get_env_default("DATABASE_PASS", "devdevdev")
    conn_str = f"postgresql://{user}:{password}@{host}/{name}"
    return sqla.create_engine(conn_str)


class LazySessionMaker(object):
    """
    Wrapper to initialize a sessionmaker only in the first time an object of this type is called.
    The engine/bind function is also evaluated when creating the sessionmaker object.
    """
    def __init__(self, lazy_bind):
        self.lazy_bind = lazy_bind
        self.session_maker = None

    def __call__(self, **kwargs):
        if self.session_maker == None:
            self.session_maker = sessionmaker(bind=self.lazy_bind())
        return self.session_maker(**kwargs)


Session = LazySessionMaker(lazy_bind=get_default_engine)
