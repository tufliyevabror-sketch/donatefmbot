#!/usr/bin/env bash
# [29exop] DonateFM Bot - Production Deployment & Git Sync Script

echo "[29exop] DonateFM Bot deployment helper..."
cd /home/abror69/donatefmbot

echo "[1] Checking git status..."
git status

echo "[2] Preparing git commit for latest changes..."
git add -A
git commit -m "Auto-update: production deployment prep ($(date +'%Y-%m-%d %H:%M:%S'))" || echo "No changes to commit"

echo "[3] Environment & Docker check..."
if [ -f Dockerfile ]; then
    echo "Dockerfile is ready."
fi

echo "[4] To deploy to a free server (Koyeb/Render/Hugging Face) with .com domain:"
echo "    - Push this repository to GitHub."
echo "    - Connect your GitHub repo to your free hosting provider."
echo "    - Add your BOT_TOKEN and ADMIN_IDS in environment variables."
echo "    - Point your .com domain (CNAME) to your hosting URL."
echo "[29exop] Ready for production."
