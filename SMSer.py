# ---------------------------------------------------------------------------------
# Name: SMSer
# Description: Отправка сообщений через SMS
# meta developer: @kompot_69
# ---------------------------------------------------------------------------------
__version__ = (1,5,"public beta") 

from .. import loader, utils
from telethon import types
from telethon.tl.types import PeerUser, PeerChannel
import logging, subprocess, asyncio, re
logger = logging.getLogger(__name__)

async def del_msg_timer(sec, message):
    await asyncio.sleep(sec)
    await message.delete()

sms_queue = asyncio.Queue()
async def sms_sender(): # очередь sms
    try:
        logger.debug(f'sms queue started')
        while True:
            try:
                # return logger.info(await sms_queue.get())
                tg_message, answer_data, del_sec, sms_text, to_number, timeout = await sms_queue.get()
                if answer_data[0]: message_answer = await utils.answer(tg_message, answer_data[1], reply_to=tg_message)

                cmd = ["gammu", "-c", "/root/.gammurc", "sendsms", "TEXT", f"+{to_number}", "-unicode", "-len", "64", "-text", sms_text ]
                proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE )
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
                logger.debug(f'Сообщение от {tg_message.from_id} было отправлено по СМС на номер {to_number}')
                if answer_data[0]: await utils.answer(message_answer, answer_data[2])
                if proc.returncode != 0: logger.error(f"Ошибка gammu:\n{stdout.decode()}\n{stderr.decode()}")

            except asyncio.TimeoutError:
                proc.kill()
                await proc.communicate()
                logger.warning(f"Отправка SMS прервана по таймауту")
                if answer_data[0]: await utils.answer(message_answer, answer_data[3]+' (timeout)')
            except subprocess.CalledProcessError as e: 
                logger.error(f"Ошибка выполнения команды:\n{e.stdout}\n{e.stderr}")
                if answer_data[0]: await utils.answer(message_answer, answer_data[3])
            except FileNotFoundError as e: 
                logger.error(f"Команда gammu не найдена.")
                if answer_data[0]: await utils.answer(message_answer, answer_data[3])
            
            if answer_data[0] and del_sec > 0: asyncio.create_task(del_msg_timer(del_sec,message_answer))

    except asyncio.CancelledError: logger.debug(f'sms queue stopped')
    except Exception as e: logger.error(f'sms queue error: {e}', exc_info=True)

@loader.tds
class SMSMod(loader.Module):
    """Отправка сообщений по SMS"""

    strings = {
        "name": "SMSer",
        "_cfg_is_answer": "Уведомлять ли в чате об отправке сообщения?",
        "_cfg_answer_sending_text": "Текст уведомления о попытке отправки.",
        "_cfg_answer_sended_text": "Текст уведомления об успешной отправке.",
        "_cfg_answer_send_error_text": "Текст уведомления об ошибке отправки.",
        "_cfg_del_sec": "Время удаления уведомления в секундах. (0 - не удалять)",
        "_cfg_use_whitelist": "Использовать ли белый список ID чатов?",
        "_cfg_whitelist_ids": "Белый список ID чатов (через запятую).",
        "_cfg_to_number": "Номер, на который отправлять SMS (без +).",
        "_cfg_sms_add_date": "Добавлять ли время сообщений (по UTC) в SMS.",
        "_cfg_timeout": "Лимит в секундах на отправку одного SMS.",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue("is_answer", True, lambda m: self.strings["_cfg_is_answer"], validator=loader.validators.Boolean()),
            loader.ConfigValue("answer_sending_text", "🕒 Отправка сообщения по SMS...", lambda m: self.strings["_cfg_answer_sending_text"]),
            loader.ConfigValue("answer_sended_text", "ℹ️ Сообщение отправлено по SMS", lambda m: self.strings["_cfg_answer_sended_text"]),
            loader.ConfigValue("answer_send_error_text", "❕ Ошибка отправки сообщения по SMS", lambda m: self.strings["_cfg_answer_send_error_text"]),
            loader.ConfigValue("delete_seconds", "15", lambda m: self.strings["_cfg_del_sec"]),
            loader.ConfigValue("use_whitelist", False, lambda m: self.strings["_cfg_use_whitelist"], validator=loader.validators.Boolean()),
            loader.ConfigValue("whitelist_ids", "390623928,", lambda m: self.strings["_cfg_whitelist_ids"]),
            loader.ConfigValue("to_number", "79000000000", lambda m: self.strings["_cfg_to_number"]),
            loader.ConfigValue("sms_add_date", True, lambda m: self.strings["_cfg_sms_add_date"], validator=loader.validators.Boolean()),
            loader.ConfigValue("timeout", "600", lambda m: self.strings["_cfg_timeout"]),
        )
        self.name = self.strings["name"]
        
    async def client_ready(self, client, db):
        self._db = db
        self._me = await client.get_me()

    async def smscmd(self, message):
        """ вкл/выкл отправку сообщений по SMS"""
        if self.get_sms_status(): 
            self._db.set(__name__, "sms", False)
            self._db.set(__name__, "ratelimit", [])
            await self.allmodules.log("sms off")
            self.sms_sender_task.cancel() 
            await self.sms_sender_task
            message_answer = await utils.answer(message, "<b>✖ Отправка сообщений по SMS отключена</b>")
            if int(self.config["delete_seconds"]) > 0:
                await asyncio.sleep(int(self.config["delete_seconds"])*2)
                await message_answer.delete()
        else: 
            await utils.answer(message, "<b>🕒 Идентификация модема...</b>")
            if not await self.modem_identificate(): return await utils.answer(message, "<b>⚠️ Не удалось идентифицировать модем</b>")
            self._db.set(__name__, "sms", True)
            self._db.set(__name__, "ratelimit", [])
            await self.allmodules.log("sms on")
            self.sms_sender_task = asyncio.create_task(sms_sender())
            message_answer = await utils.answer(message, "<b>☑ Отправка сообщений по SMS включена</b>")
            if int(self.config["delete_seconds"]) > 0:
                await asyncio.sleep(int(self.config["delete_seconds"])*2)
                await message_answer.delete()

    async def watcher(self, message):
        if not isinstance(message, types.Message): return
        if message.mentioned or getattr(message.to_id, "user_id", None) == self._me.id:
            if self.get_sms_status() is not True: return
            user = await utils.get_user(message)

            ratelimit = self._db.get(__name__, "ratelimit", [])
            if message.id in ratelimit: return
            else:
                logger.debug("Новое сообщение найдено.")
                self._db.setdefault(__name__, {}).setdefault("ratelimit", []).append(message.id)
                self._db.save()
            if user.is_self or user.bot or user.verified:
                logger.debug("Сообщение от себя, бота или официального аккаунта.")
                return
            if self.config["use_whitelist"]:
                whitelist_ids = self.config["whitelist_ids"].replace(" ", "").split(",")
                if utils.get_chat_id(message) not in whitelist_ids: return

            try: 
                sms_text=''
                if self.config["sms_add_date"]: sms_text += '[ '+str(message.date.strftime("%d.%m.%Y %H:%M"))+' UTC ]\n'
                sms_text+=f'{message.sender.first_name} {message.sender.last_name or ""} {message.from_id}'
                if message.from_id != utils.get_chat_id(message): sms_text+=f' в чате {utils.get_chat_id(message)}'
                if message.fwd_from: 
                    sms_text+=' (переслано'
                    if isinstance(message.fwd_from.from_id, PeerUser):
                        user = await message.client.get_entity(message.fwd_from.from_id.user_id)
                        sms_text+=f" от {user.first_name or ''} {user.last_name or ''} {message.fwd_from.from_id.user_id} "
                    elif isinstance(message.fwd_from.from_id, PeerChannel):
                        channel = await message.client.get_entity(message.fwd_from.from_id.channel_id)
                        sms_text+=f" из {channel.title}" 
                    elif message.fwd_from.from_name: sms_text+=f' от {message.fwd_from.from_name}'
                    sms_text+=')'
                if message.text: sms_text+=f":\n{message.text}"
                if message.media and hasattr(message.media, 'document'):
                    sms_text += f'\nВложение: {message.media.document.mime_type}'

                answer_data=[self.config["is_answer"], self.config["answer_sending_text"], self.config["answer_sended_text"], self.config["answer_send_error_text"],]
                await sms_queue.put((message, answer_data, int(self.config["delete_seconds"]), sms_text, self.config["to_number"], self.config["timeout"]))
                    
            except Exception as e: logger.error(e, exc_info=True) # выдает ошибку
            
    async def modem_identificate(self):
        logger.debug("Идентификация модема...")
        try:
            cmd = ["gammu", "-c", "/root/.gammurc", "--identify"]
            proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=self.config["timeout"])
                stdout_lines = stdout.decode(errors="ignore").splitlines()
                logger.info(stdout_lines)
                modem_interface = next((line for line in stdout_lines if "Device" in line), None)
                if modem_interface: modem_interface = modem_interface.split(":", 1)[1].strip()
                else: modem_interface = None
                modem_model = next((line for line in stdout_lines if "Model" in line), None)
                if modem_model: modem_model = modem_model.split(":", 1)[1].strip()
                else: modem_model = None
                if not modem_model and not modem_interface: return None
                return modem_model, modem_interface
            except asyncio.TimeoutError:
                proc.kill()
                await proc.communicate()
                return logger.warning("Идентификация модема прервана по таймауту.")
        except subprocess.CalledProcessError as e:
            return logger.warning(f"Модем в системе не найден: {e}")
        except FileNotFoundError:
            return logger.error("Команда gammu не найдена.")
            
    def get_sms_status(self):
        return self._db.get(__name__, "sms", False)
