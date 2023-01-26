
from telethon.errors import MessageIdInvalidError, MessageNotModifiedError
from urllib.parse import urlparse
from .. import loader, utils
from pytube import YouTube
import re
import logging
logger = logging.getLogger(__name__)


@loader.tds
class FileDownloaderMod(loader.Module):
    """YouTube Video Downloader by @kompot_69"""
    strings = {"name": "YT Downloader"}

    @loader.unrestricted
    async def dlfilecmd(self, message):
        """.ytdl <link/reply message>
           Download video from YT link."""
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
                    return await message.edit(f"<b>В пересланном сообщении обнаружено несколько ссылок ({len(match_reply)}). Укажите в аргументе индекс ссылки. Пример</b>: <code>.ytdl 1</code>")
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

        link = YouTube(url) #ссылка на видео.
        filename=link.title
        filename=re.sub(r'[^\w_. -]', '_', filename)
        try:
            await message.edit(f"<b>Загрузка</b>: <code>{link.title}</code>")
            try:
                with open('/tmp/' + filename, 'wb') as f:
                    f.write(link.streams.filter(file_extension='mp4', progressive=True).get_highest_resolution().desc().first().download())
            except Exception:
                pass
            try:
                f.close()
                await message.edit(f"<b>Выгрузка</b>: <code>{filename}</code>")
                await message.client.send_file(message.to_id, '/tmp/' + filename, caption=f"<b>[YT Downloader]</b> <code>{filename}</code>", reply_to=reply)
                await message.delete()
            except Exception as e:
                await message.edit(f"<b>Не удалось выгрузить файл</b>: <code>{e}</code>")
            try:
                os.remove('/tmp/' + filename)
            except Exception:
                pass
        except Exception as e:
            await message.edit(f"<b>Произошла ошибка</b>: <code>{e}</code>")
            os.remove('/tmp/' + filename)


            
# (mp4(720) + audio или только mp4(1080) без звука). 


#streams.filter(res='480p').desc().first()
