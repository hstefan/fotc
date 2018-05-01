# -*- coding: utf8 -*-

import os
import logging
import sqlalchemy as sqla
from sqlalchemy import Column, Integer, String, TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


log = logging.getLogger("fotc")

Base = declarative_base()

def get_default_engine() -> sqla.engine.Engine:
    """
    Creates a database engine object from environment variables

    Environment variables:
        DATABASE_HOST: server hostname
        DATABASE_NAME: name of the database
        DATABASE_USER, DATABASE_PASS: credentials

    If any of the variables is not defined, the function will raise KeyError
    """
    try:
        host = os.environ["DATABASE_HOST"]
        name = os.environ["DATABASE_NAME"]
        user = os.environ["DATABASE_USER"]
        password = os.environ["DATABASE_PASS"]
    except KeyError:
        log.error("Missing one or more database environment variables")
        raise
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
