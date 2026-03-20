import os
import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

from config import BOT_TOKEN, EXCHANGE_RATE, RECHARGE_ADDRESS, ADMIN_IDS, INITIAL_COINS, POOL_FEE_PERCENT, CASHBACK_PERCENT, LEOPARD_KILL
from database import db
from games import calculate_win, format_result, DiceResult, Bet
from keyboards import build_main_keyboard, build_number_keyboard, build_withdraw_confirm_keyboard, build_back_keyboard

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_order_id() -> str:
    import time
    return f"VP{int(time.time() * 1000)}"


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    is_new = user["total_bet"] == 0 and user["coins"] == INITIAL_COINS
    
    if update.effective_user.username:
        db.update_username(user_id, update.effective_user.username)
    
    username = f"@{update.effective_user.username}" if update.effective_user.username else update.effective_user.first_name or "用户"
    
    await update.message.reply_text(
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
    
    if is_new and ADMIN_IDS:
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=f"🆕 新用户注册\n\n"
                    f"👤 用户: {username}\n"
                    f"🆔 ID: {user['uid']}\n"
                    f"💰 余额: {user['coins']}"
                )
            except Exception:
                pass


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
    await update.message.reply_text(help_text)


async def cmd_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    
    if update.effective_user.username:
        db.update_username(user_id, update.effective_user.username)
    
    username = user.get("username") or f"@{update.effective_user.username}" if update.effective_user.username else update.effective_user.first_name or "用户"
    
    await update.message.reply_text(
        f"💰   账户信息  \n\n"
        f"👤 用户: {username}\n"
        f"🆔 ID: {user['uid']}\n"
        f"💵 余额: {user['coins']} 美元\n\n"
        f"📊   统计  \n"
        f"• 总投注: {user['total_bet']}\n"
        f"• 总赢得: {user['total_win']}\n"
        f"• 总充值: {user['total_recharge']}"
    )


async def cmd_record(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    daily = db.get_daily_stats(user_id, 7)
    
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
    
    await update.message.reply_text(msg)


async def cmd_recharge_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data['state'] = 'recharge_amount'
    context.user_data['recharge_amount'] = ""
    
    msg = await update.message.reply_text(
        "💳   请输入充值金额  \n\n当前输入: 0",
        reply_markup=build_number_keyboard()
    )
    context.user_data['recharge_msg_id'] = msg.message_id
    context.user_data['recharge_chat_id'] = msg.chat_id


async def handle_recharge_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    data = query.data
    current = context.user_data.get('recharge_amount', '')
    
    if data == "num:back":
        if current:
            current = current[:-1]
    elif data == "num:confirm":
        if current and current.lstrip("0"):
            context.user_data['recharge_amount'] = int(current)
            context.user_data['state'] = 'recharge_address'
            msg = await query.message.reply_text(
                f"💳 充值金额: {int(current)}\n\n"
                f"请输入您的充值汇出地址 (USDT TRC20)："
            )
            context.user_data['recharge_msg_id'] = msg.message_id
            return
    elif data.startswith("num:"):
        num = data.split(":")[1]
        if num.isdigit():
            current += num
    
    context.user_data['recharge_amount'] = current
    
    try:
        await context.bot.edit_message_text(
            chat_id=context.user_data['recharge_chat_id'],
            message_id=context.user_data['recharge_msg_id'],
            text="💳   请输入充值金额  \n\n当前输入: " + (current or "0"),
            reply_markup=build_number_keyboard()
        )
    except Exception:
        pass


async def handle_recharge_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message.text or len(update.message.text) < 10:
        await update.message.reply_text("请输入有效的地址：")
        return
    
    address = update.message.text.strip()
    context.user_data['recharge_address'] = address
    context.user_data['state'] = 'recharge_confirm'
    
    await update.message.reply_text(
        f"💳 汇出地址: {address}\n\n"
        f"请选择充值金额按钮继续，或回复任意内容继续"
    )


async def handle_recharge_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    amount = context.user_data.get('recharge_amount', 0)
    
    if not amount:
        await update.message.reply_text("请先输入充值金额")
        return
    
    order_id = generate_order_id()
    usdt_amount = round(amount / EXCHANGE_RATE, 2)
    from datetime import datetime, timedelta
    expire_time = (datetime.now() + timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S")
    
    context.user_data.clear()
    
    await update.message.reply_text(
        f"订单号：{order_id}\n"
        f"汇率：{EXCHANGE_RATE}\n"
        f"支付金额：{usdt_amount} USDT\n"
        f"收款地址 (TRC20)：\n"
        f"```{RECHARGE_ADDRESS}```\n\n"
        f"请在 30 分钟内完成TRC20-USDT转账，转账后点击【我已支付】按钮。\n\n"
        f"订单到期时间：{expire_time}\n\n"
        f"❗️ 请务必使用 TRC20 网络转账，转错网络无法找回。\n"
        f"❗️ 请确保到账【{usdt_amount} USDT】，少转不到账，多转不退。\n"
        f"⚠️ 是到账金额，不是打款金额，交易所打款普遍扣 1U 手续费。\n"
        f"❗️ 请务必在 30 分钟内完成转账，否则订单将失效。\n"
        f"❗️ 转账时请预留足够的 TRX 作为矿工费。\n\n"
        f"❗️ 转账需要链上确认，一般一分钟内到账。"
    )


async def cmd_withdraw_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    
    if user["coins"] < 100:
        await update.message.reply_text(f"❌ 余额不足，最小提现金额为100，当前余额: {user['coins']}")
        return
    
    context.user_data['state'] = 'withdraw_address'
    
    await update.message.reply_text(
        f"💸   提现  \n\n"
        f"当前余额: {user['coins']}\n\n"
        f"请输入您的提现地址 (USDT TRC20)：",
        reply_markup=build_back_keyboard()
    )


async def handle_withdraw_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.text == "🔙 返回":
        context.user_data.clear()
        await cmd_start(update, context)
        return
    
    if not update.message.text or len(update.message.text) < 10:
        await update.message.reply_text("请输入有效的地址：")
        return
    
    context.user_data['withdraw_address'] = update.message.text.strip()
    context.user_data['state'] = 'withdraw_amount'
    
    msg = await update.message.reply_text(
        f"💸   提现  \n\n"
        f"地址: {context.user_data['withdraw_address']}\n\n"
        f"请输入提现金额：",
        reply_markup=build_number_keyboard()
    )
    context.user_data['withdraw_msg_id'] = msg.message_id


async def handle_withdraw_amount_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    data = query.data
    current = context.user_data.get('withdraw_amount', '')
    
    if data == "num:back":
        if current:
            current = current[:-1]
    elif data == "num:confirm":
        if current and current.lstrip("0"):
            context.user_data['withdraw_amount'] = int(current)
            
            amount = context.user_data['withdraw_amount']
            address = context.user_data.get('withdraw_address', '')
            user_id = update.effective_user.id
            user = db.get_user(user_id)
            
            if amount < 100:
                await context.bot.edit_message_text(
                    chat_id=query.message.chat.id,
                    message_id=context.user_data['withdraw_msg_id'],
                    text=f"❌ 最小提现金额为100，当前余额: {user['coins']}",
                    reply_markup=build_number_keyboard()
                )
                return
            
            if amount > user["coins"]:
                await context.bot.edit_message_text(
                    chat_id=query.message.chat.id,
                    message_id=context.user_data['withdraw_msg_id'],
                    text=f"❌ 余额不足！当前余额: {user['coins']}",
                    reply_markup=build_number_keyboard()
                )
                return
            
            usdt_amount = round(amount / EXCHANGE_RATE, 2)
            
            context.user_data['state'] = 'withdraw_confirm'
            
            await context.bot.edit_message_text(
                chat_id=query.message.chat.id,
                message_id=context.user_data['withdraw_msg_id'],
                text=f"📋   提现确认  \n\n"
                f"订单号：{generate_order_id()}\n"
                f"汇率：{EXCHANGE_RATE}\n"
                f"支付金额：{usdt_amount} USDT\n"
                f"收款地址 (TRC20)：\n```{address}```\n\n"
                f"⚠️ 请勿提至交易所，请使用冷钱包",
                reply_markup=build_withdraw_confirm_keyboard()
            )
            return
        return
    elif data.startswith("num:"):
        num = data.split(":")[1]
        if num.isdigit():
            current += num
    
    context.user_data['withdraw_amount'] = current
    
    try:
        await context.bot.edit_message_text(
            chat_id=query.message.chat.id,
            message_id=context.user_data['withdraw_msg_id'],
            text=f"💸   提现  \n\n"
            f"地址: {context.user_data.get('withdraw_address', '')}\n\n"
            f"请输入提现金额：\n\n当前输入: {current or '0'}",
            reply_markup=build_number_keyboard()
        )
    except Exception:
        pass


async def handle_withdraw_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    address = context.user_data.get('withdraw_address', '')
    amount = context.user_data.get('withdraw_amount', 0)
    user_id = query.from_user.id
    
    if query.data == "withdraw_confirm":
        db.update_coins(user_id, -amount)
        
        await query.message.edit_text(
            f"✅ 提现申请已提交\n\n"
            f"💳 地址: {address}\n"
            f"💰 金额: {amount}\n\n"
            f"⏰ 人工确认中，3个标准小时内到账"
        )
    else:
        await query.message.edit_text("❌ 提现已取消")
    
    context.user_data.clear()


async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text
    
    if "余额" in text:
        await cmd_balance(update, context)
    elif "记录" in text:
        await cmd_record(update, context)
    elif "帮助" in text:
        await cmd_help(update, context)
    elif "💳" in text or "充值" in text:
        await cmd_recharge_start(update, context)
    elif "💸" in text or "提现" in text:
        await cmd_withdraw_start(update, context)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_state = context.user_data.get('state', '')
    
    if user_state == 'recharge_amount':
        await handle_recharge_callback(update, context)
    elif user_state == 'withdraw_amount':
        await handle_withdraw_amount_callback(update, context)
    elif user_state == 'withdraw_confirm':
        await handle_withdraw_confirm_callback(update, context)
    elif data and data.startswith("num:"):
        if 'recharge_amount' in str(context.user_data.get('state', '')):
            await handle_recharge_callback(update, context)
        else:
            await handle_withdraw_amount_callback(update, context)
    elif data and data.startswith("withdraw_"):
        await handle_withdraw_confirm_callback(update, context)


def parse_bet(text: str) -> Bet | None:
    import re
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


async def handle_bet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message.text:
        return
    
    text = update.message.text.strip()
    text_lower = text.lower()
    user_id = update.effective_user.id
    
    if any(cmd in text for cmd in ["/start", "/help", "/balance", "/充值", "/提现", "/记录"]):
        return
    
    if "💳" in text or "💰" in text or "📊" in text or "🎰" in text or "💸" in text:
        return
    
    bet = parse_bet(text_lower)
    if not bet:
        return
    
    user = db.get_user(user_id)
    if user["coins"] < bet.amount:
        await update.message.reply_text(f"余额不足！当前余额: {user['coins']}")
        return
    
    db.update_coins(user_id, -bet.amount)
    db.add_bet(user_id, bet.amount)
    
    msg1 = await update.message.reply_dice(emoji="🎲")
    msg2 = await update.message.reply_dice(emoji="🎲")
    msg3 = await update.message.reply_dice(emoji="🎲")
    
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
        await update.message.reply_text(
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
        await update.message.reply_text(
            f"{result_text}\n\n"
            f"❌   未中奖  \n"
            f"• 反水: +{cashback}\n"
            f"• 余额: {db.get_balance(user_id)}"
        )


def main() -> None:
    token = os.environ.get("BOT_TOKEN", BOT_TOKEN)
    port = int(os.environ.get("PORT", "8000"))
    webhook_url = os.environ.get("WEBHOOK_URL", "")
    
    application = Application.builder().token(token).build()
    
    def is_command(text: str) -> bool:
        return text and text.startswith("/")
    
    async def handle_all_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        state = context.user_data.get('state', '')
        
        if state == 'recharge_address':
            await handle_recharge_address(update, context)
        elif state == 'recharge_confirm':
            await handle_recharge_confirm(update, context)
        elif state == 'withdraw_address':
            await handle_withdraw_address(update, context)
        elif state == 'withdraw_amount':
            await handle_withdraw_address(update, context)
        elif state == 'withdraw_confirm':
            pass
        else:
            await handle_button(update, context)
            await handle_bet(update, context)
    
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("help", cmd_help))
    application.add_handler(CommandHandler("balance", cmd_balance))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^/记录$"), cmd_record))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^/充值"), cmd_recharge_start))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^/提现"), cmd_withdraw_start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_all_text))
    
    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path="webhook",
        webhook_url=webhook_url or None,
    )


if __name__ == "__main__":
    main()
