# -*- coding: utf-8 -*-

import telegram
from telegram.ext import CommandHandler
from fotc.database import Session


class DbCommandHandler(CommandHandler):
    """
    A wrapper for CommandHandlers that require database operations

    The functionality from CommandHandler is preserved, but the callback is wrapped and called with
    an extra Session object as its first argument
    """
    def __init__(self, command, callback, filters=None, allow_edited=False, pass_args=False,
                 pass_update_queue=False, pass_job_queue=False, pass_user_data=False,
                 pass_chat_data=False):
        super().__init__(command, self._callback_wrapper, filters, allow_edited, pass_args,
                         pass_update_queue, pass_job_queue, pass_user_data, pass_chat_data)
        self.inner_callback = callback

    def _callback_wrapper(self, bot: telegram.Bot, update: telegram.Update, **kwargs):
        """Begins a database transaction and forwards command arguments to the inner callback"""
        try:
            session = Session()
            self.inner_callback(session, bot, update, **kwargs)
            session.commit()
        except:
            raise
