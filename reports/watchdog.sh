#!/bin/bash
# DonateFM watchdog — har 5 daqiqada: bot + WebApp sog'lommi?
# Muammo bo'lsa: botni o'zi restart qiladi, admin'ga Telegram'dan xabar yuboradi.
BASE=/home/abror69/donatefmbot
cd "$BASE" || exit 0

TOKEN=$(grep -E "^BOT_TOKEN=" .env 2>/dev/null | cut -d= -f2-)
ADMIN=$(grep -E "^ADMIN_IDS=" .env 2>/dev/null | cut -d= -f2- | cut -d, -f1)
[ -z "$TOKEN" ] && exit 0

alert() {
    [ -n "$ADMIN" ] && curl -s -m 10 -X POST "https://api.telegram.org/bot$TOKEN/sendMessage" \
        --data-urlencode "chat_id=$ADMIN" --data-urlencode "text=$1" >/dev/null 2>&1
}

# 1) bot process
if ! systemctl --user is-active -q donatefmbot.service; then
    systemctl --user restart donatefmbot.service
    alert "🤖 <b>Watchdog:</b> bot o'lik edi — qayta ishga tushirildi."
fi

# 2) lokal server
if ! curl -s -m 8 -o /dev/null -w "%{http_code}" http://127.0.0.1:8010/health 2>/dev/null | grep -q "^200$"; then
    sleep 10
    if ! curl -s -m 8 -o /dev/null -w "%{http_code}" http://127.0.0.1:8010/health 2>/dev/null | grep -q "^200$"; then
        systemctl --user restart donatefmbot.service
        alert "🤖 <b>Watchdog:</b> lokal server javob bermadi — bot restart qilindi."
    fi
fi

# 3) tashqi tunnel (faqat xabar, URL almashmasligi uchun avtomatik restart yo'q)
URL=$(./venv/bin/python -c "import sys; sys.path.insert(0,'.'); import config; print(config.get_settings().get('webapp_url',''))" 2>/dev/null)
if [ -n "$URL" ]; then
    if ! curl -s -m 15 -o /dev/null -w "%{http_code}" "$URL/health" 2>/dev/null | grep -q "^200$"; then
        echo "$(date -Is) WATCHDOG: tunnel o'lik: $URL" >> logs/watchdog.log
        alert "🌐 <b>Watchdog:</b> WebApp tashqaridan ochilmayapti. Tunnelni tekshiring."
    fi
fi
