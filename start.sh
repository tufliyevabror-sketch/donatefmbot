#!/bin/bash
# DonateFM bot ishga tushirish (Linux/Termux)
cd "$(dirname "$0")" || exit 1
mkdir -p logs data

if [ ! -d /data/data/com.termux ] && [ "$ALLOW_LAPTOP" != "1" ]; then
    export ALLOW_LAPTOP=1
fi

# Python tanlash: tashqi venv > lokal venv
if [ -x /tmp/game-shop-venv/bin/python ]; then
    BIN=/tmp/game-shop-venv/bin/python
elif [ -x venv/bin/python ]; then
    BIN=venv/bin/python
else
    BIN=python3
fi

LOGFILE="$PWD/logs/bot.log"
echo "🚀 Ishga tushirilmoqda (python: $BIN, log: $LOGFILE)..."

# Agar bot systemd (user) tomonidan boshqarilsa — qo'lda urinmang.
# Aks holda ikkita instansiya bot.lock uchun kurashadi.
if command -v systemctl >/dev/null 2>&1 && systemctl --user cat donatefmbot.service >/dev/null 2>&1; then
    STATE=$(systemctl --user is-active donatefmbot.service 2>/dev/null)
    case "$STATE" in
        active|activating|reloading|deactivating)
            echo "ℹ️  Bot systemd tomonidan boshqarilmoqda (donatefmbot.service: $STATE)."
            echo "   Qayta ishga tushirish: systemctl --user restart donatefmbot"
            echo "   Holat:                 systemctl --user status donatefmbot"
            echo "   Log:                   journalctl --user -u donatefmbot -f"
            exit 1
            ;;
    esac
fi

if [ -f logs/bot.pid ]; then
    OLD_PID=$(cat logs/bot.pid 2>/dev/null)
    if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
        echo "🛑 Eski protsess to'xtatilmoqda (PID $OLD_PID)..."
        pkill -P "$OLD_PID" 2>/dev/null
        kill "$OLD_PID" 2>/dev/null
        sleep 1
        kill -9 "$OLD_PID" 2>/dev/null
    fi
    rm -f logs/bot.pid logs/bot.lock
fi

rm -f logs/bot.lock
cd "$PWD" && ALLOW_LAPTOP=1 PYTHONUNBUFFERED=1 nohup "$BIN" -u main.py >> "$LOGFILE" 2>&1 &
echo $! > logs/bot.pid
sleep 4

NEW_PID=$(cat logs/bot.pid)
if kill -0 "$NEW_PID" 2>/dev/null; then
    echo "✅ Boshlandi. PID=$NEW_PID"
    echo "📄 Log:  tail -f logs/bot.log"
    echo "🌐 URL:  grep -E 'trycloudflare|ngrok' logs/*.log | tail -5"
else
    echo "❌ Bot ishga tushmadi! Loglarni tekshiring:"
    echo "   tail -50 logs/bot.log"
    exit 1
fi
