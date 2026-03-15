import random
from dataclasses import dataclass


@dataclass
class Bet:
    bet_type: str
    amount: int
    odds: int


@dataclass
class DiceResult:
    d1: int
    d2: int
    d3: int

    @property
    def total(self) -> int:
        return self.d1 + self.d2 + self.d3

    @property
    def is_big(self) -> bool:
        return 11 <= self.total <= 17

    @property
    def is_small(self) -> bool:
        return 4 <= self.total <= 10

    @property
    def is_odd(self) -> bool:
        return self.total % 2 == 1

    @property
    def is_even(self) -> bool:
        return self.total % 2 == 0

    @property
    def is_leopard(self) -> bool:
        return self.d1 == self.d2 == self.d3

    @property
    def is_pair(self) -> bool:
        return len(set([self.d1, self.d2, self.d3])) == 2

    @property
    def is_straight(self) -> bool:
        nums = sorted([self.d1, self.d2, self.d3])
        return nums == [1, 2, 3] or nums == [2, 3, 4] or nums == [3, 4, 5] or nums == [4, 5, 6]

    @property
    def is_dragon(self) -> bool:
        return self.d1 > self.d3

    @property
    def is_tiger(self) -> bool:
        return self.d1 < self.d3

    @property
    def is_tie(self) -> bool:
        return self.d1 == self.d3

    @property
    def first_die(self) -> int:
        return self.d1

    @property
    def third_die(self) -> int:
        return self.d3


def roll_dice() -> DiceResult:
    return DiceResult(
        d1=random.randint(1, 6),
        d2=random.randint(1, 6),
        d3=random.randint(1, 6),
    )


def calculate_win(bet_type: str, amount: int, result: DiceResult, leopard_kill: bool = False) -> tuple[bool, int]:
    win = False
    win_amount = 0
    bt = bet_type.lower()

    if bt in ("大", "big", "da"):
        if result.is_big and not result.is_leopard:
            win = True
            win_amount = amount
    elif bt in ("小", "small", "xiao"):
        if result.is_small and not result.is_leopard:
            win = True
            win_amount = amount
    elif bt in ("单", "odd", "dan"):
        if result.is_odd and not result.is_leopard:
            win = True
            win_amount = amount
    elif bt in ("双", "even", "shuang"):
        if result.is_even and not result.is_leopard:
            win = True
            win_amount = amount
    elif bt in ("豹", "leopard", "baozi"):
        if result.is_leopard:
            win = True
            win_amount = amount * 3
    elif bt in ("对子", "pair"):
        if result.is_pair:
            win = True
            win_amount = amount * 2
    elif bt in ("顺子", "straight"):
        if result.is_straight:
            win = True
            win_amount = amount * 3
    elif bt in ("龙", "dragon", "long"):
        if result.is_dragon:
            win = True
            win_amount = amount
    elif bt in ("虎", "tiger", "hu"):
        if result.is_tiger:
            win = True
            win_amount = amount
    elif bt in ("和", "tie", "he"):
        if result.is_tie:
            win = True
            win_amount = amount * 9
    elif bt.startswith(("3", "4", "5", "6")) and (bt.endswith(("豹", "b")) or "豹" in bt or bt.endswith("b")):
        try:
            num = int(bt[0])
            if result.is_leopard and result.d1 == num:
                win = True
                win_amount = amount * 30
        except (ValueError, IndexError):
            pass
    elif bt in ("大龙", "dl", "big dragon"):
        if result.is_dragon and result.is_big and not result.is_leopard:
            win = True
            win_amount = amount * 3
    elif bt in ("小龙", "xl", "small dragon"):
        if result.is_dragon and result.is_small and not result.is_leopard:
            win = True
            win_amount = amount * 3
    elif bt in ("大虎", "dh", "big tiger"):
        if result.is_tiger and result.is_big and not result.is_leopard:
            win = True
            win_amount = amount * 3
    elif bt in ("小虎", "xh", "small tiger"):
        if result.is_tiger and result.is_small and not result.is_leopard:
            win = True
            win_amount = amount * 3
    elif bt in ("大单", "dd", "big odd"):
        if result.is_big and result.is_odd:
            win = True
            win_amount = amount * 3
    elif bt in ("大双", "ds", "big even"):
        if result.is_big and result.is_even:
            win = True
            win_amount = amount * 3
    elif bt in ("小单", "xd", "small odd"):
        if result.is_small and result.is_odd:
            win = True
            win_amount = amount * 3
    elif bt in ("小双", "xs", "small even"):
        if result.is_small and result.is_even:
            win = True
            win_amount = amount * 3
    elif bt.startswith(("z", "总", "sum", "total")):
        try:
            target_str = bt.replace("z", "").replace("总", "").replace("sum", "").replace("total", "").replace("/", "")
            target = int(target_str)
            if 4 <= target <= 17:
                if result.total == target:
                    win = True
                    win_amount = amount * 20
        except ValueError:
            pass
    elif bt.replace("/", "").isdigit():
        try:
            target = int(bt.replace("/", ""))
            if 4 <= target <= 17:
                if result.total == target:
                    win = True
                    win_amount = amount * 20
        except ValueError:
            pass

    combo_bets = ("大", "小", "单", "双", "big", "small", "odd", "even", "da", "xiao", "dan", "shuang",
                 "大单", "大双", "小单", "小双", "dd", "ds", "xd", "xs", "big odd", "big even", "small odd", "small even")
    leopard_bets = ("豹", "baozi", "leopard")

    if result.is_leopard:
        is_leopard_bet = any(bt == lb or bt.startswith(lb) for lb in leopard_bets)
        if not is_leopard_bet:
            if leopard_kill:
                win = False
                win_amount = 0
            elif bt in combo_bets:
                win = False
                win_amount = 0

    return win, win_amount


def format_result(result: DiceResult) -> str:
    dice_emoji = {1: "⚀", 2: "⚁", 3: "⚂", 4: "⚃", 5: "⚄", 6: "⚅"}
    emoji = f"{dice_emoji[result.d1]}{dice_emoji[result.d2]}{dice_emoji[result.d3]}"
    total_type = "大" if result.is_big else "小"
    if result.is_leopard:
        total_type = f"豹子 ({result.d1})"
    elif result.is_straight:
        total_type = "顺子"
    elif result.is_pair:
        total_type = "对子"
    return f"🎲 开奖: {emoji} = {result.total} ({total_type})"
