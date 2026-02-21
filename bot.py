import logging
import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Import database functions
from bingo_db import (
    get_user_by_telegram_id, create_user, get_user_balance,
    buy_card, get_all_cards_with_status, get_user_cards,
    get_called_numbers, check_card_winner, handle_winner,
    get_cardboard_as_grid, reset_round, set_card_price,
    admin_stats, request_deposit, get_pending_deposits,
    approve_deposit, request_withdrawal, get_pending_withdrawals,
    approve_withdrawal
)

# ========== CONFIGURATION ==========
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6835994100"))
WEB_APP_URL = os.getenv("WEB_APP_URL", "https://your-app.up.railway.app/")  # Root URL of your Flask app

# Enable logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== USER COMMANDS ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db_user = get_user_by_telegram_id(user.id)
    if not db_user:
        create_user(user.id, user.username or "Unknown")
        await update.message.reply_text("Welcome! You are now registered.")
    else:
        await update.message.reply_text("Welcome back!")

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bal = get_user_balance(update.effective_user.id)
    await update.message.reply_text(f"Your balance: {bal} ETB")

async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cards = get_all_cards_with_status()
    # Show only first 20 available cards (you can implement pagination)
    keyboard = []
    count = 0
    for card in cards:
        if not card['taken']:
            keyboard.append([InlineKeyboardButton(f"Card {card['id']}", callback_data=f"buy_{card['id']}")])
            count += 1
            if count >= 20:
                break
    if not keyboard:
        await update.message.reply_text("No cards available.")
        return
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Choose a card to buy:", reply_markup=reply_markup)

async def buy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith("buy_"):
        card_id = int(data.split("_")[1])
        success, msg = buy_card(update.effective_user.id, card_id)
        await query.edit_message_text(msg)

async def mycards(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cards = get_user_cards(update.effective_user.id)
    if not cards:
        await update.message.reply_text("You have no cards.")
    else:
        await update.message.reply_text(f"Your cards: {', '.join(map(str, cards))}")

async def called(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nums = get_called_numbers()
    if nums:
        await update.message.reply_text(f"Called numbers: {', '.join(map(str, nums))}")
    else:
        await update.message.reply_text("No numbers called yet.")

async def view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cards = get_user_cards(update.effective_user.id)
    if not cards:
        await update.message.reply_text("You have no cards.")
        return
    card_id = cards[0]   # For simplicity, show the first card
    web_app_url = f"{WEB_APP_URL}?card={card_id}"
    keyboard = [[InlineKeyboardButton("View My Card", web_app=WebAppInfo(url=web_app_url))]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Click below to view your bingo card:", reply_markup=reply_markup)

async def web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = json.loads(update.effective_message.web_app_data.data)
    action = data.get('action')
    if action == 'win':
        card_id = data.get('cardId')
        user_id = update.effective_user.id
        # Verify user owns this card
        user_cards = get_user_cards(user_id)
        if card_id not in user_cards:
            await update.message.reply_text("You don't own this card.")
            return
        called = get_called_numbers()
        card_grid = get_cardboard_as_grid(card_id)
        if card_grid and check_card_winner(card_grid, called):
            result = handle_winner(user_id)
            await update.message.reply_text(result)
        else:
            await update.message.reply_text("Not a winning card yet.")

# ========== DEPOSIT COMMANDS ==========
async def deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Usage: /deposit <amount> <transaction_ref>
    try:
        amount = int(context.args[0])
        ref = context.args[1]
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /deposit <amount> <transaction_ref>")
        return
    msg = request_deposit(update.effective_user.id, amount, ref)
    await update.message.reply_text(msg)

# ========== WITHDRAWAL COMMANDS ==========
async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Usage: /withdraw <amount> <method> <account>
    try:
        amount = int(context.args[0])
        method = context.args[1]
        account = ' '.join(context.args[2:])
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /withdraw <amount> <method> <account>")
        return
    msg = request_withdrawal(update.effective_user.id, amount, method, account)
    await update.message.reply_text(msg)

# ========== ADMIN COMMANDS ==========
async def admin_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Unauthorized.")
        return
    msg = reset_round(update.effective_user.id)
    await update.message.reply_text(msg)

async def admin_setprice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Unauthorized.")
        return
    try:
        new_price = int(context.args[0])
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /setprice <new_price>")
        return
    msg = set_card_price(update.effective_user.id, new_price)
    await update.message.reply_text(msg)

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Unauthorized.")
        return
    stats = admin_stats()
    text = (
        f"📊 Admin Statistics\n"
        f"Total users: {stats['total_users']}\n"
        f"Total deposits: {stats['total_deposits']} ETB\n"
        f"Current prize pool: {stats['current_prize_pool']} ETB\n"
        f"Total rounds: {stats['total_rounds']}\n"
        f"House earnings: {stats['total_house_earnings']} ETB"
    )
    await update.message.reply_text(text)

async def admin_pending_deposits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Unauthorized.")
        return
    pending = get_pending_deposits()
    if not pending:
        await update.message.reply_text("No pending deposits.")
        return
    text = "Pending deposits:\n"
    for pid, username, amount, ref in pending:
        text += f"ID: {pid} | User: {username} | Amount: {amount} | Ref: {ref}\n"
    await update.message.reply_text(text)

async def admin_approve_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Unauthorized.")
        return
    try:
        payment_id = context.args[0]
    except IndexError:
        await update.message.reply_text("Usage: /approve_deposit <payment_id>")
        return
    msg = approve_deposit(update.effective_user.id, payment_id)
    await update.message.reply_text(msg)

# Similar for withdrawals (pending, approve, reject) – you can add them.

# ========== MAIN ==========
def main():
    app = Application.builder().token(TOKEN).build()

    # User commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("buy", buy))
    app.add_handler(CommandHandler("mycards", mycards))
    app.add_handler(CommandHandler("called", called))
    app.add_handler(CommandHandler("view", view))
    app.add_handler(CommandHandler("deposit", deposit))
    app.add_handler(CommandHandler("withdraw", withdraw))

    # Admin commands
    app.add_handler(CommandHandler("resetround", admin_reset))
    app.add_handler(CommandHandler("setprice", admin_setprice))
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(CommandHandler("pendingdeposits", admin_pending_deposits))
    app.add_handler(CommandHandler("approvedeposit", admin_approve_deposit))
    # Add similar for withdrawals

    # Callbacks
    app.add_handler(CallbackQueryHandler(buy_callback, pattern="^buy_"))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data))

    logger.info("Bot started")
    app.run_polling()

if __name__ == "__main__":
    main()