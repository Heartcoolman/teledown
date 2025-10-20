from typing import Iterable, Optional

from telethon import TelegramClient, events
from telethon.tl.types import MessageMediaDocument, MessageMediaPhoto

from tools.down_file import download_file
from tools.tool import GetChatId, GetChatTitle


async def StartMonit(client: TelegramClient, channel_ids: Iterable[str], prefix: Optional[str] = None):
    resolved_ids = []
    for channel_id in channel_ids:
        chat_id = await GetChatId(client, channel_id)
        resolved_ids.append(chat_id)
    resolved_ids = list(dict.fromkeys(resolved_ids))

    @client.on(events.NewMessage(chats=resolved_ids))
    async def event_handler(event):
        chat_id = event.chat_id
        channel_title = await GetChatTitle(client, chat_id)
        message = event.message
        if isinstance(message.media, (MessageMediaDocument, MessageMediaPhoto)):
            await download_file(client, channel_title, chat_id, message, prefix=prefix)
        elif message.media is None:
            content = f'From:{channel_title}\n{message.message}'
            await client.send_message(entity='me', message=content)
