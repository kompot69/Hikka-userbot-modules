# requires: pornhub-api

from random import choice

from pornhub_api import PornhubApi
from telethon import types

from .. import loader, utils


@loader.tds
class PhSrchMod(loader.Module):
    strings = {"name": "PornHub"}

    @loader.owner
    async def sphcmd(self, m: types.Message):
        "Найти видео на PornHub"
        if args := utils.get_args_raw(m):
            srch = args
        else:
            return await m.delete()
        api = PornhubApi()
        data = api.search.search(srch, ordering="mostviewed")
        video = choice(data.videos)
        await m.reply(
            f'<b>Нашёл кое-что по запросу</b> <code>{srch}</code>: <a href="{video.url}">{video.title}</a>',
            parse_mode='html'
        )
