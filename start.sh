#!/bin/bash
set -e

git clone https://github.com/diyichongdi/bot.git /app
cd /app/kuaisan_bot
pip install -r requirements.txt
python main.py
