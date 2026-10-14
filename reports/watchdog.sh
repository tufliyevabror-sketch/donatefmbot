#!/bin/bash
# DonateFM watchdog — har 5 daqiqada: bot + WebApp + disk + zaxira sog'lommi?
# Muammo bo'lsa: botni o'zi restart qiladi, admin'ga Telegram'dan xabar yuboradi.
# Ogohlantirishlar cooldown bilan: tunnel 1s/soat, disk 1s/12 soat, zaxira 1s/6 soat.
BASE=/home/abror69/donatefmbot
cd "$BASE" || exit 0

TOKEN=$(grep -E "^BOT_TOKEN=" .env 2>/dev/null | cut -d= -f2-)
ADMIN=$(grep -E "^ADMIN_IDS=" .env 2>/dev/null | cut -d= -f2- | cut -d, -f1)
[ -z "$TOKEN" ] && exit 0

alert() {
    if [ -n "$ADMIN" ]; then
        curl -s -m 10 -X POST "https://api.telegram.org/bot$TOKEN/sendMessage" \
            --data-urlencode "chat_id=$ADMIN" --data-urlencode "text=$1" >/dev/null 2>&1 || true
    fi
    return 0
}

# cooldown_alert <state_file> <seconds> <text>
cooldown_alert() {
    local f="logs/.wc_$1" now last
    now=$(date +%s)
    last=0
    [ -f "$f" ] && last=$(cat "$f" 2>/dev/null || echo 0)
    case "$last" in ''|*[!0-9]*) last=0 ;; esac
    if [ $((now - last)) -ge "$2" ]; then
        alert "$3"
        echo "$now" > "$f" 2>/dev/null || true
    fi
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
        cooldown_alert tunnel 3600 "🌐 <b>Watchdog:</b> WebApp tashqaridan ochilmayapti. Tunnelni tekshiring."
    fi
fi

# 4) disk (>=90% -> xabar, 12 soatda 1 marta)
DISK_PCT=$(df -P . 2>/dev/null | awk 'NR==2 {gsub("%","",$5); print $5}')
case "$DISK_PCT" in
    ''|*[!0-9]*) ;;
    *)
        if [ "$DISK_PCT" -ge 90 ]; then
            cooldown_alert disk 43200 "⚠️ <b>Watchdog:</b> Disk to'lgan: ${DISK_PCT}% ($BASE). Eski fayllarni tozalang."
        fi
        ;;
esac

# 5) zaxira yangiligi (eng yangi backup 6 soatdan eski bo'lsa)
LATEST=$(ls -t data/backups/*.db 2>/dev/null | head -1)
if [ -z "$LATEST" ]; then
    cooldown_alert backup 21600 "🗄 <b>Watchdog:</b> data/backups/ da hech qanday zaxira yo'q!"
else
    AGE=$(( $(date +%s) - $(stat -c %Y "$LATEST" 2>/dev/null || echo 0) ))
    if [ "$AGE" -gt 21600 ]; then
        H=$((AGE / 3600))
        cooldown_alert backup 21600 "🗄 <b>Watchdog:</b> Eng yangi zaxira ${H} soat oldingi — backup ishlamayapti."
    fi
fi

exit 0
