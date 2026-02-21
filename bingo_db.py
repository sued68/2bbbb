import sqlite3
import json
import random
import os
from datetime import datetime

# ========== CONFIGURATION ==========
DB_PATH = os.getenv("DB_PATH", "/data/bingo.db")   # Railway volume mount point
DEPOSIT_BONUS = 10
MAX_CARDS_PER_USER = 3
ADMIN_TELEGRAM_ID = int(os.getenv("ADMIN_ID", "6835994100"))
DEFAULT_CARD_PRICE = 20
DEFAULT_HOUSE_PERCENT = 10
DEFAULT_WITHDRAWAL_FEE_PERCENT = 5
DEFAULT_ROUND_DURATION = 300   # seconds

# ========== 200 FIXED UNIQUE CARDS ==========
ALL_CARDS = {
  1: [14,12,10,5,9, 17,27,29,20,28, 35,31,"FREE",43,44, 49,58,46,53,54, 65,67,75,72,68],
  2: [7,13,2,11,4, 23,26,29,17,24, 35,40,"FREE",41,37, 60,53,47,57,49, 65,70,63,64,72],
  # ... (include all 200 cards; for brevity only first two shown)
  200: [10,1,2,8,7, 18,19,23,24,30, 32,37,"FREE",40,39, 53,49,50,59,55, 70,75,64,72,68]
}

# ========== DATABASE CONNECTION ==========
def get_connection():
    return sqlite3.connect(DB_PATH)

# ========== INITIALISATION ==========
def init_db():
    conn = get_connection()
    c = conn.cursor()

    # ----- Users -----
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE,
        username TEXT,
        balance INTEGER DEFAULT 0,
        total_deposited INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # ----- Game rounds -----
    c.execute('''CREATE TABLE IF NOT EXISTS game_rounds (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        ended_at TIMESTAMP,
        status TEXT DEFAULT 'active',
        prize_pool INTEGER DEFAULT 0,
        duration_seconds INTEGER DEFAULT 300,
        is_paused INTEGER DEFAULT 0
    )''')

    # ----- Game settings (single row) -----
    c.execute('''CREATE TABLE IF NOT EXISTS game_settings (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        card_price INTEGER DEFAULT 20,
        house_percent INTEGER DEFAULT 10,
        withdrawal_fee_percent INTEGER DEFAULT 5
    )''')

    # ----- Cardboards (fixed 200 cards) -----
    c.execute('''CREATE TABLE IF NOT EXISTS cardboards (
        id INTEGER PRIMARY KEY,
        numbers TEXT NOT NULL
    )''')

    # ----- Active cards for the current round -----
    c.execute('''CREATE TABLE IF NOT EXISTS user_cards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        cardboard_id INTEGER UNIQUE,
        purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (cardboard_id) REFERENCES cardboards(id)
    )''')

    # ----- Permanent purchase history (per round) -----
    c.execute('''CREATE TABLE IF NOT EXISTS card_purchase_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        round_id INTEGER,
        user_id INTEGER,
        cardboard_id INTEGER,
        purchased_at TIMESTAMP,
        FOREIGN KEY (round_id) REFERENCES game_rounds(id),
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')

    # ----- Called numbers per round -----
    c.execute('''CREATE TABLE IF NOT EXISTS called_numbers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        round_id INTEGER,
        number INTEGER,
        called_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (round_id) REFERENCES game_rounds(id),
        UNIQUE(round_id, number)
    )''')

    # ----- Payments (deposits) -----
    c.execute('''CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        payment_id TEXT UNIQUE,
        user_id INTEGER,
        amount INTEGER,
        status TEXT DEFAULT 'pending',
        screenshot TEXT,
        approved_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        approved_at TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')

    # ----- Withdrawals -----
    c.execute('''CREATE TABLE IF NOT EXISTS withdrawals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount INTEGER,
        fee INTEGER,
        final_amount INTEGER,
        payout_method TEXT,
        payout_account TEXT,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')

    # ----- House earnings (track profit) -----
    c.execute('''CREATE TABLE IF NOT EXISTS house_earnings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT,
        amount INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # Indexes
    c.execute('CREATE INDEX IF NOT EXISTS idx_user_cards_user_id ON user_cards(user_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_payments_user_id ON payments(user_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_withdrawals_user_id ON withdrawals(user_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_withdrawals_status ON withdrawals(status)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_called_numbers_round ON called_numbers(round_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_history_round ON card_purchase_history(round_id)')

    conn.commit()

    # Load fixed cards if empty
    c.execute("SELECT COUNT(*) FROM cardboards")
    if c.fetchone()[0] == 0:
        for cid, nums in ALL_CARDS.items():
            c.execute("INSERT INTO cardboards (id, numbers) VALUES (?, ?)", (cid, json.dumps(nums)))
        conn.commit()
        print("✅ 200 cards loaded into database.")

    # Insert default game settings if missing
    c.execute("SELECT COUNT(*) FROM game_settings")
    if c.fetchone()[0] == 0:
        c.execute('''INSERT INTO game_settings (id, card_price, house_percent, withdrawal_fee_percent)
                     VALUES (1, ?, ?, ?)''',
                  (DEFAULT_CARD_PRICE, DEFAULT_HOUSE_PERCENT, DEFAULT_WITHDRAWAL_FEE_PERCENT))
        conn.commit()
        print("✅ Default game settings loaded.")

    # Start an initial round if no active round exists
    c.execute("SELECT id FROM game_rounds WHERE status = 'active'")
    if not c.fetchone():
        c.execute('''INSERT INTO game_rounds (status, duration_seconds)
                     VALUES ('active', ?)''', (DEFAULT_ROUND_DURATION,))
        conn.commit()
        print("✅ Initial game round started.")

    conn.close()

# ========== USER FUNCTIONS ==========
def get_user_by_telegram_id(telegram_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    row = c.fetchone()
    conn.close()
    return row

def create_user(telegram_id, username):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO users (telegram_id, username, balance) VALUES (?, ?, 0)",
              (telegram_id, username))
    conn.commit()
    user_id = c.lastrowid
    conn.close()
    return user_id

def get_user_id(telegram_id):
    user = get_user_by_telegram_id(telegram_id)
    return user[0] if user else None

def get_user_balance(telegram_id):
    user = get_user_by_telegram_id(telegram_id)
    return user[3] if user else 0

def update_user_balance(telegram_id, new_balance):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET balance = ? WHERE telegram_id = ?", (new_balance, telegram_id))
    conn.commit()
    conn.close()

# ========== CARD FUNCTIONS ==========
def get_cardboard(card_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT numbers FROM cardboards WHERE id = ?", (card_id,))
    row = c.fetchone()
    conn.close()
    return json.loads(row[0]) if row else None

def get_cardboard_as_grid(card_id):
    nums = get_cardboard(card_id)
    if not nums:
        return None
    grid = []
    for row in range(5):
        row_start = row * 5
        grid.append(nums[row_start:row_start + 5])
    return grid

def get_user_cards(telegram_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''SELECT cardboard_id FROM user_cards
                 WHERE user_id = (SELECT id FROM users WHERE telegram_id = ?)
                 ORDER BY purchased_at''', (telegram_id,))
    cards = [row[0] for row in c.fetchall()]
    conn.close()
    return cards

def get_all_cards_with_status():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        SELECT 
            cardboards.id,
            cardboards.numbers,
            user_cards.user_id IS NOT NULL as taken
        FROM cardboards
        LEFT JOIN user_cards ON cardboards.id = user_cards.cardboard_id
        ORDER BY cardboards.id
    ''')
    rows = c.fetchall()
    conn.close()
    return [{"id": row[0], "numbers": json.loads(row[1]), "taken": bool(row[2])} for row in rows]

# ========== GAME ROUND FUNCTIONS ==========
def start_new_round():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT duration_seconds FROM game_rounds ORDER BY id DESC LIMIT 1")
    row = c.fetchone()
    duration = row[0] if row else DEFAULT_ROUND_DURATION
    c.execute("INSERT INTO game_rounds (status, duration_seconds) VALUES ('active', ?)", (duration,))
    conn.commit()
    round_id = c.lastrowid
    conn.close()
    return round_id

def get_active_round():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id FROM game_rounds WHERE status = 'active' ORDER BY id DESC LIMIT 1")
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def get_round_prize_pool(round_id=None):
    if round_id is None:
        round_id = get_active_round()
        if not round_id:
            return 0
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT prize_pool FROM game_rounds WHERE id = ?", (round_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0

def is_round_expired(round_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT started_at, duration_seconds FROM game_rounds WHERE id = ?", (round_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return True
    started_at, duration = row
    started = datetime.strptime(started_at, '%Y-%m-%d %H:%M:%S')
    now = datetime.utcnow()
    elapsed = (now - started).total_seconds()
    return elapsed >= duration

def pause_round(round_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE game_rounds SET is_paused = 1 WHERE id = ?", (round_id,))
    conn.commit()
    conn.close()

def resume_round(round_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE game_rounds SET is_paused = 0 WHERE id = ?", (round_id,))
    conn.commit()
    conn.close()

# ========== CARD PURCHASE ==========
def buy_card(telegram_id, cardboard_id):
    conn = get_connection()
    c = conn.cursor()

    user_id = get_user_id(telegram_id)
    if not user_id:
        conn.close()
        return False, "User not found. Please register first."

    round_id = get_active_round()
    if not round_id:
        conn.close()
        return False, "No active game round. Please wait for admin to start one."

    c.execute("SELECT card_price FROM game_settings WHERE id = 1")
    row = c.fetchone()
    price = row[0] if row else DEFAULT_CARD_PRICE

    c.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
    balance = c.fetchone()[0]
    if balance < price:
        conn.close()
        return False, f"❌ Insufficient balance. Need {price}, you have {balance}."

    c.execute("SELECT COUNT(*) FROM user_cards WHERE user_id = ?", (user_id,))
    if c.fetchone()[0] >= MAX_CARDS_PER_USER:
        conn.close()
        return False, f"❌ Maximum {MAX_CARDS_PER_USER} cards allowed per round."

    try:
        c.execute("UPDATE users SET balance = balance - ? WHERE id = ?", (price, user_id))
        c.execute("UPDATE game_rounds SET prize_pool = prize_pool + ? WHERE id = ?", (price, round_id))
        c.execute("INSERT INTO user_cards (user_id, cardboard_id) VALUES (?, ?)", (user_id, cardboard_id))
        c.execute('''
            INSERT INTO card_purchase_history (round_id, user_id, cardboard_id, purchased_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ''', (round_id, user_id, cardboard_id))
        conn.commit()
        conn.close()
        return True, f"✅ Card purchased! New balance: {balance - price}"
    except sqlite3.IntegrityError:
        conn.rollback()
        conn.close()
        return False, "❌ This card is already taken by another user."

# ========== CALLED NUMBERS ==========
def call_number(round_id=None):
    if round_id is None:
        round_id = get_active_round()
        if not round_id:
            return None

    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT is_paused, status FROM game_rounds WHERE id = ?", (round_id,))
    row = c.fetchone()
    if not row or row[1] != 'active' or row[0] == 1:
        conn.close()
        return None

    c.execute("SELECT number FROM called_numbers WHERE round_id = ?", (round_id,))
    used = {row[0] for row in c.fetchall()}

    available = [n for n in range(1, 76) if n not in used]
    if not available:
        conn.close()
        return None

    number = random.choice(available)
    c.execute("INSERT INTO called_numbers (round_id, number) VALUES (?, ?)", (round_id, number))
    conn.commit()
    conn.close()
    return number

def get_called_numbers(round_id=None):
    if round_id is None:
        round_id = get_active_round()
        if not round_id:
            return []
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT number FROM called_numbers WHERE round_id = ? ORDER BY called_at", (round_id,))
    nums = [row[0] for row in c.fetchall()]
    conn.close()
    return nums

# ========== WINNER DETECTION ==========
def check_card_winner(card, called_numbers):
    called = set(called_numbers)
    for row in card:
        if all(cell == "FREE" or cell in called for cell in row):
            return True
    for col in range(5):
        if all(card[row][col] == "FREE" or card[row][col] in called for row in range(5)):
            return True
    return False

def find_winners(round_id=None):
    if round_id is None:
        round_id = get_active_round()
        if not round_id:
            return []

    conn = get_connection()
    c = conn.cursor()

    called = get_called_numbers(round_id)
    if not called:
        conn.close()
        return []

    c.execute('SELECT user_id, cardboard_id FROM user_cards')
    winners = []
    for user_id, cardboard_id in c.fetchall():
        card_data = get_cardboard(cardboard_id)
        if not card_data:
            continue
        card_grid = [card_data[i*5:(i+1)*5] for i in range(5)]
        if check_card_winner(card_grid, called):
            winners.append(user_id)

    conn.close()
    return winners

# ========== PRIZE DISTRIBUTION ==========
def handle_winner(winner_user_id, round_id=None):
    conn = get_connection()
    c = conn.cursor()

    if round_id is None:
        round_id = get_active_round()
        if not round_id:
            conn.close()
            return "No active round."

    c.execute("UPDATE game_rounds SET status = 'processing' WHERE id = ? AND status = 'active'", (round_id,))
    if c.rowcount == 0:
        conn.close()
        return "Round already finished or being processed."

    c.execute("SELECT prize_pool, started_at, duration_seconds FROM game_rounds WHERE id = ?", (round_id,))
    row = c.fetchone()
    if not row:
        conn.rollback()
        conn.close()
        return "Round not found."
    prize_pool, started_at, duration = row

    started = datetime.strptime(started_at, '%Y-%m-%d %H:%M:%S')
    if (datetime.utcnow() - started).total_seconds() > duration:
        conn.rollback()
        conn.close()
        return refund_round(round_id)

    if prize_pool <= 0:
        conn.rollback()
        conn.close()
        return "Prize pool empty."

    c.execute("SELECT house_percent FROM game_settings WHERE id = 1")
    house_percent = c.fetchone()[0]

    house_cut = (prize_pool * house_percent) // 100
    winner_amount = prize_pool - house_cut

    c.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (winner_amount, winner_user_id))
    c.execute("INSERT INTO house_earnings (source, amount) VALUES ('bingo_round', ?)", (house_cut,))
    c.execute('''UPDATE game_rounds SET status = 'finished', ended_at = CURRENT_TIMESTAMP
                 WHERE id = ?''', (round_id,))

    conn.commit()
    conn.close()

    new_round_id = start_new_round()
    return f"🏆 Winner paid {winner_amount} ETB. House earned {house_cut} ETB. New round {new_round_id} started."

def refund_round(round_id):
    conn = get_connection()
    c = conn.cursor()

    c.execute('''
        SELECT user_id, SUM(price) FROM (
            SELECT uc.user_id, gs.card_price as price
            FROM user_cards uc
            JOIN game_settings gs ON 1=1
            WHERE uc.cardboard_id IN (
                SELECT cardboard_id FROM card_purchase_history WHERE round_id = ?
            )
        ) GROUP BY user_id
    ''', (round_id,))
    refunds = c.fetchall()

    if not refunds:
        c.execute("UPDATE game_rounds SET status = 'finished', ended_at = CURRENT_TIMESTAMP WHERE id = ?", (round_id,))
        conn.commit()
        conn.close()
        start_new_round()
        return "Round closed (no players)."

    for user_id, total_paid in refunds:
        c.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (total_paid, user_id))

    c.execute('''UPDATE game_rounds SET status = 'refunded', ended_at = CURRENT_TIMESTAMP
                 WHERE id = ?''', (round_id,))

    conn.commit()
    conn.close()

    new_round_id = start_new_round()
    return f"All players refunded. New round {new_round_id} started."

def check_round_timeout():
    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT id FROM game_rounds WHERE status = 'active' ORDER BY id DESC LIMIT 1")
    row = c.fetchone()
    if not row:
        conn.close()
        return

    round_id = row[0]
    if is_round_expired(round_id):
        c.execute("SELECT status FROM game_rounds WHERE id = ?", (round_id,))
        status = c.fetchone()[0]
        if status == 'active':
            conn.close()
            return refund_round(round_id)
    conn.close()

# ========== DEPOSITS (Payments) ==========
def request_deposit(telegram_id, amount, transaction_ref):
    conn = get_connection()
    c = conn.cursor()

    user_id = get_user_id(telegram_id)
    if not user_id:
        conn.close()
        return "User not found."

    c.execute("""
        INSERT INTO payments (payment_id, user_id, amount, status)
        VALUES (?, ?, ?, 'pending')
    """, (transaction_ref, user_id, amount))

    conn.commit()
    conn.close()
    return "✅ Deposit request submitted. Waiting for admin approval."

def approve_deposit(admin_id, payment_id):
    if admin_id != ADMIN_TELEGRAM_ID:
        return "⛔ Not authorized."

    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT user_id, amount, status FROM payments WHERE payment_id = ?", (payment_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return "Deposit not found."

    user_id, amount, status = row
    if status != "pending":
        conn.close()
        return "Already processed."

    c.execute("UPDATE payments SET status = 'approved', approved_by = ?, approved_at = CURRENT_TIMESTAMP WHERE payment_id = ?",
              (admin_id, payment_id))
    c.execute("UPDATE users SET balance = balance + ? + ? WHERE id = ?", (amount, DEPOSIT_BONUS, user_id))
    c.execute("UPDATE users SET total_deposited = total_deposited + ? WHERE id = ?", (amount, user_id))

    conn.commit()
    conn.close()
    return "✅ Deposit approved and balance updated."

def reject_deposit(admin_id, payment_id):
    if admin_id != ADMIN_TELEGRAM_ID:
        return "⛔ Not authorized."

    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE payments SET status = 'rejected' WHERE payment_id = ?", (payment_id,))
    conn.commit()
    conn.close()
    return "❌ Deposit rejected."

def get_pending_deposits():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        SELECT payments.id, users.username, payments.amount, payments.payment_id
        FROM payments
        JOIN users ON payments.user_id = users.id
        WHERE payments.status = 'pending'
    ''')
    rows = c.fetchall()
    conn.close()
    return rows

# ========== WITHDRAWALS ==========
def request_withdrawal(telegram_id, amount, payout_method, payout_account):
    conn = get_connection()
    c = conn.cursor()

    user_id = get_user_id(telegram_id)
    if not user_id:
        conn.close()
        return "User not found."

    c.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
    balance = c.fetchone()[0]

    if amount <= 0:
        conn.close()
        return "Invalid amount."

    if balance < amount:
        conn.close()
        return "❌ Insufficient balance."

    c.execute("SELECT withdrawal_fee_percent FROM game_settings WHERE id = 1")
    fee_percent = c.fetchone()[0]

    fee = (amount * fee_percent) // 100
    final_amount = amount - fee

    c.execute('''
        INSERT INTO withdrawals (user_id, amount, fee, final_amount, payout_method, payout_account)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, amount, fee, final_amount, payout_method, payout_account))

    conn.commit()
    conn.close()
    return f"✅ Withdrawal requested.\nFee: {fee}\nYou will receive: {final_amount}"

def approve_withdrawal(admin_id, withdrawal_id):
    if admin_id != ADMIN_TELEGRAM_ID:
        return "⛔ Not authorized."

    conn = get_connection()
    c = conn.cursor()

    c.execute('''
        SELECT user_id, amount, fee, final_amount, status
        FROM withdrawals
        WHERE id = ?
    ''', (withdrawal_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return "Withdrawal not found."

    user_id, amount, fee, final_amount, status = row
    if status != "pending":
        conn.close()
        return "Already processed."

    c.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
    balance = c.fetchone()[0]
    if balance < amount:
        conn.close()
        return "User has insufficient balance now."

    c.execute("UPDATE users SET balance = balance - ? WHERE id = ?", (amount, user_id))
    c.execute("INSERT INTO house_earnings (source, amount) VALUES ('withdrawal_fee', ?)", (fee,))
    c.execute("UPDATE withdrawals SET status = 'approved' WHERE id = ?", (withdrawal_id,))

    conn.commit()
    conn.close()
    return "✅ Withdrawal approved. Pay user manually."

def reject_withdrawal(admin_id, withdrawal_id):
    if admin_id != ADMIN_TELEGRAM_ID:
        return "⛔ Not authorized."

    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE withdrawals SET status = 'rejected' WHERE id = ?", (withdrawal_id,))
    conn.commit()
    conn.close()
    return "❌ Withdrawal rejected."

def get_pending_withdrawals():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        SELECT withdrawals.id, users.username, withdrawals.amount,
               withdrawals.fee, withdrawals.final_amount,
               withdrawals.payout_method, withdrawals.payout_account
        FROM withdrawals
        JOIN users ON withdrawals.user_id = users.id
        WHERE withdrawals.status = 'pending'
    ''')
    rows = c.fetchall()
    conn.close()
    return rows

# ========== ADMIN FUNCTIONS ==========
def reset_round(admin_telegram_id):
    if admin_telegram_id != ADMIN_TELEGRAM_ID:
        return "⛔ You are not admin."

    conn = get_connection()
    c = conn.cursor()

    c.execute('''
        UPDATE game_rounds
        SET status = 'finished', ended_at = CURRENT_TIMESTAMP
        WHERE status = 'active'
    ''')
    c.execute("DELETE FROM user_cards")
    conn.commit()
    conn.close()

    new_round_id = start_new_round()
    return f"♻ Round reset. New round started (ID: {new_round_id})"

def set_card_price(admin_telegram_id, new_price):
    if admin_telegram_id != ADMIN_TELEGRAM_ID:
        return "⛔ You are not admin."
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE game_settings SET card_price = ? WHERE id = 1", (new_price,))
    conn.commit()
    conn.close()
    return f"✅ Card price updated to {new_price}."

def set_house_percent(admin_telegram_id, new_percent):
    if admin_telegram_id != ADMIN_TELEGRAM_ID:
        return "⛔ You are not admin."
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE game_settings SET house_percent = ? WHERE id = 1", (new_percent,))
    conn.commit()
    conn.close()
    return f"✅ House percent updated to {new_percent}%."

def set_withdrawal_fee(admin_telegram_id, new_percent):
    if admin_telegram_id != ADMIN_TELEGRAM_ID:
        return "⛔ You are not admin."
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE game_settings SET withdrawal_fee_percent = ? WHERE id = 1", (new_percent,))
    conn.commit()
    conn.close()
    return f"✅ Withdrawal fee updated to {new_percent}%."

def set_round_duration(admin_telegram_id, new_duration_seconds):
    if admin_telegram_id != ADMIN_TELEGRAM_ID:
        return "⛔ You are not admin."
    conn = get_connection()
    c = conn.cursor()
    round_id = get_active_round()
    if round_id:
        c.execute("UPDATE game_rounds SET duration_seconds = ? WHERE id = ?", (new_duration_seconds, round_id))
    conn.commit()
    conn.close()
    return f"✅ Round duration updated to {new_duration_seconds} seconds."

def admin_stats():
    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]

    c.execute("SELECT SUM(total_deposited) FROM users")
    total_deposits = c.fetchone()[0] or 0

    c.execute("SELECT prize_pool FROM game_rounds WHERE status='active'")
    row = c.fetchone()
    current_prize_pool = row[0] if row else 0

    c.execute("SELECT COUNT(*) FROM game_rounds")
    total_rounds = c.fetchone()[0]

    c.execute("SELECT SUM(amount) FROM house_earnings")
    total_house = c.fetchone()[0] or 0

    conn.close()
    return {
        "total_users": total_users,
        "total_deposits": total_deposits,
        "current_prize_pool": current_prize_pool,
        "total_rounds": total_rounds,
        "total_house_earnings": total_house
    }

# ========== INITIALISE ON IMPORT ==========
init_db()