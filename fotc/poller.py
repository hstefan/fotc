# -*- encoding: utf-8 -*-

import logging
import threading
import telegram
import time
import datetime

from fotc.database import Session, Reminder
from sqlalchemy.orm.session import Session as DbSession

from fotc.repository import ReminderRepository, ChatGroupRepository

log = logging.getLogger("fotc")


class RemindersPoller(object):
    def __init__(self, bot: telegram.Bot, interval: float):
        self.bot = bot
        self.interval = interval
        self.thread = threading.Thread(target=self._poll_loop)
        self.stop_event = threading.Event()

    def start(self):
        if self.thread.is_alive():
            return
        self.stop_event.clear()
        self.thread.start()

    def stop(self):
        if not self.thread.is_alive():
            return
        self.stop_event.set()
        self.thread.join(timeout=10)
        if self.thread.is_alive():
            log.error("Poller thread did not stop after timeout")

    def _poll_loop(self):
        while not self.stop_event.is_set():
            try:
                session: DbSession = Session()
                reminder_repo = ReminderRepository(session)
                group_repo = ChatGroupRepository(session)
                for reminder in reminder_repo.query_due_reminders():
                    self._process_reminder(reminder, group_repo)
                else:
                    session.commit()

                time.sleep(self.interval)
            except Exception: # catch-all to prevent any sort of crash
                log.exception("Exception caught during reminder polling")
                time.sleep(2.0)


    def _process_reminder(self,  reminder: Reminder, group_repo: ChatGroupRepository):
        group_user = group_repo.find_group_user_by_id(reminder.group_user_id)
        user = self.bot.get_chat_member(group_user.group_id, group_user.user_id).user
        user_mention = f"<a href=\"tg://user?id={user.id}\">{user.first_name}</a>"
        self.bot.send_message(chat_id=group_user.group_id,
                              text=f"Remember this, {user_mention}?",
                              reply_to_message_id=reminder.message_ref,
                              parse_mode=telegram.ParseMode.HTML,
                              quote=True)
        reminder.sent_on = datetime.datetime.utcnow()
