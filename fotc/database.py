# -*- coding: utf8 -*-

import os
import logging
from typing import Text

import sqlalchemy as sqla
from sqlalchemy import Column, Integer, String, TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


log = logging.getLogger("fotc")

Base = declarative_base()

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


class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True)
    target_chat_id = Column(String, nullable=False)
    when = Column(TIMESTAMP, nullable=False)
    message_reference = Column(String, nullable=True)
    sent_on = Column(TIMESTAMP, nullable=True)


Session = sessionmaker(bind=get_default_engine())
