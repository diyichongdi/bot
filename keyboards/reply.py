from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


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
    builder = InlineKeyboardBuilder()
    for i in [1, 2, 3, 4, 5, 6, 7, 8, 9]:
        builder.button(text=f"「{i}」", callback_data=f"num:{i}")
    builder.button(text="✅ 确认", callback_data="num:confirm")
    builder.button(text="0", callback_data="num:0")
    builder.button(text="🔙", callback_data="num:back")
    builder.adjust(3, 3, 3, 1, 1, 1)
    return builder.as_markup()


def build_recharge_confirm_keyboard(amount: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ 确认充值", callback_data=f"recharge_confirm:{amount}")
    builder.button(text="❌ 取消", callback_data="recharge_cancel")
    return builder.as_markup()


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
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ 确认", callback_data="withdraw_confirm")
    builder.button(text="❌ 取消", callback_data="withdraw_cancel")
    return builder.as_markup()
