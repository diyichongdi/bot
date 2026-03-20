from telegram import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


def build_main_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="💰 余额"),
                KeyboardButton(text="📊 记录"),
            ],
            [
                KeyboardButton(text="💳 充值"),
                KeyboardButton(text="💸 提现"),
            ],
            [
                KeyboardButton(text="🎰 帮助"),
            ],
        ],
        resize_keyboard=True,
    )
    return keyboard


def build_number_keyboard() -> InlineKeyboardMarkup:
    keyboard = []
    row = []
    for i in range(1, 10):
        row.append(InlineKeyboardButton(text=f"「{i}」", callback_data=f"num:{i}"))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    keyboard.append(row)
    keyboard.append([InlineKeyboardButton(text="✅ 确认", callback_data="num:confirm")])
    keyboard.append([InlineKeyboardButton(text="0", callback_data="num:0"), InlineKeyboardButton(text="🔙", callback_data="num:back")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def build_recharge_confirm_keyboard(amount: int) -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text="✅ 确认充值", callback_data=f"recharge_confirm:{amount}")],
        [InlineKeyboardButton(text="❌ 取消", callback_data="recharge_cancel")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def build_back_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🔙 返回"),
            ],
        ],
        resize_keyboard=True,
    )
    return keyboard


def build_withdraw_confirm_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text="✅ 确认", callback_data="withdraw_confirm")],
        [InlineKeyboardButton(text="❌ 取消", callback_data="withdraw_cancel")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
