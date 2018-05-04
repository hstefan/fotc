# -*- encoding: utf-8 -*-

import logging
import threading
import telegram
import time
import datetime

from fotc.database import Session, Reminder
from sqlalchemy.orm.session import Session as DbSession

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
                reminders = session.query(Reminder)\
                    .filter(Reminder.sent_on.is_(None))\
                    .filter(Reminder.when < datetime.datetime.now())\
                    .all()

                for reminder in reminders:
                    self._process_reminder(reminder)
                else:
                    session.commit()

                time.sleep(self.interval)
            except Exception: # catch-all to prevent any sort of crash
                log.exception("Exception caught during reminder polling")
                time.sleep(2.0)


    def _process_reminder(self, reminder: Reminder):
        self.bot.send_message(chat_id=reminder.target_chat_id,
                              text="Remember this?",
                              reply_to_message_id=reminder.message_reference,
                              quote=True)
        reminder.sent_on = datetime.datetime.now()