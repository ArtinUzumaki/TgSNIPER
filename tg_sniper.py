#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import json
import os
from datetime import datetime
from telethon import TelegramClient
from telethon.errors import UsernameNotOccupiedError
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.types import InputPeerEmpty, PeerUser, PeerChat, PeerChannel
from rich import print
from rich.table import Table
import config

LOG = config.LOG_FILE

def log_change(kind: str, old: str, new: str):
    entry = {
        "time": datetime.utcnow().isoformat(),
        "kind": kind,
        "old": old,
        "new": new
    }
    if os.path.exists(LOG):
        data = json.load(open(LOG, "r", encoding="utf-8"))
    else:
        data = []
    data.append(entry)
    with open(LOG, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

async def fetch_user(client, username: str):
    try:
        result = await client(GetFullUserRequest(username))
        user = result.users[0]  # اصلاح‌شده
        full = result.full_user  # اصلاح‌شده
        return user, full
    except UsernameNotOccupiedError:
        print(f"[red]❌ No account found for @{username}[/red]")
        return None, None

async def list_dialogs(client):
    dialogs = await client(GetDialogsRequest(
        offset_date=None,
        offset_id=0,
        offset_peer=InputPeerEmpty(),
        limit=100,
        hash=0
    ))
    return dialogs.chats, dialogs.messages

def show_summary(user, full):
    print("[bold cyan]\n────────────── Info Summary ──────────────[/bold cyan]")
    print(f"🆔 ID: [green]{user.id}[/green]")
    print(f"👤 Name: [green]{user.first_name or ''} {user.last_name or ''}[/green]")
    print(f"📛 Username: [green]@{user.username or ''}[/green]")

    bio = getattr(full, "about", None)
    print(f"📄 Bio: [green]{bio or 'None'}[/green]")

    has_photo = hasattr(full, "profile_photo") and full.profile_photo
    print(f"🖼️ Profile Picture: [green]{'✅' if has_photo else '❌'}[/green]")

    last_seen = getattr(user.status, 'was_online', None) or getattr(user.status, 'expires', None)
    print(f"📶 Last Seen: [green]{last_seen or 'Unknown'}[/green]")

async def show_dialogs(chats, messages):
    tbl = Table(title="\nPrivate Chats / Groups", show_lines=True)
    tbl.add_column("Name", style="cyan")
    tbl.add_column("Type", style="magenta")
    tbl.add_column("Unread", justify="right", style="red")
    tbl.add_column("Last Message", style="yellow")

    # آخرین پیام‌ها رو استخراج می‌کنیم
    last_msgs = {}
    for msg in messages:
        peer_id = None
        if isinstance(msg.peer_id, PeerUser):
            peer_id = msg.peer_id.user_id
        elif isinstance(msg.peer_id, PeerChat):
            peer_id = msg.peer_id.chat_id
        elif isinstance(msg.peer_id, PeerChannel):
            peer_id = msg.peer_id.channel_id

        if peer_id is not None:
            last_msgs[peer_id] = msg.message

    for chat in chats:
        typ = type(chat).__name__
        name = getattr(chat, "title", None) or f"{getattr(chat, 'first_name', '')} {getattr(chat, 'last_name', '')}".strip()
        unread = str(getattr(chat, "unread_count", 0))
        lm = last_msgs.get(chat.id, "")
        if not lm:
            lm = ""
        tbl.add_row(name, typ, unread, lm[:30] + ("…" if len(lm) > 30 else ""))
    print(tbl)

async def main():
    username = input("[blue][?] Enter target username (without @): [/blue]").strip()
    async with TelegramClient(config.SESSION_NAME, config.API_ID, config.API_HASH) as client:
        user, full = await fetch_user(client, username)
        if not user:
            return

        # بررسی تغییرات bio / photo
        prev = {}
        if os.path.exists(LOG):
            prev = {e["kind"]: e["new"] for e in json.load(open(LOG, "r", encoding="utf-8"))}

        bio = getattr(full, "about", None)
        if bio and prev.get("bio") != bio:
            log_change("bio", prev.get("bio", ""), bio)

        has_photo = hasattr(full, "profile_photo") and full.profile_photo
        if has_photo and prev.get("photo") != "present":
            log_change("photo", prev.get("photo", "none"), "present")

        # نمایش خلاصه
        show_summary(user, full)

        # نمایش دیالوگ‌ها
        chats, messages = await list_dialogs(client)
        await show_dialogs(chats, messages)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[red]❌ Interrupted by user[/red]")
