"""
ShotBot — A Telegram bot for drinking shots with friends.

Commands:
  /start  — Show welcome message
  /join   — Join the current round
  /leave  — Leave the current round
  /players — List everyone in the round
  /spin   — Randomly pick someone to drink (needs 3+ players)
  /reset  — Clear all players and start fresh
"""

import os
import random
import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
MIN_PLAYERS = int(os.environ.get("MIN_PLAYERS", "3"))

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("shotbot")

# ---------------------------------------------------------------------------
# State  (single-group, in-memory)
# ---------------------------------------------------------------------------
players: dict[int, str] = {}  # user_id -> display_name


def _name(user) -> str:
    """Build a readable display name from a Telegram User object."""
    if user.username:
        return f"@{user.username}"
    return user.first_name or "Anonymous"


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🥃 *Welcome to ShotBot!*\n\n"
        "Gather your friends and let the bot decide who drinks next\\.\n\n"
        "• /join — hop in\n"
        "• /leave — hop out\n"
        "• /players — see who's playing\n"
        "• /spin — pick a drinker \\(min\\. 3 players\\)\n"
        "• /reset — clear the round\n",
        parse_mode="MarkdownV2",
    )


async def join(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user.id in players:
        await update.message.reply_text(f"{_name(user)}, you're already in! 🍻")
        return
    players[user.id] = _name(user)
    count = len(players)
    msg = f"✅ {_name(user)} joined! ({count} player{'s' if count != 1 else ''})"
    if count >= MIN_PLAYERS:
        msg += "\n\nEnough players — someone can /spin now! 🎰"
    else:
        msg += f"\n\nNeed {MIN_PLAYERS - count} more to start spinning."
    await update.message.reply_text(msg)


async def leave(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user.id not in players:
        await update.message.reply_text("You're not in the round. /join first!")
        return
    del players[user.id]
    await update.message.reply_text(
        f"👋 {_name(user)} left. ({len(players)} remaining)"
    )


async def list_players(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not players:
        await update.message.reply_text("Nobody's here yet. Type /join to hop in!")
        return
    roster = "\n".join(f"  • {name}" for name in players.values())
    await update.message.reply_text(
        f"🧑‍🤝‍🧑 Current players ({len(players)}):\n{roster}"
    )


async def spin(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if len(players) < MIN_PLAYERS:
        need = MIN_PLAYERS - len(players)
        await update.message.reply_text(
            f"Not enough players! Need {need} more (minimum {MIN_PLAYERS}).\n"
            f"Tell your friends to /join 🫵"
        )
        return

    chosen_id = random.choice(list(players.keys()))
    chosen_name = players[chosen_id]

    phrases = [
        f"🎯 {chosen_name} — bottoms up! 🥃",
        f"🔥 The bottle points to {chosen_name}! Drink up!",
        f"🍀 Luck has spoken: {chosen_name}, take your shot!",
        f"🫡 {chosen_name}, it's your turn. Cheers!",
        f"💀 No escape, {chosen_name}. Down the hatch!",
    ]
    await update.message.reply_text(random.choice(phrases))


async def reset(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    players.clear()
    await update.message.reply_text("🔄 Round cleared! Everyone /join again to play.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN environment variable is not set. Exiting.")
        raise SystemExit(1)

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("join", join))
    app.add_handler(CommandHandler("leave", leave))
    app.add_handler(CommandHandler("players", list_players))
    app.add_handler(CommandHandler("spin", spin))
    app.add_handler(CommandHandler("reset", reset))

    logger.info("ShotBot is running …")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
