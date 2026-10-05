#!/bin/bash
# DonateFM bot — faqat shu loyihani to'xtatadi
cd "$(dirname "$0")" || exit 1

PIDFILE="logs/bot.pid"
if [ -f "$PIDFILE" ]; then
    PID=$(cat "$PIDFILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "🛑 Bot to'xtatilmoqda (PID $PID)..."
        # bolalar cloudflared/ngrok ham yopiladi
        pkill -P "$PID" 2>/dev/null
        kill "$PID" 2>/dev/null
        sleep 2
        kill -9 "$PID" 2>/dev/null
    else
        echo "ℹ️  Protsess allaqachon to'xtagan."
    fi
    rm -f "$PIDFILE"
else
    echo "ℹ️  pid fayl topilmadi. Jarayonni qidiraman..."
fi

# faqat shu papkadagi main.py
THIS_DIR="$(pwd)"
pkill -f "$THIS_DIR.*main\.py" 2>/dev/null

# faqat shu papkadagi 8010 portidagi cloudflared/ngrok
pkill -f "cloudflared tunnel --url http://127.0.0.1:8010" 2>/dev/null
pkill -f "ngrok http 8010" 2>/dev/null

rm -f logs/bot.lock
echo "✅ DonateFM bot to'xtatildi."
