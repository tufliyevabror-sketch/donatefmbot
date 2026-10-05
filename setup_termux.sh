#!/data/data/com.termux/files/usr/bin/bash
# Game Shop bot — Termux (Android / telefon) uchun to'liq o'rnatuvchi
# Ishga tushirish:  bash setup_termux.sh
set -e

echo "📲 Game Shop bot — Termux o'rnatuvchi"
echo "====================================="

# 1) Asosiy shebang tuzatish (Termux)
if [ -f stop.sh ]; then
    sed -i '1s|^#!/bin/bash|#!/data/data/com.termux/files/usr/bin/bash|' stop.sh 2>/dev/null || true
fi
if [ -f start.sh ]; then
    sed -i '1s|^#!/bin/bash|#!/data/data/com.termux/files/usr/bin/bash|' start.sh 2>/dev/null || true
fi

# 2) Python va kerakli paketlar
if ! command -v python3 >/dev/null; then
    echo "📦 python o'rnatilmoqda..."
    pkg install -y python
fi

# ngrok — Termux'da eng ishonchli tunnel (cloudflared ARM'da og'ir)
install_ngrok() {
    echo "🌐 ngrok o'rnatilmoqda (Mini App HTTPS tunnel uchun)..."
    # Birinchi urinish: pkg orqali
    if pkg install -y ngrok 2>/dev/null; then
        command -v ngrok >/dev/null 2>&1 && return 0
    fi
    # Ikkinchi urinish: Yandex yoki boshqa mirror'dan avtomatik o'rnatish emas —
    # foydalanuvchi qo'lda qiladi, chunki ngrok auth-talab qiladi.
    echo "⚠️  ngrok pkg'dan olinmadi. Qo'lda o'rnating:"
    echo "   pkg install wget tar"
    echo "   wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-arm64.tgz"
    echo "   tar -xzf ngrok-v3-stable-linux-arm64.tgz -C \$PREFIX/bin"
    echo "   ngrok config add-authtoken <TOKEN>   # https://dashboard.ngrok.com free token"
    sleep 3
}

if ! command -v ngrok >/dev/null 2>&1; then
    install_ngrok
fi

# cloudflared — alternativ (agar ngrok yo'q bo'lsa)
if ! command -v cloudflared >/dev/null 2>&1; then
    echo "🌐 cloudflared ham yuklanmoqda (zaxira)..."
    pkg install -y cloudflared 2>/dev/null || echo "⚠️  cloudflared pkg'dan olinmadi (ngrok yetarli)"
fi

# 3) Kerakli boshqa paketlar
pkg list-installed 2>/dev/null | grep -q "^openssl" || pkg install -y openssl 2>/dev/null || true
pkg list-installed 2>/dev/null | grep -q "^termux-api" || pkg install -y termux-api 2>/dev/null || echo "⚠️  termux-api o'rnatilmadi"

# 4) venv yaratish (agar yo'q bo'lsa)
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"
if [ ! -x venv/bin/python ]; then
    echo "🏗  venv yaratilmoqda..."
    python3 -m venv venv
    ./venv/bin/pip install -U pip -q
fi

echo "📦 Python paketlari tekshirilmoqda..."
./venv/bin/pip install -q -r requirements.txt
# blackboxprotobuf protobuf==3.10.0 talab qiladi (FlexbaseGFFT esa >=5.26.1).
# Shuning uchun u --no-deps bilan o'rnatiladi: faqat o'z kodini qo'shadi,
# protobuf versiyasini buzmaydi.
./venv/bin/pip install -q --no-deps blackboxprotobuf

chmod +x start.sh stop.sh

echo
echo "✅ Tayyor! Botni ishga tushirish uchun:"
echo "   bash start.sh"
echo "   Loglarni kuzatish: tail -f logs/bot.log"
echo "   To'xtatish:        bash stop.sh"
echo
echo "💡 Eslatma: Termux'da bot doimiy ishlashi uchun:"
echo "   termux-wake-lock      # CPU uyquga ketishini oldini oladi"
echo
echo "🔑 mAgar ngrok ishlatilsa, avval auth token sozlash kerak:"
echo "   ngrok config add-authtoken <TOKEN>"
echo "   (https://dashboard.ngrok.com — bepul token)"
echo
echo "🔗 BotFather'da Mini App URLni yangilashni unutmang"
echo "   (start.sh ishga tushgach logs/ngrok.log yoki logs/bot.log'dan URL oling)"