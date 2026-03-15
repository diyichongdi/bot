import os
from pathlib import Path

BASE_DIR = Path(__file__).parent

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8650899994:AAGhaCD4hXzVg-CZvKdTqQ4OvRvJ288rJ7k")
GROUP_ID = int(os.environ.get("GROUP_ID", "0"))
ADMIN_IDS = [int(x) for x in os.environ.get("ADMIN_IDS", "").split(",") if x]

INITIAL_COINS = int(os.environ.get("INITIAL_COINS", "1000"))
MIN_BET = int(os.environ.get("MIN_BET", "1"))
MAX_BET = int(os.environ.get("MAX_BET", "100000"))

POOL_FEE_PERCENT = float(os.environ.get("POOL_FEE_PERCENT", "0.5"))
CASHBACK_PERCENT = float(os.environ.get("CASHBACK_PERCENT", "0.5"))

RECHARGE_ADDRESS = os.environ.get("RECHARGE_ADDRESS", "TCBK7w8ieXQTwY47m6cMGKAVMMscLuCfvC")

EXCHANGE_RATE = float(os.environ.get("EXCHANGE_RATE", "6.93"))

LEOPARD_KILL = os.environ.get("LEOPARD_KILL", "false").lower() == "true"

ROUND_DURATION = int(os.environ.get("ROUND_DURATION", "120"))
