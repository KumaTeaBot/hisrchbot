import os
import pickle
import logging  # bot.session imported bot.store
from pyrogram.types import Message
from common.data import msg_data_dir, GROUP_MSG_LIMIT, TRUSTED_GROUP_MSG_LIMIT
from dataclasses import dataclass
from typing import Optional
from common.local import trusted_group


@dataclass
class TextMessage:
    id: int
    text: str


def get_text_message(msg: Message) -> Optional[TextMessage]:
    text = msg.text or msg.caption
    if text:
        return TextMessage(msg.id, text)
    return None


class TextMsgStore:
    def __init__(self):
        self.msgs = {}
        self.load()

    def raw_add_msg(self, chat_id: int, msg_id: int, text: str) -> None:
        # assert chat_id and msg_id and text
        if chat_id not in self.msgs:
            self.msgs[chat_id] = {}
        self.msgs[chat_id][msg_id] = TextMessage(msg_id, text)

    def add_msg(self, msg: Message) -> None:
        try:
            chat_id = msg.chat.id
            msg_id = msg.id
        except AttributeError:
            return None
        if chat_id not in self.msgs:
            self.msgs[chat_id] = {}
        text_msg = get_text_message(msg)
        if text_msg:
            self.msgs[chat_id][msg_id] = text_msg
    
    def delete_msg(self, msg: Message) -> None:
        try:
            chat_id = msg.chat.id
            msg_id = msg.id
        except AttributeError:
            return None
        if chat_id in self.msgs and msg_id in self.msgs[chat_id]:
            del self.msgs[chat_id][msg_id]
            logging.info(f'[bot.store]\tDeleting message {msg_id} from chat {chat_id}')

    def update_msg(self, msg: Message) -> None:
        text = msg.text or msg.caption
        if text:
            return self.add_msg(msg)
        else:
            return self.delete_msg(msg)

    def get_msg(self, chat_id: int, msg_id: int) -> Optional[TextMessage]:
        # if chat_id in self.msgs:
        #     if msg_id in self.msgs[chat_id]:
        #         return self.msgs[chat_id][msg_id]
        # return None
        return self.msgs.get(chat_id, {}).get(msg_id, None)

    def clean_all(self) -> None:
        cleaned = 0
        # if len(self.msgs) > 100:
        #     # find last 100 active chats
        #     active_chats = sorted(
        #         self.msgs.keys(),
        #         key=lambda x: max([msg.date for msg in self.msgs[x].values()]),
        #         reverse=True
        #     )[:100]
        #     # clear all other chats
        #     for chat_id in self.msgs:
        #         if chat_id not in active_chats:
        #             del self.msgs[chat_id]
        #             logging.warning(f'[bot.store]\tClearing inactive chat {chat_id}')
        #             cleared += 1
        for chat_id in self.msgs:
            limit = GROUP_MSG_LIMIT if chat_id not in trusted_group else TRUSTED_GROUP_MSG_LIMIT
            if len(self.msgs[chat_id]) > limit:
                msg_ids = self.msgs[chat_id].keys()
                msg_ids = sorted(msg_ids)  # int
                msg_ids = msg_ids[len(msg_ids) - limit:]

                # self.msgs[chat_id] = {k: v for k, v in self.msgs[chat_id].items() if k in msg_ids}
                for msg_id in self.msgs[chat_id]:
                    if msg_id not in msg_ids:
                        del self.msgs[chat_id][msg_id]

                logging.warning(f'[bot.store]\tCleaning messages for chat {chat_id}')
                cleaned += 1
        if cleaned:
            self.save()

    def clear_chat(self, chat_id: int) -> None:
        if chat_id in self.msgs and self.msgs[chat_id]:
            # del self.msgs[chat_id]
            self.msgs[chat_id] = {}
            logging.warning(f'[bot.store]\tRemoving chat {chat_id}')
            self.save()

    def chat_to_json(self, chat_id: int) -> list:
        # return [msg.id for msg in self.msgs.get(chat_id, {}).values()]
        msg_list = [
            {
                'id': msg.id,
                'text': msg.text
            }
            for msg in self.msgs.get(chat_id, {}).values()
        ]
        return msg_list

    def chat_from_json(self, chat_id: int, msg_list: list) -> None:
        self.msgs[chat_id] = {
            msg['id']: TextMessage(msg['id'], msg['text'])
            for msg in msg_list
        }

    def save(self) -> None:
        with open(f'{msg_data_dir}/msg.p', 'wb') as f:
            pickle.dump(self.msgs, f)

    def load(self) -> None:
        if os.path.isfile(f'{msg_data_dir}/msg.p'):
            with open(f'{msg_data_dir}/msg.p', 'rb') as f:
                self.msgs = pickle.load(f)
            logging.info(f'[bot.store]\tLoaded {len(self.msgs)} messages from file')
