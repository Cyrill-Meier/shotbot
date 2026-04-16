# ShotBot

A Telegram bot for drinking shots with friends. Once 3+ players join, anyone can spin to randomly pick the next drinker.

## Commands

| Command    | Description                              |
|------------|------------------------------------------|
| `/start`   | Show welcome message                     |
| `/join`    | Join the current round                   |
| `/leave`   | Leave the current round                  |
| `/players` | List everyone in the round               |
| `/spin`    | Randomly pick someone to drink           |
| `/reset`   | Clear all players and start fresh        |

## Quick Start

1. Create a bot via [@BotFather](https://t.me/BotFather) and copy the token
2. Clone this repo and create a `.env` file:

```bash
cp .env.example .env
# paste your token into .env
```

3. Run with Docker Compose:

```bash
docker compose up -d --build
```

## Docker Image

Every push to `main` builds and publishes a Docker image to GitHub Container Registry.

```bash
docker pull ghcr.io/<your-username>/shotbot:latest
docker run -e BOT_TOKEN=your-token ghcr.io/<your-username>/shotbot:latest
```

## Configuration

| Variable      | Default | Description                        |
|---------------|---------|------------------------------------|
| `BOT_TOKEN`   | —       | Telegram bot token (required)      |
| `MIN_PLAYERS` | `3`     | Minimum players before /spin works |
