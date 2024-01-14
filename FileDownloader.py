# Friendly Telegram File Downloader (Uploader to Telegram) module by @kompot_69 & @mirivan
# requires: requests
import datetime as DT
import logging
import os
import re
import requests
import sys

from datetime import datetime
from io import BytesIO
from telethon.errors import MessageIdInvalidError, MessageNotModifiedError
from traceback import format_exc
from urllib.parse import urlparse


from .. import loader, utils

def sizeof_fmt(num):
    for unit in ["B", "KB", "MB", "GB"]:
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}"
        num /= 1024.0
    return f"{num:.1f}Yi"


@loader.tds
class FileDownloaderMod(loader.Module):
    strings = {"name": "File Downloader"}

    async def client_ready(self, client, db):
        self.client = client
        self.db = db

    @loader.unrestricted
    async def dlfilecmd(self, message):
        await message.edit("<b>Инициализация...</b>")
        prefix = self.db.get("dlfile", "command_prefix", ["."])[0]
        commands = [
            f"<code>{prefix}dlfile [пересланное сообщение]|<URL> [текст по окончанию загрузки]</code> - скачать файл по ссылке (продерживаются прямые ссылки, ссылки с перенаправлением), можно указать текст по окончанию загрузки - появляется вместо текста с информацией, по какой ссылке был скачан файл.",
            f"<code>{prefix}dlfile <пересланное сообщение> [индекс> [текст по окончанию загрузки]</code> - скачать файл по ссылке из пересланного сообщения, можно указать индекс ссылки по которой необходимо скачать файл (должен начинаться с 1, используется только когда в сообщении присутствует более одной ссылки)."
        ]
        usage = "<b>Использование модуля</b>:\n" + "\n".join(commands)
        reply = await message.get_reply_message()
        arg = utils.get_args_raw(message)
        url_regex = "((?:https?:\/\/)[A-z0-9]{2,}\.(?:[A-z]{2,})?[^\s]+[^. ])"

        match_arg = re.findall(url_regex, arg)
        match_reply = re.findall(url_regex, reply.raw_text) if reply and reply.raw_text else None
        if match_arg or match_reply:
            url = match_arg[0] if match_arg else match_reply[0]
            args = arg.split(" ", 1)
            last_args_index = len(args) - 1
            text = args[-1]
            if url in args and len(args) > 1:
                if not args.index(url) == last_args_index:
                    text = args[-2]

            if match_reply and len(match_reply) > 1:
                index = args[0]
                if index.isnumeric() and int(index) > 0:
                    url = match_arg[int(index) - 1] if match_arg else match_reply[int(index) - 1]
                else:
                    return await message.edit(usage)
        else:
            return await message.edit(usage)

        try:
            with requests.get(url.strip(), headers={'Accept-Encoding': None}, stream=True, timeout=(10, 5), verify=False) as r:
                if r.status_code == 404:
                    return await message.edit("<b>Ошибка 404 при запросе на URL, указанный файл не найден.</b>")
                r.raise_for_status()
                filename = r.headers.get("Content-Disposition", "").split("filename=")[-1].split(';')[0].strip() or os.path.basename(urlparse(url).path)
                if not filename:
                    return await message.edit("<b>Указаный URL не ведёт на файл.</b>")
                length = int(r.headers.get("Content-Length", 0))
                if not length:
                    return await message.edit("<b>Не удалось получить размер файла.</b>")
                me = await message.client.get_me()
                allowed_file_size = 4 if me.premium else 2
                if length > allowed_file_size * 1024 ** 3:
                    return await message.edit(f"<b>Файл не будет загружен, поскольку его размер (</b><code>{sizeof_fmt(length)}</code><b>) превышает допустимые для вас <code>{allowed_file_size}GB</code> для загрузки файлов.")
                length_h = sizeof_fmt(length)
                timestamp_old = timestamp_new = datetime.now()
                downloaded = 0
                await message.edit(f"<b>Загружаю файл</b>: <code>{filename}</code>")
                with open('/tmp/' + filename, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                        downloaded += len(chunk)
                        done = int(20 * downloaded / length)
                        percent = round(downloaded / length * 100, 1)
                        if timestamp_old >= timestamp_new:
                            try:
                                await message.edit(f"<b>Загружаю файл</b>: <code>{filename}</code>\n{percent}% [<code>{'=' * done}{' ' * (20-done)}</code>] <code>{sizeof_fmt(downloaded)}/{length_h}</code>")
                            except MessageNotModifiedError:
                                pass
                            timestamp_new += DT.timedelta(seconds=5)
                        else:
                            timestamp_old = datetime.now()
                    await message.edit(f"<b>Выгружаю файл</b>: <code>{filename}</code>")
                    caption = text or f"<b>Файл загружен по ссылке</b>: <code>{url}</code>"
                    await message.client.send_file(message.to_id, '/tmp/' + filename, caption=caption, reply_to=reply)
                    await message.delete()
        except MessageIdInvalidError:
            await message.client.send_message(message.to_id, "<b>Загрузка файла остановлена пользователем.</b>", reply_to=reply)
        except requests.exceptions.Timeout:
            await message.edit(f"<b>Истекло время ожидания от сервера</b>: <code>{url}</code>")
        except Exception as e:
            traceback = re.sub("(`|\\|\\||\\*\\*|__|~~)", "", format_exc())
            await message.edit(f"<b>Произошла ошибка</b>:\n\n<code>{traceback}</code>")
        if filename:
            os.remove('/tmp/' + filename)
