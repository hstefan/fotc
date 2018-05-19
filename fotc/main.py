#!/usr/bin/env python3.6
# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
import io
import logging
import os
import random
import signal
from sqlalchemy.exc import IntegrityError
from typing import Text

import dateparser
import pytz
from pytz.exceptions import UnknownTimeZoneError
import requests
import telegram
from sqlalchemy.orm.session import Session as DbSession
from telegram.error import BadRequest
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

from fotc.database import Session as SessionMaker
from fotc.database import Reminder, ChatUser, GroupUser
from fotc.repository import ChatUserRepository, ChatGroupRepository, ReminderRepository, \
    QuoteRepository
from fotc.handlers import DbCommandHandler
from fotc.poller import RemindersPoller
from fotc.util import parse_command_args, memegen_str

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
log = logging.getLogger("fotc")


def greet_handler(db_session: DbSession, bot: telegram.Bot, update: telegram.Update):
    """
    Sends a hello message back to the user
    """
    _record_presence(db_session, bot, update)
    update.message.reply_text(f"Hello, {update.message.from_user.first_name}!", quote=True)


def me_handler(db_session: DbSession, bot: telegram.Bot, update: telegram.Update):
    """
    Replaces "/me" with users first name and deletes command message
    """
    _record_presence(db_session, bot, update)
    command_split = update.message.text.split(' ')
    if len(command_split) < 2:
        update.message.reply_text("Missing arguments for /me command", quote=True)
        return

    arg = ' '.join(command_split[1:]).strip()
    update.message.reply_markdown(f"_{update.message.from_user.first_name} {arg}_",
                                  quote=False)
    try:
        update.message.delete()
    except BadRequest:
        log.info("Unable to delete message, likely due to permissions or being in a private chat")


def meme_handler(db_session: DbSession, bot: telegram.Bot, update: telegram.Update):
    """
    Downloads a captioned image from memegen and posts it to the source chat
    """
    _record_presence(db_session, bot, update)
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


def remind_me_handler(db_session: DbSession, bot: telegram.Bot, update: telegram.Update):
    user, _, group_user = _record_presence(db_session, bot, update)
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

    parse_settings = {'RETURN_AS_TIMEZONE_AWARE': True,
                      'PREFER_DATES_FROM': 'future'}
    if user.timezone:
        parse_settings['TIMEZONE'] = user.timezone

    when = dateparser.parse(args[0], settings=parse_settings)
    if not when:
        message.reply_text("Failed to parse date format", quote=True)
        return

    reminder_repo = ReminderRepository(db_session)
    reminder_repo.create_reminder(group_user, message.reply_to_message.message_id, when)
    time_s = when.strftime("%H:%M:%S")
    extra_s = when.strftime("%Y-%m-%d %Z%z")
    message.reply_text(f"Reminder created for {time_s} {extra_s}", quote=True)


def set_timezone_handler(db_session: DbSession, bot: telegram.Bot, update: telegram.Update):
    """Associates the specified timezone with the issuer who issued the command"""
    user, _, _ = _record_presence(db_session, bot, update)
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

    user_id = update.effective_user.id
    log.info("Updating timezone setting for %s: %s", user_id, tz_string)
    user.timezone =  tz_string
    update.message.reply_text(f"Timezone updated to {tz_string}", quote=True)


def do_text_replace_command(update: telegram.Update, text: str):
    command_split = update.message.text.split(' ')
    arg = ' '.join(command_split[1:]).strip()

    user = update.effective_user
    user_mention = f"<a href=\"tg://user?id={user.id}\">{user.first_name}</a>"
    message = f"{user_mention}: {arg} {text}" if arg else f"{user_mention}: {text}"

    update.message.reply_html(message, quote=False)

    try:
        update.message.delete()
    except BadRequest:
        log.info("Unable to delete message, likely due to permissions or being in a private chat")


def shrug_handler(db_session: DbSession, bot: telegram.Bot, update: telegram.Update):
    """
    Adds a shrug emoji at the end of the message and delete original message
    """
    _record_presence(db_session, bot, update)
    do_text_replace_command(update, "¯\_(ツ)_/¯")


def lenny_handler(db_session: DbSession, bot: telegram.Bot, update: telegram.Update):
    """
    Adds a shrug lenny at the end of the message and delete original message
    """
    _record_presence(db_session, bot, update)
    do_text_replace_command(update, "( ͡° ͜ʖ ͡°)")


def group_membership_handler(bot: telegram.Bot, update: telegram.Update):
    """Stream of all messages the bot can see"""
    #TODO: refactor this
    session = SessionMaker()
    try:
        _record_presence(session, bot, update)
        session.commit()
    except:
        session.rollback()


def group_time_handler(db_session: DbSession, bot: telegram.Bot, update: telegram.Update):
    """Returns localtime for all known members of a given chat"""
    _, group, _ = _record_presence(db_session, bot, update)

    chat_id = update.effective_chat.id
    group_repo = ChatGroupRepository(db_session)
    members = group_repo.list_group_members(group)
    members_with_tz = filter(lambda u: u.timezone is not None, members)
    entries = []
    for utz in members_with_tz:
        user = bot.get_chat_member(chat_id, utz.id).user
        user_mention = f"<pre>{user.first_name}</pre>"
        timezone = pytz.timezone(utz.timezone)
        localtime = pytz.utc.localize(datetime.utcnow()).astimezone(timezone)
        time_s = localtime.strftime("%H:%M:%S")
        extra_s = localtime.strftime("%Y-%m-%d %Z%z")
        entries.append(f"{user_mention} <b>{time_s}</b> <i>{extra_s}</i>")

    if entries:
        message = "\n".join(entries)
        update.message.reply_html(message, quote=True)
    else:
        update.message.reply_text("No timezone or membership info could be found", quote=True)


def add_quote_handler(db_session: DbSession, bot: telegram.Bot, update: telegram.Update):
    """Adds a message as a user quote"""
    _, group, _ = _record_presence(db_session, bot, update)
    if not update.message.reply_to_message:
        update.message.reply_text("Command must be sent as a reply to a message", quote=True)
        return

    user_repo = ChatUserRepository(db_session)
    group_repo = ChatGroupRepository(db_session)
    quoted_user_id = update.message.reply_to_message.from_user.id
    quoted_user = user_repo.find_or_create_by_id(quoted_user_id)
    quoted_group_user = group_repo.record_membership(group, quoted_user)

    quote_repo = QuoteRepository(db_session)
    message_ref = update.message.reply_to_message.message_id
    _ = quote_repo.create_quote(quoted_group_user, message_ref)
    try:
        db_session.commit()
        update.message.reply_text(f"Quote created successfully!", quote=True)
    except IntegrityError:
        #FIXME: provide better error reporting
        log.exception("Failed to create quote for user %s, message_ref %s", quoted_user_id,
                      message_ref)
        update.message.reply_text(f"Failed to create new quote due to integrity error", quote=True)


def remove_quote_handler(db_session: DbSession, bot: telegram.Bot, update: telegram.Update):
    """Adds a message as a user quote"""
    _, group, group_user = _record_presence(db_session, bot, update)
    if not update.message.reply_to_message:
        update.message.reply_text("Command must be sent as a reply to a message", quote=True)

    user_repo = ChatUserRepository(db_session)
    group_repo = ChatGroupRepository(db_session)
    quote_repo = QuoteRepository(db_session)

    reply = update.message.reply_to_message
    quoted_user = user_repo.find_or_create_by_id(reply.from_user.id)
    quoted_group_user = group_repo.record_membership(group, quoted_user)

    quote = quote_repo.find_quote(quoted_group_user, str(reply.message_id))

    if not quote:
        update.message.reply_text("Message is not a registered quote", quote=True)
        return

    if group_user.id != quoted_group_user.id:
        update.message.reply_text("Only the quoted user can remove his own quote", quote=True)
        return

    db_session.delete(quote)
    update.message.reply_text("Quote removed from database", quote=True)


def _record_presence(session: DbSession, bot: telegram.Bot, update: telegram.Update):
    user_repo = ChatUserRepository(session)
    group_repo = ChatGroupRepository(session)

    user = user_repo.find_or_create_by_id(update.effective_user.id)
    group = group_repo.find_or_create_by_id(update.effective_chat.id)
    group_user = group_repo.record_membership(group, user)

    now = datetime.utcnow()
    prev_activity = user.last_active if user.last_active else now
    user.last_active = now
    _on_user_activity(session, bot, update, user, group_user, prev_activity)
    return user, group, group_user


def _on_user_activity(session: DbSession, bot: telegram.Bot, update: telegram.Update,
                      user: ChatUser,  group_user: GroupUser, last_active: datetime):
    dt = user.last_active - last_active
    if dt > timedelta(hours=12):
        #TODO: make dt configurable
        log.info("%s has become active after %s seconds idle", user.id, dt.total_seconds())
        quote_repo = QuoteRepository(session)
        quotes = quote_repo.get_user_quotes(group_user)
        if not quotes:
            return

        quote = random.choice(quotes)
        telegram_user = update.effective_user
        user_mention = f"<a href=\"tg://user?id={telegram_user.id}\">{telegram_user.first_name}</a>"
        update.message.reply_html(f"Welcome back, {user_mention}!", quote=True)
        bot.forward_message(group_user.group_id, group_user.group_id, quote.message_ref)
        quote.last_sent_on = datetime.utcnow()


def _register_command_handlers(updater: Updater):
    """Registers all exposed Telegram command handlers"""
    updater.dispatcher.add_handler(MessageHandler(Filters.text, group_membership_handler))

    persistent = {
        "greet": greet_handler,
        "me": me_handler,
        "meme": meme_handler,
        "lenny": lenny_handler,
        "shrug": shrug_handler,
        "remindme": remind_me_handler,
        "settz": set_timezone_handler,
        "gtime": group_time_handler,
        "quote": add_quote_handler,
        "rmquote": remove_quote_handler,
    }
    for k, v in persistent.items():
        updater.dispatcher.add_handler(DbCommandHandler(k, v))


def _send_message_admin(bot: telegram.Bot, text: Text, **kwargs):
    chat_id = os.environ.get("TELEGRAM_ADMIN_CHATID", None)
    if not chat_id:
        log.warning("No admin chatId defined, would send: \"%s\"", text)
    else:
        bot.send_message(chat_id, text, **kwargs)


def _handle_sigterm(bot: telegram.Bot, poller: RemindersPoller, sig):
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
    updater.user_sig_handler = lambda sig, _: _handle_sigterm(updater.bot, poller, sig)
    _register_command_handlers(updater)
    _send_message_admin(updater.bot, "Starting up now")
    poller.start()
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()