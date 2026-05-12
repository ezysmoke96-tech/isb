#!/bin/bash
# Creates a zip of the discord-bot folder ready for Railway upload.
set -e
cd "$(dirname "$0")/.."
zip -r discord-bot.zip discord-bot \
    --exclude "discord-bot/__pycache__/*" \
    --exclude "discord-bot/**/__pycache__/*" \
    --exclude "discord-bot/*.db" \
    --exclude "discord-bot/.env"
echo "Created discord-bot.zip"
