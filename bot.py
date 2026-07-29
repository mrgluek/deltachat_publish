#!/usr/bin/env python3
import asyncio
import base64
import logging
import os
import sys
import tempfile
import time
from typing import Optional

from deltachat2 import events, MsgData, Bot
from deltabot_cli import BotCli

import database
from forgejo_client import ForgejoClient
from post_builder import parse_message_text, build_post_files_payload

VERSION = "1.0.0"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("deltachat_publish")

dc_cli = BotCli("publishbot")
forgejo_client = ForgejoClient()


def get_help_message() -> str:
    admin_email = database.get_admin_email()
    owner_str = f"Owner: {admin_email}" if admin_email else "Owner: Not claimed (use /initadmin in private chat)"
    return (
        f"📝 Delta Chat Publish Bot v{VERSION}\n"
        f"{owner_str}\n\n"
        f"Publishing to blog: {forgejo_client.repo_owner}/{forgejo_client.repo_name} ({forgejo_client.branch})\n\n"
        f"📌 How to publish a post:\n"
        f"Send a message where:\n"
        f"• Line 1 = Post Title\n"
        f"• Line 2+ = Post Body (Markdown)\n"
        f"• Attachments = Photos/files embedded automatically\n\n"
        f"⚙️ Available Commands:\n"
        f"• /help - Show this documentation\n"
        f"• /initadmin - Claim bot ownership (private chat)\n"
        f"• /status - Check Forgejo Git API connection\n"
        f"• /list - Show recently published posts\n"
        f"• /stats - Show bot transport statistics\n"
        f"• /transports - Show configured mail relays\n"
        f"• /addtransport <addr> <pass> [host] [port] - Add mail transport\n"
        f"• /rmtransport <addr> - Remove mail transport\n"
        f"• /setprimary <addr> - Set primary mail transport\n"
        f"• /resilient <on|off> - Toggle transport failover\n"
        f"• /donate - Support bot development\n"
    )


@events.on(events.NewMessage)
async def on_new_message(bot: Bot, accid: int, msg: MsgData):
    sender_addr = msg.from_id
    if not sender_addr:
        return

    # Don't process bot's own messages
    bot_contact = await bot.rpc.get_contact(accid, sender_addr)
    if bot_contact.get("is_self"):
        return

    sender_email = bot_contact.get("address", "")
    fingerprint = bot_contact.get("fingerprint", "")
    chat_id = msg.chat_id
    text = (msg.text or "").strip()

    # Track message stats
    database.update_transport_stats(sender_email, received=True)

    # Command handling
    if text.startswith("/"):
        parts = text.split()
        cmd = parts[0].lower()

        if cmd == "/help" or cmd == "/start":
            await bot.rpc.send_msg(accid, chat_id, MsgData(text=get_help_message()))
            return

        elif cmd == "/initadmin":
            current_admin = database.get_admin_email()
            if current_admin and current_admin != sender_email.lower():
                await bot.rpc.send_msg(
                    accid, chat_id,
                    MsgData(text=f"❌ Ownership already claimed by {current_admin}.")
                )
                return
            
            database.set_config("admin_dc_email", sender_email.lower())
            if fingerprint:
                database.set_admin_fingerprint(fingerprint)
            
            await bot.rpc.send_msg(
                accid, chat_id,
                MsgData(text=f"✅ Ownership successfully claimed by {sender_email}!")
            )
            return

        elif cmd == "/donate":
            donate_text = (
                "☕ Support Delta Chat Publish Bot development!\n\n"
                "Donate link: https://gluek.info/donate\n"
                "Thank you for your support!"
            )
            await bot.rpc.send_msg(accid, chat_id, MsgData(text=donate_text))
            return

        elif cmd == "/status":
            configured = forgejo_client.is_configured()
            conn_ok = await forgejo_client.check_connection() if configured else False
            status_text = (
                f"⚙️ Bot Diagnostics:\n"
                f"• Version: v{VERSION}\n"
                f"• Forgejo Instance: {forgejo_client.base_url}\n"
                f"• Repository: {forgejo_client.repo_owner}/{forgejo_client.repo_name}\n"
                f"• Target Branch: {forgejo_client.branch}\n"
                f"• Layout Format: {os.getenv('BLOG_POST_FORMAT', 'single_file')}\n"
                f"• API Token Configured: {'✅ Yes' if configured else '❌ No (FORGEJO_TOKEN missing)'}\n"
                f"• Connection Test: {'✅ OK' if conn_ok else '❌ Failed / Unreachable'}\n"
            )
            await bot.rpc.send_msg(accid, chat_id, MsgData(text=status_text))
            return

        elif cmd == "/list":
            if not database.is_authorized_sender(sender_email, fingerprint):
                await bot.rpc.send_msg(accid, chat_id, MsgData(text="⛔ Access denied. Only administrator can view post list."))
                return

            recent = database.get_recent_posts(limit=5)
            if not recent:
                await bot.rpc.send_msg(accid, chat_id, MsgData(text="📭 No published posts logged yet."))
                return

            lines = ["📚 Recently Published Posts:\n"]
            for p in recent:
                t_str = time.strftime('%Y-%m-%d %H:%M', time.localtime(p['created_at']))
                sha_str = f" (`{p['commit_sha'][:7]}`)" if p['commit_sha'] else ""
                lines.append(f"• **{p['title']}**\n  Slug: `{p['slug']}` | {t_str}{sha_str}")

            await bot.rpc.send_msg(accid, chat_id, MsgData(text="\n".join(lines)))
            return

        elif cmd in ("/transports", "/addtransport", "/rmtransport", "/setprimary", "/resilient"):
            # Standard transport management placeholder
            await bot.rpc.send_msg(
                accid, chat_id,
                MsgData(text=f"ℹ️ Transport administration for {cmd}: Default primary transport is active.")
            )
            return

        elif cmd == "/stats":
            stats = database.get_all_transport_stats()
            if not stats:
                await bot.rpc.send_msg(accid, chat_id, MsgData(text="📊 No transport stats recorded yet."))
                return
            lines = ["📊 Transport Statistics:\n"]
            for s in stats:
                lines.append(f"• `{s['addr']}`: Sent {s['msgs_sent']}, Received {s['msgs_received']}")
            await bot.rpc.send_msg(accid, chat_id, MsgData(text="\n".join(lines)))
            return

    # Check Authorization for publishing
    if not database.is_authorized_sender(sender_email, fingerprint):
        logger.warning(f"Unauthorized post attempt from {sender_email} (fp: {fingerprint})")
        reply = (
            "⛔ Access Denied: You are not authorized to publish to this blog.\n\n"
            "If you are the bot administrator, run `/initadmin` to claim ownership."
        )
        await bot.rpc.send_msg(accid, chat_id, MsgData(text=reply))
        return

    # Handle Post Creation
    try:
        title, body, description = parse_message_text(text)
        
        # Download attachments if message contains photos/files
        attachments = []
        if msg.file:
            try:
                blob_path = msg.file
                if os.path.exists(blob_path):
                    with open(blob_path, "rb") as f:
                        data = f.read()
                    filename = os.path.basename(blob_path)
                    attachments.append({"filename": filename, "bytes": data})
            except Exception as e:
                logger.error(f"Error reading attached file: {e}")

        if not title and not attachments and not body:
            await bot.rpc.send_msg(
                accid, chat_id,
                MsgData(text="⚠️ Cannot publish empty message. Send a title, text, or image.")
            )
            return

        # Notify user processing started
        processing_msg = await bot.rpc.send_msg(
            accid, chat_id,
            MsgData(text=f"⏳ Packaging and committing post: **{title}**...")
        )

        files_payload, slug, _ = build_post_files_payload(
            title=title,
            body=body,
            description=description,
            attachments=attachments
        )

        commit_msg = f"Publish post: {title}"
        result = await forgejo_client.commit_files(files_payload, commit_msg)

        commit_sha = ""
        commit_url = ""
        if isinstance(result, dict):
            commit_obj = result.get("commit", {})
            commit_sha = commit_obj.get("sha", "") if isinstance(commit_obj, dict) else ""
            commit_url = result.get("html_url", "") or result.get("url", "")

        database.log_published_post(slug=slug, title=title, commit_sha=commit_sha)

        sha_display = f" (`{commit_sha[:7]}`)" if commit_sha else ""
        url_display = f"\n🔗 Commit: {commit_url}" if commit_url else ""

        success_response = (
            f"🚀 **Post Successfully Published!**\n\n"
            f"• **Title**: {title}\n"
            f"• **Slug**: `{slug}`{sha_display}\n"
            f"• **Files**: {len(files_payload)} file(s) committed via Forgejo API{url_display}\n\n"
            f"Site build pipeline will automatically trigger."
        )
        await bot.rpc.send_msg(accid, chat_id, MsgData(text=success_response))

    except Exception as e:
        logger.exception("Failed to publish post via Forgejo API")
        err_reply = f"❌ **Publishing Failed**: {str(e)}"
        await bot.rpc.send_msg(accid, chat_id, MsgData(text=err_reply))


def main():
    database.init_db()
    logger.info(f"Starting Delta Chat Publish Bot v{VERSION}...")
    
    # Parse CLI arguments and run bot
    dc_cli.run()


if __name__ == "__main__":
    main()
