import json
from datetime import datetime, timedelta

from config import BASE_DIR, INITIAL_COINS

DB_FILE = BASE_DIR / "database.json"


class Database:
    def __init__(self):
        self.data: dict[int, dict] = {}
        self.user_count = 0
        self.load()

    def load(self) -> None:
        if DB_FILE.exists():
            with open(DB_FILE, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        self.user_count = len(self.data)

    def save(self) -> None:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def get_user(self, user_id: int) -> dict:
        if user_id not in self.data:
            self.user_count += 1
            self.data[user_id] = {
                "id": user_id,
                "uid": self.user_count,
                "username": "",
                "coins": INITIAL_COINS,
                "total_bet": 0,
                "total_win": 0,
                "total_recharge": 0,
                "total_withdraw": 0,
                "recharge_address": "",
                "daily_stats": {},
            }
            self.save()
        return self.data[user_id]

    def update_username(self, user_id: int, username: str) -> None:
        user = self.get_user(user_id)
        if not user.get("username") and username:
            user["username"] = username
            self.save()

    def update_coins(self, user_id: int, amount: int) -> None:
        user = self.get_user(user_id)
        user["coins"] += amount
        self.save()

    def add_bet(self, user_id: int, amount: int) -> None:
        user = self.get_user(user_id)
        user["total_bet"] += amount
        self._update_daily_stat(user, amount, 0)
        self.save()

    def add_win(self, user_id: int, amount: int) -> None:
        user = self.get_user(user_id)
        user["total_win"] += amount
        self._update_daily_stat(user, 0, amount)
        self.save()

    def _update_daily_stat(self, user: dict, bet: int, win: int) -> None:
        today = datetime.now().strftime("%Y-%m-%d")
        if "daily_stats" not in user:
            user["daily_stats"] = {}
        if today not in user["daily_stats"]:
            user["daily_stats"][today] = {"bet": 0, "win": 0}
        user["daily_stats"][today]["bet"] += bet
        user["daily_stats"][today]["win"] += win

    def get_daily_stats(self, user_id: int, days: int = 7) -> dict:
        user = self.get_user(user_id)
        daily = user.get("daily_stats", {})
        result = {}
        for i in range(days):
            d = datetime.now() - timedelta(days=i)
            date_str = d.strftime("%Y-%m-%d")
            if date_str in daily:
                result[date_str] = daily[date_str]
        return result

    def recharge(self, user_id: int, amount: int) -> None:
        user = self.get_user(user_id)
        user["coins"] += amount
        user["total_recharge"] += amount
        self.save()

    def get_balance(self, user_id: int) -> int:
        user = self.get_user(user_id)
        return user["coins"]

    def get_user_by_uid(self, uid: int) -> dict | None:
        for user in self.data.values():
            if user.get("uid") == uid:
                return user
        return None

    def get_user_by_username(self, username: str) -> dict | None:
        username_lower = username.lower().replace("@", "")
        for user in self.data.values():
            if user.get("username", "").lower() == username_lower:
                return user
        return None


db = Database()
