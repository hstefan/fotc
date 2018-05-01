#!/usr/bin/env python3.6
# -*- coding: utf-8 -*-

import io
import logging
import re
import os
import signal
import dateparser
from typing import Tuple, Text, List, Optional

import requests
from sqlalchemy.orm.session import Session as DbSession
import telegram
from telegram.error import BadRequest
from telegram.ext import Updater, CommandHandler
from fotc.handlers import DbCommandHandler
from fotc.database import Reminder
from fotc.poller import RemindersPoller

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
    parsed = _parse_command_args(update.message.text)
    if not parsed:
        update.message.reply_text("Unable to interpret requested command")
        return

    args = parsed[1]
    if len(args) not in {2, 3}:
        update.message.reply_text("Invalid argument account. Min 2, max 3.")
        return

    meme = _memegen_str(args[0])
    top_text = _memegen_str(args[1] if len(args) > 1 else None)
    bottom_text = _memegen_str(args[2] if len(args) > 2 else None)
    uri = f"https://memegen.link/{meme}/{top_text}/{bottom_text}.jpg"
    image = requests.get(uri)
    if image.ok:
        update.message.reply_photo(photo=io.BytesIO(image.content), quote=True)
    else:
        update.message.reply_text(f"Failed to create meme, STATUS: {image.status_code}",
                                  quote=True)


def remind_me_handler(db_session: DbSession, _bot: telegram.Bot, update: telegram.Update):
    parsed = _parse_command_args(update.message.text)
    if not parsed:
        update.message.reply_text("Unable to interpret requested command")
        return

    args = parsed[1]
    if len(args) != 1:
        update.message.reply_text(f"Exactly one argument must be provided, found {len(args)}")
        return

    message = update.effective_message
    if not message.reply_to_message:
        message.reply_text("Standalone reminders are not supported yet, issue the command in a "
                           "reply to another message")
        return

    when = dateparser.parse(args[0])
    reminder = Reminder(target_chat_id=message.chat_id, when=when,
                        message_reference=message.reply_to_message.message_id)
    db_session.add(reminder)
    message.reply_text(f"Reminder created for {when.isoformat()} (UTC)", quote=True)


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
        "remindme": remind_me_handler
    }
    for k, v in persistent.items():
        updater.dispatcher.add_handler(DbCommandHandler(k, v))


def _parse_command_args(text: Text) -> Optional[Tuple[Text, List[Text]]]:
    """
    Parses command text, returning id and args.

    `/foo bar baz` => (foo, [bar, baz])
    `/foo "bar" "baz"` => (foo, [bar, baz])
    `/foo "a long string" baz` => (foo, [a long string, baz])
    """
    cmd_re = re.compile(r'/(\w*)@?\w*\s*(.*)$')
    arg_re = re.compile(r'([^"]\S*|".+?")\s*')

    if not cmd_re.match(text):
        return None

    cmd = cmd_re.search(text).groups()
    cmd_id = cmd[0].strip('"')
    if len(cmd) == 2:
        args = arg_re.findall(cmd[1])
        return cmd_id, [x.strip('"') for x in args]
    else:
        return cmd_id, []


def _memegen_str(text: Text) -> Text:
    if not text:
        return '_'
    return text.replace(' ', '_')


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