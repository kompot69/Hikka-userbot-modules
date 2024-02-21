# requires: requests
import datetime
import logging
import os
import re
import requests
import sys

from io import BytesIO
from telethon.errors import MessageIdInvalidError, MessageNotModifiedError
from traceback import format_exc
from urllib.parse import urlparse


from .. import loader, utils

delta = datetime.timedelta(seconds=3)
tasks = {}

def sizeof_fmt(num):
    for unit in ["B", "KB", "MB", "GB"]:
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}"
        num /= 1024.0
    return f"{num:.1f}Yi"


@loader.tds
class FileDownloaderMod(loader.Module):
    """File Downloader (Uploader to Telegram) v2.1 
    by @kompot_69 & @mirivan"""
    
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
        url_regex = r"(?:https?:\/\/)[A-Za-z0-9]{2,}.(?:[A-Za-z]{2,})?[^\s]+"

        match_arg = re.findall(url_regex, arg)
        match_reply = re.findall(url_regex, reply.raw_text) if reply and reply.raw_text else None
        if match_arg or match_reply:
            url = match_arg[0] if match_arg else match_reply[0]
            args = arg.split(" ", 1)
            last_args_index = len(args) - 1
            text = None
            if len(args) > 1:
                if args.index(url) == last_args_index:
                    return await message.edit("1 "+usage)
                else:
                    text = args[1]

            if match_reply and len(match_reply) > 1:
                index = args[0]
                if index.isnumeric() and int(index) > 0:
                    url = match_arg[int(index) - 1] if match_arg else match_reply[int(index) - 1]
                else:
                    return await message.edit("2 "+usage)
        else:
            return await message.edit("3 "+usage)

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
                is_premium =  getattr(me, "premium", False)
                allowed_file_size = 4 if is_premium else 2
                if length > allowed_file_size * 1024 ** 3:
                    return await message.edit(f"<b>Файл не будет загружен, поскольку его размер (</b><code>{sizeof_fmt(length)}</code><b>) превышает допустимые для вас <code>{allowed_file_size}GB</code> для загрузки файлов.")
                length_h = sizeof_fmt(length)
                downloaded = 0
                message = await message.edit(f"<b>Загружаю файл</b>: <code>{filename}</code>")
                with open('/tmp/FTG_fileDownloader/' + filename, 'wb') as file:
                    for chunk in r.iter_content(chunk_size=8192):
                        file.write(chunk)
                        downloaded += len(chunk)
                        done = int(20 * downloaded / length)
                        percent = round(downloaded / length * 100, 1)
                        now = datetime.datetime.now(tz=datetime.timezone.utc)
                        if message.edit_date and now > message.edit_date + delta:
                            message = await message.edit(f"<b>Загружаю файл</b>: <code>{filename}</code>\n{percent}% [<code>{'=' * done}{' ' * (20-done)}</code>] <code>{sizeof_fmt(downloaded)}/{length_h}</code>")
                    file.close()
            await message.client.send_file(
                message.to_id, '/tmp/FTG_fileDownloader/' + filename,
                caption=(
                    text or f"<b>Файл загружен по ссылке</b>: <code>{url}</code>"
                ),
                reply_to=reply,
                progress_callback=lambda d, t: message.client.loop.create_task(
                    progress(d, t, message, filename)
                )
            )
            await message.delete()
            del tasks[message.id]
        except MessageIdInvalidError:
            await message.client.send_message(message.to_id, "<b>Загрузка файла остановлена пользователем.</b>", reply_to=reply)
        except MessageNotModifiedError:
            pass
        except requests.exceptions.Timeout:
            await message.edit(f"<b>Истекло время ожидания от сервера</b>: <code>{url}</code>")
        except Exception as e:
            traceback = re.sub("(`|\\|\\||\\*\\*|__|~~)", "", format_exc())
            await message.edit(f"<b>Произошла ошибка</b>:\n\n<code>{traceback}</code>")
        if filename:
            try:
                os.remove("/tmp/FTG_fileDownloader/" + filename)
            except:
                await message.client.send_message(message.to_id, f"<b>Ошибка удаления временного файла</b>:\n\n<code>{format_exc()}</code>", reply_to=reply)

async def progress(current, total, message, filename):
    if not message.id in tasks:
        message = await message.edit(f"<b>Выгружаю файл</b>: <code>{filename}</code>")
        tasks[message.id] = message.edit_date + delta
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    if now > tasks[message.id]:
        percent = round(current / total * 100, 1)
        done = int(20 * current / total)
        current = sizeof_fmt(current)
        total = sizeof_fmt(total)
        progress = f"{percent}% [<code>{'=' * done}{' ' * (20-done)}</code>] <code>{current}/{total}</code>"
        try:
            message = await message.edit(f"<b>Выгружаю файл</b>: <code>{filename}</code>\n{progress}")
            tasks[message.id] = message.edit_date + delta
        except MessageNotModifiedError:
            pass
