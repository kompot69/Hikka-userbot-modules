from .. import loader, utils  # pylint: disable=relative-beyond-top-level
import io


@loader.tds
class x0Mod(loader.Module):
	"""Uploader"""
	strings = {
		"name": "Transfer.sh Uploader"
	}

	async def client_ready(self, client, db):
		self.client = client
	
	
	@loader.sudo
	async def transfershcmd(self, message):
		await message.edit("<b>...</b>")
		reply = await message.get_reply_message()
		if not reply:
			await message.edit("<b>Reply to message/media!</b>")
			return
     await message.edit("<b>Uploading...</b>")
		media = reply.media
		if not media:
			file = io.BytesIO(bytes(reply.raw_text, "utf-8"))
			file.name = "temp.txt"
		else:
			file = io.BytesIO(await self.client.download_file(media))
			file.name = reply.file.name if reply.file.name else  reply.file.id+reply.file.ext
		try:
			transfer = post('https://transfer.sh/'+file.name, files={'file': file})
		except ConnectionError as e:
			await message.edit(ste(e))
			return
		url = transfer.text
		output = f'<a href="{url}">URL: </a><code>{url}</code>'
		await message.edit(output)
