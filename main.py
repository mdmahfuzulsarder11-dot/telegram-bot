import logging
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
import asyncio

API_TOKEN = ":8926467123:AAFdfNvZz_n__bTW4wD9HWEAIImn2hde2I4"

CHANNEL_ID = "@gamilupdate"  
CHANNEL_LINK = "https://t.me/gamilupdate" 
ADMIN_ID = 5582627293  

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp =
Dispatcher(storage=MemoryStorage())

conn = sqlite3.connect("gtask.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0, hold REAL DEFAULT 0, total_earned REAL DEFAULT 0)")
cursor.execute("CREATE TABLE IF NOT EXISTS accounts (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, email TEXT, password TEXT, recovery TEXT, two_fa TEXT, status TEXT DEFAULT 'Pending', created_at TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS payouts (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL, address TEXT, status TEXT DEFAULT 'Paid', date TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS referrals (user_id INTEGER, referred_by INTEGER)")
conn.commit()

class GmailReg(StatesGroup):
    email = State()
    pwd = State()
    recovery = State()
    two_fa_opt = State()
    two_fa_key = State()

class Payout(StatesGroup):
    address = State()
    amount = State()

async def check_subscription(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        if member.status in ["creator", "administrator", "member"]:
            return True
        return False
    except Exception:
        return False

def join_channel_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="📢 Join Channel", url=CHANNEL_LINK)
    builder.button(text="✅ Joined / Check", callback_data="check_join")
    builder.adjust(1)
    return builder.as_markup()

def main_menu():
    builder = ReplyKeyboardBuilder()
    builder.button(text="➕ Register a new Gmail")
    builder.button(text="📁 My accounts")
    builder.button(text="💰 Balance")
    builder.button(text="👥 My referrals")
    builder.button(text="⚙️ Settings")
    builder.button(text="ℹ️ Help")
    builder.adjust(2, 2, 2)
    return builder.as_markup(resize_keyboard=True)

@dp.message(Command("start"))
async def start(msg: types.Message):
    user_id = msg.from_user.id
    
    if not await check_subscription(user_id):
        await msg.answer("❌ You must join our channel to use this bot!", reply_markup=join_channel_keyboard())
        return

    args = msg.text.split(" ")
    referred_by = None
    if len(args) > 1 and args[1].isdigit():
        referred_by = int(args[1])
        
    cursor.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        if referred_by and referred_by != user_id:
            cursor.execute("INSERT INTO referrals (user_id, referred_by) VALUES (?, ?)", (user_id, referred_by))
            cursor.execute("UPDATE users SET balance = balance + 0.10, total_earned = total_earned + 0.10 WHERE user_id=?", (referred_by,))
        conn.commit()

    await msg.answer("Welcome to Gtask Xgodo! Choose an option:", reply_markup=main_menu())

@dp.callback_query(F.data == "check_join")
async def check_join_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if await check_subscription(user_id):
        await callback.message.delete()
        await callback.message.answer("✅ Thank you for joining! You can now use the bot.", reply_markup=main_menu())
    else:
        await callback.answer("❌ You have not joined the channel yet! Please join first.", show_alert=True)

@dp.message(Command("admin_panel"))
async def admin_panel(msg: types.Message):
    if msg.from_user.id != ADMIN_ID:
        return 
        
    cursor.execute("SELECT id, user_id, email, password, recovery, two_fa FROM accounts WHERE status='Pending' LIMIT 1")
    acc = cursor.fetchone()
    
    if not acc:
        await msg.answer("🎉 No pending accounts found at the moment!")
        return
        
    acc_id, u_id, email, pwd, rec, two_fa = acc
    two_fa_val = two_fa if two_fa else "None"
    
    text = (
        f"⏳ **New Pending Account**\n\n"
        f"📝 Acc ID: {acc_id}\n"
        f"👤 User ID: {u_id}\n"
        f"📧 Email: `{email}`\n"
        f"🔑 Password: `{pwd}`\n"
        f"🔄 Recovery: `{rec}`\n"
        f"🔐 2FA Key: `{two_fa_val}`"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Approve ($0.27)", callback_data=f"approve_{acc_id}_{u_id}")
    builder.button(text="❌ Decline / Reject", callback_data=f"decline_{acc_id}_{u_id}")
    builder.adjust(2)
    
    await msg.answer(text, reply_markup=builder.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("approve_") | F.data.startswith("decline_"))
async def handle_admin_action(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Unauthorized action!", show_alert=True)
        return
        
    action, acc_id, u_id = callback.data.split("_")
    acc_id = int(acc_id)
    u_id = int(u_id)
    
    if action == "approve":
        cursor.execute("UPDATE accounts SET status='Approved' WHERE id=?", (acc_id,))
        cursor.execute("UPDATE users SET balance = balance + 0.27, total_earned = total_earned + 0.27 WHERE user_id=?", (u_id,))
        conn.commit()
        
        await callback.message.edit_text(f"✅ Account ID {acc_id} has been Approved! $0.27 added to user.")
        try:
            await bot.send_message(u_id, f"🎉 Your submitted account (ID: {acc_id}) has been **Approved**! $0.27 added to your balance.")
        except Exception:
            pass 
            
    elif action == "decline":
        cursor.execute("UPDATE accounts SET status='Declined' WHERE id=?", (acc_id,))
        conn.commit()
        
        await callback.message.edit_text(f"❌ Account ID {acc_id} has been Declined/Rejected.")
        try:
            await bot.send_message(u_id, f"❌ Your submitted account (ID: {acc_id}) has been **Declined/Rejected** by the admin.")
        except Exception:
            pass

@dp.message(F.text == "➕ Register a new Gmail")
async def reg_gmail(msg: types.Message, state: FSMContext):
    if not await check_subscription(msg.from_user.id):
        await msg.answer("❌ Please join our channel first!", reply_markup=join_channel_keyboard())
        return
    await msg.answer("Please enter your Gmail email address:")
    await state.set_state(GmailReg.email)

@dp.message(GmailReg.email)
async def get_email(msg: types.Message, state: FSMContext):
    await state.update_data(email=msg.text)
    await msg.answer("Please enter your password:")
    await state.set_state(GmailReg.pwd)

@dp.message(GmailReg.pwd)
async def get_pwd(msg: types.Message, state: FSMContext):
    await state.update_data(pwd=msg.text)
    await msg.answer("Please enter your recovery email address:")
    await state.set_state(GmailReg.recovery)

@dp.message(GmailReg.recovery)
async def get_recovery(msg: types.Message, state: FSMContext):
    await state.update_data(recovery=msg.text)
    builder = ReplyKeyboardBuilder()
    builder.button(text="Add 2FA key")
    builder.button(text="Done (without 2FA)")
    await msg.answer("We suggest you to set 2FA on the account to increase the chances of successful login.", reply_markup=builder.as_markup(resize_keyboard=True))
    await state.set_state(GmailReg.two_fa_opt)

@dp.message(GmailReg.two_fa_opt, F.text == "Add 2FA key")
async def opt_2fa(msg: types.Message, state: FSMContext):
    await msg.answer("Please type your 2FA secret key:")
    await state.set_state(GmailReg.two_fa_key)

@dp.message(GmailReg.two_fa_opt, F.text == "Done (without 2FA)")
async def skip_2fa(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = msg.from_user.id
    cursor.execute("INSERT INTO accounts (user_id, email, password, recovery) VALUES (?, ?, ?, ?)",
                   (user_id, data['email'], data['pwd'], data['recovery']))
    conn.commit()
    await msg.answer("Account submitted successfully and registered for $0.27!", reply_markup=main_menu())
    await state.clear()

@dp.message(GmailReg.two_fa_key)
async def save_with_2fa(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = msg.from_user.id
    cursor.execute("INSERT INTO accounts (user_id, email, password, recovery, two_fa) VALUES (?, ?, ?, ?, ?)",
                   (user_id, data['email'], data['pwd'], data['recovery'], msg.text))
    conn.commit()
    await msg.answer("Account with 2FA submitted successfully and registered for $0.27!", reply_markup=main_menu())
    await state.clear()

@dp.message(F.text == "📁 My accounts")
async def my_accounts(msg: types.Message):
    if not await check_subscription(msg.from_user.id):
        await msg.answer("❌ Please join our channel first!", reply_markup=join_channel_keyboard())
        return
    cursor.execute("SELECT email, status FROM accounts WHERE user_id=?", (msg.from_user.id,))
    accounts = cursor.fetchall()
    
    if not accounts:
        await msg.answer("You have not submitted any accounts yet.")
        return
        
    text = "Your submitted accounts:\n\n"
    for acc in accounts:
        status_icon = "✅" if acc[1] == "Approved" else ("❌" if acc[1] == "Declined" else "⏳")
        text += f"Email: {acc[0]} | Status: {status_icon} {acc[1]}\n"
        
    await msg.answer(text)

@dp.message(F.text == "💰 Balance")
async def balance_info(msg: types.Message):
    if not await check_subscription(msg.from_user.id):
        await msg.answer("❌ Please join our channel first!", reply_markup=join_channel_keyboard())
        return
    cursor.execute("SELECT balance, hold FROM users WHERE user_id=?", (msg.from_user.id,))
    user = cursor.fetchone()
    b, h = user if user else (0, 0)
    
    text = f"Total Balance: ${b + h:.2f}\nActive Balance: ${b:.2f}\nHold: ${h:.2f}"
    
    builder = ReplyKeyboardBuilder()
    builder.button(text="Payout")
    builder.button(text="Balance history")
    builder.adjust(2)
    await msg.answer(text, reply_markup=builder.as_markup(resize_keyboard=True))

@dp.message(F.text == "Payout")
async def payout_cmd(msg: types.Message):
    builder = ReplyKeyboardBuilder()
    builder.button(text="LTC (Litecoin)")
    builder.adjust(1)
    await msg.answer("Select payout method:", reply_markup=builder.as_markup(resize_keyboard=True))

@dp.message(F.text == "LTC (Litecoin)")
async def ltc_payout(msg: types.Message, state: FSMContext):
    await msg.answer("Please enter your LTC wallet address:")
    await state.set_state(Payout.address)

@dp.message(Payout.address)
async def get_address(msg: types.Message, state: FSMContext):
    await state.update_data(address=msg.text)
    await msg.answer("Now enter the amount to withdraw (in USD):")
    await state.set_state(Payout.amount)

@dp.message(Payout.amount)
async def get_amount(msg: types.Message, state: FSMContext):
    try:
        amt = float(msg.text)
    except ValueError:
        await msg.answer("Please enter a valid amount in numbers.")
        return
        
    data = await state.get_data()
    user_id = msg.from_user.id
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    res = cursor.fetchone()
    bal = res[0] if res else 0
    
    if amt > bal:
        await msg.answer("Amount exceeds available balance.")
    else:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id=?", (amt, user_id))
        cursor.execute("INSERT INTO payouts (user_id, amount, address, date) VALUES (?, ?, ?, ?)", (user_id, amt, data['address'], now))
        conn.commit()
        await msg.answer("Withdraw request sent successfully! ✅")
    await state.clear()

@dp.message(F.text == "Balance history")
async def balance_history(msg: types.Message):
    cursor.execute("SELECT amount, address, date, status FROM payouts WHERE user_id=?", (msg.from_user.id,))
    payouts = cursor.fetchall()
    
    if not payouts:
        await msg.answer("No balance history found.")
        return
        
    text = "📜 Balance History:\n\n"
    for p in payouts:
        text += f"Amount: ${p[0]:.2f} | Status: {p[3]} | Date: {p[2]}\nAddress: {p[1]}\n\n"
    await msg.answer(text)

@dp.message(F.text == "👥 My referrals")
async def referrals_info(msg: types.Message):
    if not await check_subscription(msg.from_user.id):
        await msg.answer("❌ Please join our channel first!", reply_markup=join_channel_keyboard())
        return
    user_id = msg.from_user.id
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
    
    cursor.execute("SELECT COUNT(*) FROM referrals WHERE referred_by=?", (user_id,))
    ref_count = cursor.fetchone()[0]
    
    await msg.answer(
        f"👥 Referral Program\n\n"
        f"Your Referral Link: {ref_link}\n"
        f"You have referred {ref_count} users."
    )

@dp.message(F.text == "ℹ️ Help")
async def help_cmd(msg: types.Message):
    await msg.answer("For support and help, please join our channel or group.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
  
