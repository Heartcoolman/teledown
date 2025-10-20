import argparse
import asyncio
import json
import os
import sys
from typing import Iterable

from telethon import TelegramClient

from tools.down_file import down_group
from tools.monit import StartMonit
from tools.tool import Hook, initDb, md5, print_all_channel, print_group
from tools.upload_file import upload_file

# 1.创建解释器
parser = argparse.ArgumentParser()
# 2.创建一个互斥参数组
mutex_group = parser.add_mutually_exclusive_group()
# 3.添加需要的参数
parser.add_argument('-c', '--config', default='config.json', help='配置文件')
parser.add_argument('-re', '--refresh', action='store_true', help='刷新缓存')
mutex_group.add_argument('-up', '--upload', action='store_true', help='上传文件')
mutex_group.add_argument('-down', '--download', action='store_true', help='下载文件')
mutex_group.add_argument('-print', action='store_true', help='打印消息')
mutex_group.add_argument('-m', '--monit', action='store_true', help='监控频道')
parser.add_argument('-id', help='频道ID')
parser.add_argument('-user', help='指定下载用户', default=None)
parser.add_argument('--range', default='>0', help='下载范围')
parser.add_argument('--prefix', help='通配符', default=None)
parser.add_argument('-path', help='上传路径')
parser.add_argument('-dau', default='N', choices=['y', 'Y', 'n', 'N'], help='上传完成删除原文件')
parser.add_argument('-at', '--addtag', help='增加tag')
parser.add_argument('--proxy', help='代理')
# 3.进行参数解析
args = parser.parse_args()
config_path = args.config
# 配置处理开始
with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)
api_id = config.get('api_id')
api_hash = config.get('api_hash')
phone = config.get('phone')
bot_token = config.get('bot_token')
alias = config.get('alias')
if (phone is not None and bot_token is not None) or (phone is None and bot_token is None):
    print('请确认使用机器人登录还是电话号码登录')
    exit()
if phone:
    md5Token = md5(phone)
else:
    md5Token = md5(bot_token)
if alias:
    for _id in alias:
        os.environ[_id] = alias[_id]
initDb(md5Token)
os.environ['save_path'] = save_path = config.get('save_path')
proxy = config.get('proxy')
if proxy is None and config.get('proxy_port') is not None:
    proxy = f"127.0.0.1:{config['proxy_port']}"
if args.proxy is not None:
    proxy = args.proxy
if proxy is not None:
    import python_socks

    username = None
    password = None
    ip_port = proxy
    if '@' in proxy:
        auth_ipaddress = proxy.split('@')
        user_pass = auth_ipaddress[0].split(':')
        username = user_pass[0]
        password = user_pass[1]
        ip_port = auth_ipaddress[1]
    # 适配ipv6
    addr_port = ip_port.rsplit(':', 1)
    addr = addr_port[0]
    port = addr_port[1]
    proxy = {
        'proxy_type': python_socks.ProxyType.SOCKS5,  # (mandatory) protocol to use (see above)
        'addr': addr,  # (mandatory) proxy IP address
        'port': int(port),  # (mandatory) proxy port number
        'username': username,  # (optional) username if the proxy requires auth
        'password': password,  # (optional) password if the proxy requires auth
        'rdns': True  # (optional) whether to use remote or local resolve, default remote
    }
    client = TelegramClient(md5Token, api_id, api_hash, proxy=proxy)
else:
    client = TelegramClient(md5Token, api_id, api_hash)


# 配置处理结束


# 展示登陆的信息
def show_my_inf(me):
    print("-----****************-----")
    print("Name:", me.username)
    print("ID:", me.id)
    print("-----login successful-----")


async def client_main() -> None:
    print("-client-main-")
    me = await client.get_me()
    show_my_inf(me)


async def run() -> int:
    # 除了刷新缓存，都需要频道ID
    if not args.refresh and args.id is None:
        print('缺失频道ID')
        return 1
    if args.upload and args.path is None:
        print('缺失上传路径')
        return 1

    await client.start(phone=phone, bot_token=bot_token)
    try:
        await client_main()
        await Hook(client)

        if args.refresh:
            await print_all_channel(client=client)
        if args.download:
            if 't.me' in args.id:
                tmp_list = args.id.split('/')
                channel_id = tmp_list[-2]
                plus_func = '=' + tmp_list[-1]
            else:
                channel_id = args.id
                plus_func = args.range
            for _id in _split_items(channel_id, '|'):
                await down_group(client, _id, plus_func, args.user, args.prefix)
        elif args.upload:
            del_after_upload = args.dau.upper() == 'Y'
            await upload_file(client, args.id, args.path, del_after_upload, args.addtag)
        elif args.print:
            await print_group(client, args.id)
        elif args.monit:
            channel_ids = list(_split_items(args.id, ','))
            if not channel_ids:
                print('缺失监控频道ID')
                return 1
            await StartMonit(client, channel_ids, prefix=args.prefix)
            print('监控已启动，按 Ctrl+C 结束')
            await client.disconnected
    finally:
        await client.disconnect()
    return 0


def _split_items(text: str, delimiter: str) -> Iterable[str]:
    for item in text.split(delimiter):
        stripped = item.strip()
        if stripped:
            yield stripped


if __name__ == '__main__':
    sys.exit(asyncio.run(run()))
