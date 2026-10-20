#!/usr/bin/env bash
# [29exop] GitHub Sync & Update Script for DonateFM Bot
# Both Bot and WebApp run on the same free server, syncing with GitHub.

echo "[29exop] Syncing with GitHub..."
cd /home/abror69/donatefmbot

# Check if git is initialized
if [ ! -d .git ]; then
    git init
    echo "Initialized git repository."
fi

# Check for uncommitted local changes
git status

echo "[29exop] To pull latest updates from GitHub repository:"
echo "    git pull origin main"
echo ""
echo "[29exop] To push local improvements to GitHub:"
echo "    git add ."
echo "    git commit -m 'Update DonateFM Bot'"
echo "    git push origin main"
echo ""
echo "[29exop] Deployment architecture:"
echo "    - Web App + Telegram Bot run together on the same free server (Docker / FastAPI)."
echo "    - Custom .com domain can be pointed to the server for the Web App."
echo "    - Bot runs continuously in polling/webhook mode."
