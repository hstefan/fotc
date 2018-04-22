#!/usr/bin/env python3.6
# -*- coding: utf-8 -*-

import io
import logging
import re
import os
from typing import Tuple, Text, List, Optional

import requests
import telegram
from telegram.error import BadRequest
from telegram.ext import Updater, CommandHandler

log = logging.getLogger(__name__)


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


def _register_command_handlers(updater: Updater):
    """
    Registers all exposed Telegram command handlers
    """
    handlers = {
        "greet": greet_handler,
        "me": me_handler,
        "meme": meme_handler,
    }

    for k, v in handlers.items():
        updater.dispatcher.add_handler(CommandHandler(k, v))


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


def main():
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    token = os.environ["TELEGRAM_API_KEY"]
    updater = Updater(token)
    _register_command_handlers(updater)
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()