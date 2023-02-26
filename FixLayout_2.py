from .. import loader, utils
@loader.tds
class FixLayoutMod(loader.Module):
	"""Фиксит раскладку"""
	strings = {"name": "FixLayout"}
	@loader.owner
	async def printcmd(self, message):
		""".fl <text or reply>"""
		layout = dict(zip(map(ord, "qwertyuiop[]asdfghjkl;'zxcvbnm,./`" 'QWERTYUIOP{}ASDFGHJKL:"ZXCVBNM<>?~'), "йцукенгшщзхъфывапролджэячсмитьбю.ё" 'ЙЦУКЕНГШЩЗХЪФЫВАПРОЛДЖЭЯЧСМИТЬБЮ,Ё'))
		text = utils.get_args_raw(message)
		if not text:
			reply = await message.get_reply_message()
			if not reply or not reply.message:
				await message.edit("<b>Текста нет!</b>")
				return
			text = reply.message
		text = text.translate(layout)
		await message.edit(text)
