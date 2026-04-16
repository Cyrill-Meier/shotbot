"""
ShotBot — A Telegram bot for drinking shots with friends.

Player commands:
  /start          — Show welcome message
  /join <nickname> — Join with a nickname
  /leave          — Leave the current round
  /players        — List everyone in the round
  /spin           — Randomly pick someone to drink (needs 3+ players)
  /reset          — Clear all players and start fresh

Admin-only commands (private chat):
  /mode fair      — Use true random selection (default)
  /mode rigged    — Use weighted selection
  /weight <nickname> <multiplier>  — Set how many times a player is in the pool
  /weights        — Show current weight configuration
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
ADMIN_ID = int(os.environ.get("TELEGRAM_ADMIN_ID", "0"))

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("shotbot")

# ---------------------------------------------------------------------------
# State (single-group, in-memory)
# ---------------------------------------------------------------------------
# user_id -> nickname
players: dict[int, str] = {}

# nickname (lowercase) -> weight multiplier  (default 1)
weights: dict[str, int] = {}

# "fair" or "rigged"
mode: str = "fair"


def _is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


# ---------------------------------------------------------------------------
# Player commands
# ---------------------------------------------------------------------------
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🥃 Welcome to ShotBot!\n\n"
        "Gather your friends and let the bot decide who drinks next.\n\n"
        "• /join <nickname> — hop in with a name\n"
        "• /leave — hop out\n"
        "• /players — see who's playing\n"
        "• /spin — pick a drinker (min. 3 players)\n"
        "• /reset — clear the round",
    )


async def join(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user

    if not ctx.args:
        await update.message.reply_text("Usage: /join <nickname>\nExample: /join BigMike")
        return

    nickname = " ".join(ctx.args).strip()
    if not nickname:
        await update.message.reply_text("Please provide a nickname: /join <nickname>")
        return

    # Check if nickname is already taken by someone else
    for uid, existing in players.items():
        if existing.lower() == nickname.lower() and uid != user.id:
            await update.message.reply_text(
                f"The nickname \"{nickname}\" is already taken. Pick another one!"
            )
            return

    if user.id in players:
        old = players[user.id]
        players[user.id] = nickname
        await update.message.reply_text(f"✏️ {old} is now {nickname}!")
        return

    players[user.id] = nickname
    count = len(players)
    msg = f"✅ {nickname} joined! ({count} player{'s' if count != 1 else ''})"
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
    nickname = players.pop(user.id)
    await update.message.reply_text(
        f"👋 {nickname} left. ({len(players)} remaining)"
    )


async def list_players(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not players:
        await update.message.reply_text("Nobody's here yet. Type /join <nickname> to hop in!")
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
            f"Tell your friends to /join <nickname>"
        )
        return

    # Build the pool
    if mode == "rigged":
        pool: list[int] = []
        for uid, nickname in players.items():
            w = weights.get(nickname.lower(), 1)
            pool.extend([uid] * w)
    else:
        pool = list(players.keys())

    chosen_id = random.choice(pool)
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
# Admin commands (only work in private chat with the admin)
# ---------------------------------------------------------------------------
async def set_mode(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    global mode
    user = update.effective_user

    if not _is_admin(user.id):
        await update.message.reply_text("Only the admin can change the mode.")
        return

    if update.message.chat.type != "private":
        await update.message.reply_text("Use this command in our private chat!")
        return

    if not ctx.args or ctx.args[0].lower() not in ("fair", "rigged"):
        await update.message.reply_text("Usage: /mode fair  or  /mode rigged")
        return

    mode = ctx.args[0].lower()
    if mode == "fair":
        await update.message.reply_text("✅ Mode: FAIR — true random selection.")
    else:
        await update.message.reply_text(
            "🎭 Mode: RIGGED — weighted selection active.\n"
            "Use /weight <nickname> <multiplier> to configure."
        )


async def set_weight(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user

    if not _is_admin(user.id):
        await update.message.reply_text("Only the admin can set weights.")
        return

    if update.message.chat.type != "private":
        await update.message.reply_text("Use this command in our private chat!")
        return

    if len(ctx.args) < 2:
        await update.message.reply_text(
            "Usage: /weight <nickname> <multiplier>\n"
            "Example: /weight BigMike 5\n\n"
            "This puts BigMike in the pool 5 times (5x more likely)."
        )
        return

    nickname = " ".join(ctx.args[:-1])
    try:
        multiplier = int(ctx.args[-1])
        if multiplier < 1:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Multiplier must be a positive number.")
        return

    weights[nickname.lower()] = multiplier
    await update.message.reply_text(
        f"⚖️ {nickname} weight set to {multiplier}x"
    )


async def show_weights(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user

    if not _is_admin(user.id):
        await update.message.reply_text("Only the admin can view weights.")
        return

    if update.message.chat.type != "private":
        await update.message.reply_text("Use this command in our private chat!")
        return

    lines = [f"Mode: {mode.upper()}\n"]

    if not players:
        lines.append("No players in the round yet.")
    else:
        for uid, nickname in players.items():
            w = weights.get(nickname.lower(), 1)
            lines.append(f"  • {nickname}: {w}x")

    if weights:
        # Show configured weights for players not currently in the round
        active_nicks = {n.lower() for n in players.values()}
        inactive = {k: v for k, v in weights.items() if k not in active_nicks}
        if inactive:
            lines.append("\nSaved (not in round):")
            for nick, w in inactive.items():
                lines.append(f"  • {nick}: {w}x")

    await update.message.reply_text("\n".join(lines))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN environment variable is not set. Exiting.")
        raise SystemExit(1)

    if not ADMIN_ID:
        logger.warning("TELEGRAM_ADMIN_ID not set — admin commands will be disabled.")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("join", join))
    app.add_handler(CommandHandler("leave", leave))
    app.add_handler(CommandHandler("players", list_players))
    app.add_handler(CommandHandler("spin", spin))
    app.add_handler(CommandHandler("reset", reset))

    # Admin commands
    app.add_handler(CommandHandler("mode", set_mode))
    app.add_handler(CommandHandler("weight", set_weight))
    app.add_handler(CommandHandler("weights", show_weights))

    logger.info("ShotBot is running …")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
