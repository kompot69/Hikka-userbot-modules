# Friendly Telegram File Downloader (Uploader) module by @kompot_69 & @mirivan
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
from urllib.parse import urlparse


from .. import loader, utils

logger = logging.getLogger(__name__)

def sizeof_fmt(num):
    for unit in ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB"]:
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}"
        num /= 1024.0
    return f"{num:.1f}Yi"


@loader.tds
class FileDownloaderMod(loader.Module):
    """File Downloader by @kompot_69 and @mirivan"""
    strings = {"name": "File Downloader"}

    @loader.unrestricted
    async def dlfilecmd(self, message):
        """.dlfile <link/reply message>
           Download file from link or reply message with url."""
        await message.edit("<b>Инициализация...</b>")
        reply = await message.get_reply_message()
        arg = utils.get_args_raw(message)
        url_regex = "http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"

        if reply and reply.raw_text:
            match_reply = re.findall(url_regex, reply.raw_text)
            match_arg = re.findall(url_regex, arg)
            if match_arg:
                url = match_arg[0]
            elif len(match_reply) > 1:
                try:
                    try:
                        target_match = int(arg)
                        if target_match < 0:
                            raise IndexError("target_match value lower than zero")
                        url = match_reply[target_match - 1]
                    except IndexError:
                        return await message.edit(f"<b>Ссылка с индексом [{target_match}] в пересланном сообщении не обнаружена. Подсказка: индексация начинается от числа 1.</b>")
                except (TypeError, ValueError):
                    return await message.edit(f"<b>В пересланном сообщении обнаружено несколько ссылок ({len(match_reply)}) на файлы. Укажите в аргументе индекс ссылки по которой нужно загружать файл. Пример</b>: <code>.dlfile 1</code>")
            else:
                try:
                    url = match_reply[0]
                except IndexError:
                    return await message.edit("<b>В пересланном сообщении не обнаружены ссылки.</b>")
        else:
            match_arg = re.findall(url_regex, arg)
            if match_arg:
                url = match_arg[0]
            else:
                return await message.edit("<b>Укажите ссылку в качестве аргумента или перешлите сообщение с ссылкой.</b>")

        try:
            with requests.get(url.strip(), stream=True) as r:
                r.raise_for_status()
                try:
                    content_disposition = r.headers["Content-Disposition"]
                    match = re.compile("filename=(.*)(| )")
                    filename = match.search(content_disposition).group(1)
                except (AttributeError, KeyError):
                    filename = os.path.basename(urlparse(url).path)
                    if not filename:
                        return await message.edit(f"<b>Не удалось получить имя файла.</b>")
                length = int(r.headers["Content-Length"])
                timestamp_old = timestamp_new = datetime.now()
                downloaded = 0
                await message.edit(f"<b>Загружаю файл</b>: <code>{filename}</code>")
                with open('/tmp/' + filename, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                        downloaded += len(chunk)
                        done = int(30 * downloaded / length)
                        percent = round(downloaded / length * 100, 1)
                        if timestamp_old >= timestamp_new:
                            try:
                                await message.edit(f"<b>Загружаю файл</b>: <code>{filename}</code>\n{percent}% [<code>{'=' * done}{' ' * (30-done)}</code>]")
                            except MessageNotModifiedError:
                                pass
                            timestamp_new += DT.timedelta(seconds=5)
                        else:
                            timestamp_old = datetime.now()
                    else:
                        f.close()
                        await message.edit(f"<b>Выгружаю файл</b>: <code>{filename}</code>")
                        try:
                            await message.client.send_file(message.to_id, '/tmp/' + filename, caption=f"<b>Файл загружен по ссылке</b>: <code>{url}</code>", reply_to=reply)
                            await message.delete()
                        except Exception as e:
                            await message.edit(f"<b>Не удалось выгрузить файл</b>: <code>{e}</code>")
                        try:
                            os.remove('/tmp/' + filename)
                        except Exception:
                            pass
        except MessageIdInvalidError:
            await message.client.send_message(message.to_id, "<b>Загрузка файла остановлена пользователем.</b>", reply_to=reply)
            try:
                os.remove('/tmp/' + filename)
            except Exception:
                pass
        except Exception as e:
            await message.edit(f"<b>Произошла ошибка</b>: <code>{e}</code>")
