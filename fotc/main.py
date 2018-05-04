#!/usr/bin/env python3.6
# -*- coding: utf-8 -*-

import io
import logging
import os
import signal
from typing import Text

import dateparser
import pytz
from pytz.exceptions import UnknownTimeZoneError
import requests
import telegram
from sqlalchemy.orm.session import Session as DbSession
from telegram.error import BadRequest
from telegram.ext import Updater, CommandHandler

from fotc.database import Reminder, UserConfig
from fotc.handlers import DbCommandHandler
from fotc.poller import RemindersPoller
from fotc.util import parse_command_args, memegen_str

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
log = logging.getLogger("fotc")


def greet_handler(_bot: telegram.Bot, update: telegram.Update):
    """
    Sends a hello message back to the user
    """
    update.message.reply_text(f"Hello, {update.message.from_user.first_name}!", quote=True)


def me_handler(_bot: telegram.Bot, update: telegram.Update):
    """
    Replaces "/me" with users first name and deletes command message
    """
    command_split = update.message.text.split(' ')
    if len(command_split) < 2:
        update.message.reply_text("Missing arguments for /me command", quote=True)
        return

    arg = ' '.join(command_split[1:]).strip()
    update.message.reply_markdown(f"**{update.message.from_user.first_name} {arg}**",
                                  quote=False)
    try:
        update.message.delete()
    except BadRequest:
        log.info("Unable to delete message, likely due to permissions or being in a private chat")


def meme_handler(_bot: telegram.Bot, update: telegram.Update):
    """
    Downloads a captioned image from memegen and posts it to the source chat
    """
    parsed = parse_command_args(update.message.text)
    if not parsed:
        update.message.reply_text("Unable to interpret requested command")
        return

    args = parsed[1]
    if len(args) not in {2, 3}:
        update.message.reply_text("Invalid argument account. Min 2, max 3.")
        return

    meme = memegen_str(args[0])
    top_text = memegen_str(args[1] if len(args) > 1 else None)
    bottom_text = memegen_str(args[2] if len(args) > 2 else None)
    uri = f"https://memegen.link/{meme}/{top_text}/{bottom_text}.jpg"
    image = requests.get(uri)
    if image.ok:
        update.message.reply_photo(photo=io.BytesIO(image.content), quote=True)
    else:
        update.message.reply_text(f"Failed to create meme, STATUS: {image.status_code}",
                                  quote=True)


def remind_me_handler(db_session: DbSession, _bot: telegram.Bot, update: telegram.Update):
    parsed = parse_command_args(update.message.text)
    if not parsed:
        update.message.reply_text("Unable to interpret requested command", quote=True)
        return

    args = parsed[1]
    if len(args) != 1:
        update.message.reply_text(f"Exactly one argument must be provided, found {len(args)}",
                                  quote=True)
        return

    message = update.effective_message
    if not message.reply_to_message:
        message.reply_text("Standalone reminders are not supported yet, issue the command in a "
                           "reply to another message", quote=True)
        return

    when = dateparser.parse(args[0])
    if not when:
        message.reply_text("Failed to parse date format", quote=True)
        return

    reminder = Reminder(target_chat_id=message.chat_id, when=when,
                        message_reference=message.reply_to_message.message_id)
    db_session.add(reminder)
    message.reply_text(f"Reminder created for {when.isoformat()} (UTC)", quote=True)


def set_timezone_handler(db_session: DbSession, _bot: telegram.Bot, update: telegram.Update):
    """Associates the specified timezone with the issuer who issued the command"""
    parsed = parse_command_args(update.message.text)
    if not parsed:
        update.message.reply_text("Unable to interpret requested command", quote=True)
        return

    _, args = parsed
    if not args:
        update.message.reply_text("At least one argument is required for this command", quote=True)
        return

    tz_string = ' '.join(args)
    try:
        _ = pytz.timezone(tz_string)
    except UnknownTimeZoneError:
        help_url = "https://en.wikipedia.org/wiki/List_of_tz_database_time_zones#List"
        update.message.reply_text(f"Unable to parse specified timezone, please check: {help_url}",
                                  quote=True)
        return

    user = update.effective_user
    log.info("Updating timezone setting for %s: %s", user.id, tz_string)
    user_config = db_session.query(UserConfig)\
        .filter(UserConfig.telegram_user_id == user.id)\
        .first()

    if not user_config:
        user_config = UserConfig(telegram_user_id=user.id, timezone=tz_string)
        db_session.add(user_config)
    else:
        user_config.timezone = tz_string

    update.message.reply_text(f"Timezone updated to {tz_string}", quote=True)


def _register_command_handlers(updater: Updater):
    """
    Registers all exposed Telegram command handlers
    """
    stateless = {
        "greet": greet_handler,
        "me": me_handler,
        "meme": meme_handler,
    }

    for k, v in stateless.items():
        updater.dispatcher.add_handler(CommandHandler(k, v))

    persistent = {
        "remindme": remind_me_handler,
        "settz": set_timezone_handler
    }
    for k, v in persistent.items():
        updater.dispatcher.add_handler(DbCommandHandler(k, v))


def _send_message_admin(bot: telegram.Bot, text: Text, **kwargs):
    chat_id = os.environ.get("TELEGRAM_ADMIN_CHATID", None)
    if not chat_id:
        log.warning("No admin chatId defined, would send: \"%s\"", text)
    else:
        bot.send_message(chat_id, text, **kwargs)


def _handle_sigterm(bot: telegram.Bot, poller: RemindersPoller, sig, frame):
    if sig in [signal.SIGTERM, signal.SIGINT]:
        sig_msg = f"Shutting down on signal {sig}"
        log.info(sig_msg)
        poller.stop()
        _send_message_admin(bot, sig_msg)
    else:
        log.info("Ignoring received signal %s", sig)


def main():
    token = os.environ["TELEGRAM_API_KEY"]
    updater = Updater(token)
    bot = updater.bot
    poller = RemindersPoller(bot, interval=1)
    updater.user_sig_handler = lambda sig, frame: _handle_sigterm(updater.bot, poller, sig, frame)
    _register_command_handlers(updater)
    _send_message_admin(updater.bot, "Starting up now")
    poller.start()
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()