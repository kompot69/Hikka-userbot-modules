# ---------------------------------------------------------------------------------
# Name: File Downloader
# Description: Загрузка файлов по ссылке в Телеграм чат
# meta developer: @mirivan & @kompot_69
# ---------------------------------------------------------------------------------
__version__ = (3,2)
# requires: requests
import datetime, logging, requests
import os, re

from io import BytesIO
from telethon.errors import MessageIdInvalidError, MessageNotModifiedError
from traceback import format_exc
from urllib.parse import urlparse

from .. import loader, utils
logger = logging.getLogger(__name__)

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
    """File Downloader (Uploader to Telegram)"""
    
    strings = {"name": "File Downloader"}

    async def client_ready(self, client, db):
        self.client = client
        self.db = db

    async def initialize(self, message):
        message_to_edit = await utils.answer(message, f"<b>[{self.strings['name']}]</b>\nИнициализация...")
        reply = await message.get_reply_message()
        return message_to_edit, reply

    @loader.unrestricted
    async def dlfilecmd(self, message):
        """<URL | ответ на сообщение [индекс ссылки]> - скачать файл по ссылке и выгрузить в текущий диалог"""
        message_to_edit, reply = await self.initialize(message)
        arg = utils.get_args_raw(message)
        url_regex = r'(?i)\b((?:https?|ftp)://(?:[a-z0-9-]+(?:\.[a-z0-9-]+)+|\[[0-9a-f:.]+\])(?::\d+)?(?:/[^\s]*)?)'
    
        match_arg = re.findall(url_regex, arg)
        match_reply = re.findall(url_regex, reply.raw_text) if reply and reply.raw_text else []

        if match_arg or match_reply:
            urls = match_arg or match_reply

            if len(urls) > 1: # >1 URL
                if arg.isdigit() and 0 < int(arg) <= len(urls):  url = urls[int(arg) - 1]
                else: return await message_to_edit.edit(f"<b>[{self.strings['name']}]</b>\nНе указан индекс ссылки для загрузки.")
            else: url = urls[0]
            url_domain = re.search(r"^(?:https?:\/\/)?([^\/:]+)", url).group(1) or url

            # выделяем текст после ссылки (если есть)
            args = arg.split(" ", 1)
    
        else: return await message_to_edit.edit(f"<b>[{self.strings['name']}]</b>\nВ сообщении не найдена ссылка.")

        try:
            with requests.get(url.strip(), headers={'Accept-Encoding': None}, stream=True, timeout=(10, 5), verify=False) as r:
                if r.status_code == 404:
                    return await message_to_edit.edit(f"<b>[{self.strings['name']}]</b>\n<a href='{url}'>{url_domain}</a> вернул ошибку 404")
                r.raise_for_status()
                filename = r.headers.get("Content-Disposition", "").split("filename=")[-1].split(';')[0].strip() or os.path.basename(urlparse(url).path)
                if not filename:
                    return await message_to_edit.edit(f"<b>[{self.strings['name']}]</b>\n<a href='{url}'>Указаный URL</a> не ведёт на файл.")
                length = int(r.headers.get("Content-Length", 0))
                if not length:
                    return await message_to_edit.edit(f"<b>[{self.strings['name']}]</b>\nНе удалось получить размер <a href='{url}'>файла</a>")
                me = await message.client.get_me()
                is_premium =  getattr(me, "premium", False)
                allowed_file_size = 4 if is_premium else 2
                if length > allowed_file_size * 1024 ** 3:
                    return await message_to_edit.edit(f"<b>[{self.strings['name']}]</b>\nРазмер <a href='{url}'>файла</a> (<code>{sizeof_fmt(length)}</code>) превышает лимит в <code>{allowed_file_size}GB</code>")
                length_h = sizeof_fmt(length)
                downloaded = 0
                with open('/tmp/' + filename, 'wb') as file:
                    for chunk in r.iter_content(chunk_size=8192):
                        file.write(chunk)
                        downloaded += len(chunk)
                        done = int(20 * downloaded / length)
                        percent = round(downloaded / length * 100, 1)
                        now = datetime.datetime.now(tz=datetime.timezone.utc)
                        if message_to_edit.edit_date and now > message_to_edit.edit_date + delta:
                            message_to_edit = await message_to_edit.edit(f"<b>[{self.strings['name']}]</b>\nЗагрузка <a href='{url}'>{filename} с сайта {url_domain}</a>\n<code>[{'▓' * done}{'░' * (20-done)}]</code>\n<code>{sizeof_fmt(downloaded)}/{length_h} | {percent}%</code>")
                    file.close()
            await message.client.send_file(
                (reply.to_id if reply else message.to_id), 
                f'/tmp/{filename}', 
                caption=(f"<b>Файл загружен по ссылке</b>: {url}" if len(url)<300 else f"<b>Файл загружен c сайта <a href='{url}'>{url_domain}</a></b>"),
                reply_to=reply,
                progress_callback=lambda d, t: message.client.loop.create_task( progress(d, t, message, filename, self.strings['name']) )
            )
            await message_to_edit.delete()
            del tasks[message_to_edit.id]

        except MessageIdInvalidError:
            await message.client.send_message(message.to_id, f"<b>[{self.strings['name']}]</b>\nЗагрузка <a href='{url}'>файла</a> остановлена пользователем.", reply_to=reply)
        except MessageNotModifiedError:
            pass
        except requests.exceptions.Timeout:
            await message_to_edit.edit(f"<b>[{self.strings['name']}]</b>\nИстекло время ожидания от <a href='{url}'>{url_domain}</a>")
        except Exception as e:
            traceback = re.sub("(`|\\|\\||\\*\\*|__|~~)", "", format_exc())
            await message_to_edit.edit(f"<b>[{self.strings['name']}]</b>\nПри загрузке <a href='{url}'>файла</a> произошла ошибка:\n\n<code>{traceback}</code>")
        if filename:
            try:
                os.remove("/tmp/" + filename)
            except:
                await message.client.send_message(message.to_id, f"<b>[{self.strings['name']}]</b>\nОшибка удаления временного файла:\n<code>{format_exc()}</code>", reply_to=reply)

async def progress(current, total, message, filename, module_name):
    if not message.id in tasks:
        message = await message.edit(f"<b>[{module_name}]</b>\nФайл <code>{filename}</code> загружен.")
        tasks[message.id] = message.edit_date + delta
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    if now > tasks[message.id]:
        percent = round(current / total * 100, 1)
        done = int(20 * current / total)
        try:
            message = await message.edit(f"<b>[{module_name}]</b>\nВыгрузка <code>{filename}</code>\n<code>[{'█' * done}{'▓' * (20-done)}]</code>\n<code>{sizeof_fmt(current)}/{sizeof_fmt(total)} | {percent}%</code>")
            tasks[message.id] = message.edit_date + delta
        except MessageNotModifiedError:
            pass
