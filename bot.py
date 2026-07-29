#!/usr/bin/env python3
import asyncio
import base64
import logging
import os
import sys
import tempfile
import time
from typing import Optional

from deltachat2 import events, MsgData
from deltabot_cli import BotCli

import database
from forgejo_client import ForgejoClient
from post_builder import parse_message_text, build_post_files_payload

VERSION = "1.0.1"

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


@dc_cli.on(events.NewMessage)
def on_new_message(bot, accid: int, event):
    msg = event.msg
    sender_addr = msg.from_id
    if not sender_addr:
        return

    # Don't process bot's own messages
    bot_contact = bot.rpc.get_contact(accid, sender_addr)
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
            bot.rpc.send_msg(accid, chat_id, MsgData(text=get_help_message()))
            return

        elif cmd == "/initadmin":
            current_admin = database.get_admin_email()
            if current_admin and current_admin != sender_email.lower():
                bot.rpc.send_msg(
                    accid, chat_id,
                    MsgData(text=f"❌ Ownership already claimed by {current_admin}.")
                )
                return
            
            database.set_config("admin_dc_email", sender_email.lower())
            if fingerprint:
                database.set_admin_fingerprint(fingerprint)
            
            bot.rpc.send_msg(
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
            bot.rpc.send_msg(accid, chat_id, MsgData(text=donate_text))
            return

        elif cmd == "/status":
            configured = forgejo_client.is_configured()
            conn_ok = forgejo_client.check_connection() if configured else False
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
            bot.rpc.send_msg(accid, chat_id, MsgData(text=status_text))
            return

        elif cmd == "/list":
            if not database.is_authorized_sender(sender_email, fingerprint):
                bot.rpc.send_msg(accid, chat_id, MsgData(text="⛔ Access denied. Only administrator can view post list."))
                return

            recent = database.get_recent_posts(limit=5)
            if not recent:
                bot.rpc.send_msg(accid, chat_id, MsgData(text="📭 No published posts logged yet."))
                return

            lines = ["📚 Recently Published Posts:\n"]
            for p in recent:
                t_str = time.strftime('%Y-%m-%d %H:%M', time.localtime(p['created_at']))
                sha_str = f" (`{p['commit_sha'][:7]}`)" if p['commit_sha'] else ""
                lines.append(f"• **{p['title']}**\n  Slug: `{p['slug']}` | {t_str}{sha_str}")

            bot.rpc.send_msg(accid, chat_id, MsgData(text="\n".join(lines)))
            return

        elif cmd in ("/transports", "/addtransport", "/rmtransport", "/setprimary", "/resilient"):
            # Standard transport management placeholder
            bot.rpc.send_msg(
                accid, chat_id,
                MsgData(text=f"ℹ️ Transport administration for {cmd}: Default primary transport is active.")
            )
            return

        elif cmd == "/stats":
            stats = database.get_all_transport_stats()
            if not stats:
                bot.rpc.send_msg(accid, chat_id, MsgData(text="📊 No transport stats recorded yet."))
                return
            lines = ["📊 Transport Statistics:\n"]
            for s in stats:
                lines.append(f"• `{s['addr']}`: Sent {s['msgs_sent']}, Received {s['msgs_received']}")
            bot.rpc.send_msg(accid, chat_id, MsgData(text="\n".join(lines)))
            return

    # Check Authorization for publishing
    if not database.is_authorized_sender(sender_email, fingerprint):
        logger.warning(f"Unauthorized post attempt from {sender_email} (fp: {fingerprint})")
        reply = (
            "⛔ Access Denied: You are not authorized to publish to this blog.\n\n"
            "If you are the bot administrator, run `/initadmin` to claim ownership."
        )
        bot.rpc.send_msg(accid, chat_id, MsgData(text=reply))
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
            bot.rpc.send_msg(
                accid, chat_id,
                MsgData(text="⚠️ Cannot publish empty message. Send a title, text, or image.")
            )
            return

        # Notify user processing started
        processing_msg = bot.rpc.send_msg(
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
        result = forgejo_client.commit_files(files_payload, commit_msg)

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
        bot.rpc.send_msg(accid, chat_id, MsgData(text=success_response))

    except Exception as e:
        logger.exception("Failed to publish post via Forgejo API")
        err_reply = f"❌ **Publishing Failed**: {str(e)}"
        bot.rpc.send_msg(accid, chat_id, MsgData(text=err_reply))


@dc_cli.on_init
def on_init(bot, _args):
    accounts = bot.rpc.get_all_account_ids()
    if not accounts:
        accid = bot.rpc.add_account()
    else:
        accid = accounts[0]

    # Configure bot profile metadata from environment variables
    bot_name = os.environ.get("DISPLAY_NAME", "Delta Chat Publish Bot")
    bot.rpc.set_config(accid, "displayname", bot_name)

    status_text = os.environ.get("STATUS_TEXT", "Publishes blog posts directly to Git/Astro via Delta Chat")
    bot.rpc.set_config(accid, "selfstatus", status_text)

    avatar_env = os.environ.get("AVATAR_PATH")
    avatar_paths = []
    base_dir = os.path.dirname(os.path.abspath(__file__))
    if avatar_env:
        if os.path.isabs(avatar_env):
            avatar_paths.append(avatar_env)
        else:
            avatar_paths.append(os.path.join(base_dir, avatar_env))
            avatar_paths.append(os.path.abspath(avatar_env))

    avatar_paths.extend([
        os.path.join(base_dir, "avatar.png"),
        os.path.join(base_dir, "avatar.jpg"),
        os.path.join(base_dir, "icon.png"),
        os.path.join(base_dir, "icon.jpg")
    ])

    for path in avatar_paths:
        if os.path.exists(path):
            bot.rpc.set_config(accid, "selfavatar", path)
            break

    if not bot.rpc.is_configured(accid):
        bot.rpc.set_config(accid, "bot", "1")
        relay = os.getenv("RELAY", "chatmail.uk").strip()
        addr = os.getenv("ADDR")
        mail_pw = os.getenv("MAIL_PW")

        if addr and mail_pw:
            bot.logger.info(f"Configuring account for {addr}...")
            params = {"addr": addr, "password": mail_pw}
            mail_server = os.getenv("MAIL_SERVER")
            mail_port = os.getenv("MAIL_PORT")
            if mail_server:
                params["mail_server"] = mail_server
            if mail_port:
                params["mail_port"] = mail_port
            bot.rpc.add_or_update_transport(accid, params)
        elif relay:
            bot.logger.info(f"Auto-creating new chatmail account on relay '{relay}'...")
            qr_uri = relay if (relay.startswith("DCACCOUNT:") or relay.startswith("http")) else f"DCACCOUNT:{relay}"
            bot.rpc.add_transport_from_qr(accid, qr_uri)
        else:
            bot.logger.error("No account credentials (ADDR/MAIL_PW) or RELAY set!")


@dc_cli.on_start
def on_start(bot, _args):
    bot.logger.info(f"🚀 Delta Chat Publish Bot v{VERSION} is running. Waiting for events...")

    try:
        import io
        try:
            import qrcode
        except ImportError:
            qrcode = None

        accounts = bot.rpc.get_all_account_ids()
        if accounts:
            accid = accounts[0]
            qrdata = None
            for _ in range(10):
                try:
                    if bot.rpc.is_configured(accid):
                        qrdata = bot.rpc.get_chat_securejoin_qr_code(accid, None)
                        if qrdata:
                            break
                except Exception:
                    pass
                time.sleep(0.5)

            if qrdata:
                print("\n" + "=" * 50)
                print("To add this bot, scan the QR code or copy the link:\n")
                if qrcode:
                    qr = qrcode.QRCode(version=1, box_size=1, border=2)
                    qr.add_data(qrdata)
                    qr.make(fit=True)
                    f = io.StringIO()
                    qr.print_ascii(out=f)
                    print(f.getvalue(), flush=True)
                print(qrdata, flush=True)
                print("=" * 50 + "\n", flush=True)
    except Exception as e:
        bot.logger.error(f"Failed to generate QR code: {e}")


def main():
    database.init_db()
    logger.info(f"Starting Delta Chat Publish Bot v{VERSION}...")
    
    # Ensure default config_dir uses persistent /app/data volume if available
    if "-c" not in sys.argv and "--config-dir" not in sys.argv:
        default_dir = "/app/data" if os.path.exists("/app/data") else "data"
        sys.argv.insert(1, "-c")
        sys.argv.insert(2, default_dir)

    # Parse CLI arguments and start bot
    dc_cli.start()


if __name__ == "__main__":
    main()
