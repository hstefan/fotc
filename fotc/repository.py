# -*- coding: utf-8 -*-
from datetime import datetime

from typing import List, Optional

from fotc.database import ChatUser, GroupUser, ChatGroup, Reminder, ChatGroupUserQuote
from sqlalchemy.orm.session import Session as DbSession


class ChatUserRepository(object):
    def __init__(self, session: DbSession):
        self.session = session

    def find_or_create_by_id(self, user_id: int) -> ChatUser:
        user = self.session.query(ChatUser).filter(ChatUser.id == user_id).first()
        if not user:
            user = ChatUser(id=user_id, last_active=datetime.utcnow(), timezone=None)
            self.session.add(user)
        return user


class ChatGroupRepository(object):
    def __init__(self, session: DbSession):
        self.session = session

    def find_or_create_by_id(self, group_id: int) -> ChatGroup:
        group = self.session.query(ChatGroup).filter(ChatGroup.id == group_id).first()
        if not group:
            group = ChatGroup(id=group_id)
            self.session.add(group)
        return group

    def is_user_member(self, group: ChatGroup, user: ChatUser) -> bool:
        group_user = self._find_membership(group, user)
        return group_user is not None

    def record_membership(self, group: ChatGroup, user: ChatUser) -> GroupUser:
        group_user = self._find_membership(group, user)
        if not group_user:
            group_user = GroupUser(user_id=user.id, group_id=group.id)
            self.session.add(group_user)
        return group_user

    def list_group_members(self, group: ChatGroup) -> List[ChatUser]:
        members = self.session.query(ChatUser) \
            .join(GroupUser, GroupUser.user_id == ChatUser.id) \
            .join(ChatGroup, GroupUser.group_id == ChatGroup.id) \
            .filter(ChatGroup.id == group.id)
        return members.all()

    def find_group_user_by_id(self, group_user_id: int) -> Optional[GroupUser]:
        return self.session.query(GroupUser) \
            .filter(GroupUser.id == group_user_id) \
            .first()

    def _find_membership(self, group: ChatGroup, user: ChatUser) -> Optional[GroupUser]:
        return self.session.query(GroupUser) \
            .filter(GroupUser.group_id == group.id) \
            .filter(GroupUser.user_id == user.id) \
            .first()


class ReminderRepository(object):
    def __init__(self, session: DbSession):
        self.session = session

    def create_reminder(self, group_user: GroupUser, message_ref: str,
                        scheduled_time: datetime) -> Reminder:
        reminder = Reminder(group_user=group_user,
                            message_ref=message_ref,
                            scheduled_for=scheduled_time,
                            sent_on=None)
        self.session.add(reminder)
        return reminder

    def query_due_reminders(self) -> List[Reminder]:
        return self.session.query(Reminder) \
            .filter(Reminder.sent_on.is_(None)) \
            .filter(Reminder.scheduled_for <= datetime.utcnow()) \
            .all()


class QuoteRepository(object):
    def __init__(self, session: DbSession):
        self.session = session

    def create_quote(self, group_user: GroupUser, message_ref: str) -> ChatGroupUserQuote:
        quote = ChatGroupUserQuote(group_user=group_user, message_ref=message_ref,
                                   last_sent_on=None)
        self.session.add(quote)
        return quote

    def get_user_quotes(self, group_user: GroupUser) -> List[ChatGroupUserQuote]:
        return self.session.query(ChatGroupUserQuote) \
            .filter(ChatGroupUserQuote.group_user_id == group_user.id) \
            .order_by(ChatGroupUserQuote.last_sent_on.asc()) \
            .all()

    def find_quote(self, group_user: GroupUser, message_ref: str) -> Optional[ChatGroupUserQuote]:
        return self.session.query(ChatGroupUserQuote) \
            .filter(ChatGroupUserQuote.group_user_id == group_user.id) \
            .filter(ChatGroupUserQuote.message_ref == message_ref) \
            .one_or_none()
