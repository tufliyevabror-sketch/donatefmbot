#!/bin/bash
# DonateFM bot — avtomatik ishga tushirish (cron/systemd uchun)
APP_DIR="/home/abror69/donatefmbot"
cd "$APP_DIR" || exit 1

# Band bo'lmasa ishga tushir
if [ -f logs/bot.pid ]; then
    PID=$(cat logs/bot.pid 2>/dev/null)
    if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
        exit 0
    fi
fi

exec bash "$APP_DIR/start.sh"
