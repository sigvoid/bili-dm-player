# -*- coding: utf-8 -*-

from dm_player import DmPlayer

import asyncio
import http.cookies
import random
from typing import *

import aiohttp

import blivedm
import blivedm.models.web as web_models

# 直播间ID的取值看直播间URL
TEST_ROOM_ID = 9792252

# 这里填一个已登录账号的cookie的SESSDATA字段的值。不填也可以连接，但是收到弹幕的用户名会打码，UID会变成0
SESSDATA = ''

session: Optional[aiohttp.ClientSession] = None

dmplayer = DmPlayer()

async def dm_monitor():
    init_session()
    try:
        await run_single_client()
    finally:
        await session.close()


def init_session():
    cookies = http.cookies.SimpleCookie()
    cookies['SESSDATA'] = SESSDATA
    cookies['SESSDATA']['domain'] = 'bilibili.com'

    global session
    session = aiohttp.ClientSession()
    session.cookie_jar.update_cookies(cookies)


async def run_single_client():
    room_id = TEST_ROOM_ID
    client = blivedm.BLiveClient(room_id, session=session)
    handler = MyHandler()
    client.set_handler(handler)

    client.start()
    try:
        await client.join()
    finally:
        await client.stop_and_close()

def test_callback(user, msg):
    # 可以给消息写类似的callback，从而设置l2d表情、换人说话等
    print(f'{user}: {msg}')

class MyHandler(blivedm.BaseHandler):

    def _on_heartbeat(self, client: blivedm.BLiveClient, message: web_models.HeartbeatMessage):
        pass

    def _on_danmaku(self, client: blivedm.BLiveClient, message: web_models.DanmakuMessage):
        dmplayer.Add(message.msg, "bubu.wav", test_callback, message.uname, message.msg) # 可以给消息写类似的callback

    def _on_gift(self, client: blivedm.BLiveClient, message: web_models.GiftMessage):
        dmplayer.Add(f'感谢{message.uname}赠送的{message.num}个{message.gift_name}，阿里嘎多！', "po.wav")

    def _on_buy_guard(self, client: blivedm.BLiveClient, message: web_models.GuardBuyMessage):
        dmplayer.Add(f'感谢{message.uname}的{message.gift_name}，阿里嘎多！', "po.wav")

    def _on_super_chat(self, client: blivedm.BLiveClient, message: web_models.SuperChatMessage):
        dmplayer.Add(f'{message.uname}说：{message.message}', "dingding.wav")


if __name__ == '__main__':
    dmplayer.Start()
    dmplayer.LoadCharacter("圣园未花")
    dmplayer.SetVoiceOption(0.6, 0.668, 1.1)
    asyncio.run(dm_monitor())