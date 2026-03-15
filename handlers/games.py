import re
from aiogram import Dispatcher, Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from config import POOL_FEE_PERCENT, CASHBACK_PERCENT, ADMIN_IDS, RECHARGE_ADDRESS, LEOPARD_KILL
from database import db
from games import calculate_win, format_result, DiceResult, Bet
from keyboards import build_main_keyboard, build_number_keyboard

router = Router()


class RechargeState(StatesGroup):
    entering_amount = State()
    entering_address = State()


PENDING_BETS: dict[int, Bet] = {}


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    user = db.get_user(message.from_user.id)
    if message.from_user.username:
        db.update_username(message.from_user.id, message.from_user.username)
    
    username = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name or "用户"
    await message.answer(
        f"🎰 欢迎来到骰子游戏！\n\n"
        f"👤 用户: {username}\n"
        f"🆔 ID: {user['uid']}\n"
        f"💰 余额: {user['coins']} 美元\n\n"
        f"下注格式：\n"
        f"• 大100 / 小100 / 单100 / 双100\n"
        f"• 豹100 / 对子100 / 顺子50\n"
        f"• 3豹100 / 4豹200 (指定豹子)\n\n"
        f"💡 发送 /help 查看完整规则",
        reply_markup=build_main_keyboard(),
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    help_text = """
🎰   快三游戏规则

  基本投注：
• 🟧 大/小 - 4-10小 / 11-17大 (1:1)
• ✋ 单/双 - 单数/双数 (1:1)

  特殊投注：  
• 🐲 龙 - 第1个骰子 > 第3个 (1:1)
• 🐯 虎 - 第1个骰子 < 第3个 (1:1)
• ⚖️ 和 - 第1个 = 第3个 (1:9)
• 🎰 豹子 - 三同号 (1:3)
• 💎 对子 - 两同号 (1:2)
• 🔢 顺子 - 连续号 (1:3)

  指定豹子：  
• 3豹/4豹/5豹/6豹 (1:30)

  组合投注：  
• 大龙/小龙/大虎/小虎 (1:3)
• 大单/大双/小单/小双 (1:3)

  总和投注：  
• 4-17 总点数 (1:20)
• 格式: 4/100

━━━━━━━━━━━━━━
💦 反水: 0.5%  💵 抽佣: 0.5%
"""
    await message.answer(help_text)


@router.message(Command("balance"))
async def cmd_balance(message: Message) -> None:
    user = db.get_user(message.from_user.id)
    if message.from_user.username:
        db.update_username(message.from_user.id, message.from_user.username)
    
    username = user.get("username") or f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name or "用户"
    await message.answer(
        f"💰   账户信息  \n\n"
        f"👤 用户: {username}\n"
        f"🆔 ID: {user['uid']}\n"
        f"💵 余额: {user['coins']} 美元\n\n"
        f"📊   统计  \n"
        f"• 总投注: {user['total_bet']}\n"
        f"• 总赢得: {user['total_win']}\n"
        f"• 总充值: {user['total_recharge']}"
    )


@router.message(Command("记录"))
@router.message(F.text == "💰 余额")
@router.message(F.text == "📊 记录")
@router.message(F.text == "🎰 帮助")
async def handle_buttons(message: Message) -> None:
    text = message.text
    
    if text and "余额" in text:
        await cmd_balance(message)
    elif text and "记录" in text:
        user = db.get_user(message.from_user.id)
        daily = db.get_daily_stats(message.from_user.id, 7)
        
        net = user['total_win'] - (user['total_bet'] - user['total_win'])
        
        msg = "📊   游戏记录  \n\n"
        msg += f"• 总投注: {user['total_bet']}\n"
        msg += f"• 总赢得: {user['total_win']}\n"
        msg += f"• 总充值: {user['total_recharge']}\n"
        msg += f"• 净盈利: {'+' if net > 0 else ''}{net}\n\n"
        
        if daily:
            msg += "📅   近期统计  \n"
            for date, stats in sorted(daily.items(), reverse=True)[:7]:
                day_net = stats["win"] - stats["bet"]
                date_str = date[5:]
                msg += f"{date_str} | 投注:{stats['bet']} 赢得:{stats['win']} 净:{'+' if day_net > 0 else ''}{day_net}\n"
        
        await message.answer(msg)
    elif text and "帮助" in text:
        await cmd_help(message)


@router.message(F.text == "💳 充值")
async def handle_recharge_button(message: Message, state: FSMContext) -> None:
    await state.set_state(RechargeState.entering_amount)
    await state.update_data(amount="", message_id=None)
    msg = await message.answer(
        "💳   请输入充值金额  \n\n当前输入: 0",
        reply_markup=build_number_keyboard()
    )
    await state.update_data(message_id=msg.message_id)


@router.message(Command("充值"))
async def cmd_recharge_start(message: Message, state: FSMContext) -> None:
    await handle_recharge_button(message, state)


@router.callback_query()
async def handle_number_callback(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    current_amount = data.get("amount", "")
    message_id = data.get("message_id")
    
    if callback.data == "num:back":
        if current_amount:
            current_amount = current_amount[:-1]
    elif callback.data == "num:confirm":
        if current_amount and current_amount.lstrip("0"):
            amount = int(current_amount)
            await state.set_state(RechargeState.entering_address)
            await state.update_data(amount=amount)
            await callback.message.edit_text(
                f"💳   充值金额: {amount}  \n\n"
                f"请输入您的充值汇出地址 (USDT TRC20)："
            )
            await callback.answer()
            return
        await callback.answer()
        return
    elif callback.data.startswith("num:"):
        num = callback.data.split(":")[1]
        if num.isdigit():
            current_amount += num
    
    await state.update_data(amount=current_amount)
    
    if message_id:
        try:
            await bot.edit_message_text(
                chat_id=callback.message.chat.id,
                message_id=message_id,
                text="💳   请输入充值金额  \n\n当前输入: " + (current_amount or "0"),
                reply_markup=build_number_keyboard()
            )
        except Exception:
            pass
    
    await callback.answer()


@router.message(RechargeState.entering_address)
async def handle_recharge_address(message: Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("请输入有效的地址：")
        return
    
    address = message.text.strip()
    
    data = await state.get_data()
    amount = data.get("amount", 0)
    
    await state.clear()
    
    await message.answer(
        f"📋   充值信息确认  \n\n"
        f"💳 汇出地址: {address}\n"
        f"💰 充值金额: {amount} 美元\n\n"
        f"  请向以下地址转账USDT：  \n"
        f"{RECHARGE_ADDRESS}\n\n"
        f"⚠️ 转账完成后，等待0~15分钟到账！"
    )


@router.message(Command("recharge"))
async def cmd_recharge_start(message: Message, state: FSMContext) -> None:
    await handle_recharge_button(message, state)


@router.message(Command("give"))
async def cmd_give(message: Message) -> None:
    args = message.text.split()
    if len(args) < 3:
        await message.answer("用法: /give <用户ID> <数量>")
        return
    
    try:
        target_id = int(args[1])
        amount = int(args[2])
        if amount <= 0:
            await message.answer("金额必须大于0")
            return
    except ValueError:
        await message.answer("请输入有效的数字")
        return
    
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        await message.answer("只有管理员可以赠送美元")
        return
    
    db.recharge(target_id, amount)
    await message.answer(f"✅ 成功给用户 {target_id} 充值 {amount} 美元")


@router.message(Command("setting"))
async def cmd_setting(message: Message) -> None:
    if message.from_user.id not in ADMIN_IDS:
        return
    
    text = """
⚙️   管理员设置

当前配置：
"""
    await message.answer(text)


@router.message()
async def handle_bet(message: Message) -> None:
    if not message.text:
        return
    
    text = message.text.strip()
    text_lower = text.lower()
    user_id = message.from_user.id
    
    if any(cmd in text for cmd in ["/start", "/help", "/balance", "/recharge", "/give", "/记录", "/充值", "/setting"]):
        return
    
    if "💳" in text or "充值" in text:
        return
    
    bet = parse_bet(text_lower)
    if not bet:
        await message.answer("无效的下注格式，请查看 /help")
        return
    
    user = db.get_user(user_id)
    if user["coins"] < bet.amount:
        await message.answer(f"余额不足！当前余额: {user['coins']}")
        return
    
    db.update_coins(user_id, -bet.amount)
    db.add_bet(user_id, bet.amount)
    
    msg1 = await message.answer_dice(emoji="🎲")
    msg2 = await message.answer_dice(emoji="🎲")
    msg3 = await message.answer_dice(emoji="🎲")
    
    result = DiceResult(
        d1=msg1.dice.value if msg1.dice else 1,
        d2=msg2.dice.value if msg2.dice else 1,
        d3=msg3.dice.value if msg3.dice else 1,
    )
    
    win, win_amount = calculate_win(bet.bet_type, bet.amount, result, LEOPARD_KILL)
    
    is_combo = bet.bet_type in ("大", "小", "单", "双", "大单", "大双", "小单", "小双", "大龙", "小龙", "大虎", "小虎")
    is_leopard_or_straight = result.is_leopard or result.is_straight
    
    if is_combo and is_leopard_or_straight:
        pool_fee = 0
    else:
        pool_fee = int(win_amount * POOL_FEE_PERCENT / 100) if win_amount > 0 else 0
    
    net_win = win_amount - pool_fee
    
    if win:
        total_return = bet.amount + net_win
        db.update_coins(user_id, total_return)
        db.add_win(user_id, net_win)
        
        result_text = format_result(result)
        await message.answer(
            f"{result_text}\n\n"
            f"🎉   恭喜中奖！  \n"
            f"• 赢得: +{net_win}\n"
            f"• 抽佣: -{pool_fee}\n"
            f"• 余额: {db.get_balance(user_id)}"
        )
    else:
        if is_combo and is_leopard_or_straight:
            cashback = 0
        else:
            cashback = int(bet.amount * CASHBACK_PERCENT / 100)
        db.update_coins(user_id, cashback)
        
        result_text = format_result(result)
        await message.answer(
            f"{result_text}\n\n"
            f"❌   未中奖  \n"
            f"• 反水: +{cashback}\n"
            f"• 余额: {db.get_balance(user_id)}"
        )


def parse_bet(text: str) -> Bet | None:
    text = text.strip().lower().replace(" ", "")
    
    patterns = [
        (r"^(大|小|单|双|龙|虎|和|豹|对子|顺子|大龙|小龙|大虎|小虎|单龙|双龙|单虎|双虎|大单|大双|小单|小双|dl|xl|dh|xh|dd|ds|xd|xs|sl|sh|big|small|odd|even|dragon|tiger|tie|leopard|pair|straight|da|xiao|dan|shuang|long|hu|he|baozi)(\d+)$", 1, 2),
        (r"^(\d)(豹|b)(\d+)$", 1, 3),
        (r"^(z|总|sum|total)(\d+)/(\d+)$", 1, 3),
        (r"^(\d+)/(\d+)$", 1, 2),
    ]
    
    for pattern, bet_type_group, amount_group in patterns:
        match = re.match(pattern, text)
        if match:
            bet_type = match.group(bet_type_group)
            amount = int(match.group(amount_group))
            
            if "豹" in bet_type or bet_type.endswith("b"):
                bet_type = "3豹" if bet_type.startswith("3") else bet_type
            if bet_type.isdigit():
                bet_type = f"{bet_type}豹"
            
            return Bet(bet_type=bet_type, amount=amount, odds=1)
    
    return None


def register_handlers(dp: Dispatcher) -> None:
    dp.include_router(router)
