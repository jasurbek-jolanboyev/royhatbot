import asyncio
import logging
import sqlite3
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import (
    ChatPermissions,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.client.default import DefaultBotProperties

# =========================
# 🔧 Sozlamalar
# =========================
BOT_TOKEN = "6335576043:AAG9s9vmorxeHakm-uZ5-Jb3SRZGqRX2e7I"
DATABASE_CHANNEL = -1003085828839
admins = {6060353145}   # bosh admin ID
owners = {6060353145}   # egalar IDlari
DB_FILE = "data.db"

# =========================
# 🔔 Logging
# =========================
logging.basicConfig(level=logging.INFO)

# =========================
# 🤖 Bot & Dispatcher
# =========================
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher(storage=MemoryStorage())

# =========================
# 🗂️ Runtime ma'lumotlar
# =========================
registered_users: set[int] = set()
joined_groups: set[int] = set()
pending_unlock: dict[int, list[int]] = {}   # user_id -> [group_ids]
last_blocked_group: dict[int, int] = {}     # oxirgi bloklangan guruh

# =========================
# 🧭 States (FSM)
# =========================
class RegisterForm(StatesGroup):
    fullname = State()
    age = State()
    phone = State()
    about = State()

class FeedbackForm(StatesGroup):
    text = State()

class BroadcastState(StatesGroup):
    text = State()

class DMState(StatesGroup):
    target_id = State()
    text = State()

class AddAdminState(StatesGroup):
    user_id = State()

class RemoveAdminState(StatesGroup):
    user_id = State()

# =========================
# ⌨️ Klaviaturalar
# =========================
def main_menu(user_id: int):
    keyboard = [
        [KeyboardButton(text="Ro'yxatdan o'tish")],
        [KeyboardButton(text="💬 Fikr bildirish")],
        [KeyboardButton(text="👨‍💻 Dasturchi")],
    ]
    if user_id in admins:
        keyboard += [
            [KeyboardButton(text="📊 Statistika")],
            [KeyboardButton(text="👥 Guruhlar")],
            [KeyboardButton(text="📢 Broadcast (barchaga)")],
            [KeyboardButton(text="✉️ DM (ID bo‘yicha)")],
            [KeyboardButton(text="➕ Admin qo‘shish")],
            [KeyboardButton(text="➖ Adminni olib tashlash")],
        ]
    return ReplyKeyboardMarkup(resize_keyboard=True, keyboard=keyboard)

cancel_kb = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[[KeyboardButton(text="❌ Bekor qilish")]])

# =========================
# 🗃️ SQLite bazasi
# =========================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        fullname TEXT,
        age TEXT,
        phone TEXT,
        about TEXT
    )
    """)
    conn.commit()
    conn.close()

def add_user_to_db(user_id: int, fullname: str, age: str, phone: str, about: str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT OR REPLACE INTO users (user_id, fullname, age, phone, about)
    VALUES (?, ?, ?, ?, ?)
    """, (user_id, fullname, age, phone, about))
    conn.commit()
    conn.close()

def load_registered_users():
    global registered_users
    if os.path.exists(DB_FILE):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users")
        rows = cursor.fetchall()
        registered_users = {row[0] for row in rows}
        conn.close()

# =========================
# 🚀 /start
# =========================
@dp.message(Command("start"))
async def start_handler(message: types.Message, state: FSMContext):
    if message.chat.type != "private":
        return
    await state.clear()
    await message.answer("👋 Salom!\nQuyidagi bo‘limlardan birini tanlang:", reply_markup=main_menu(message.from_user.id))

# ❌ Bekor qilish
@dp.message(F.text == "❌ Bekor qilish")
async def cancel_handler(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Amaliyot bekor qilindi.", reply_markup=main_menu(message.from_user.id))

# =========================
# 👨‍💻 Dasturchi
# =========================
@dp.message(F.text == "👨‍💻 Dasturchi")
async def dev_info(message: types.Message):
    await message.answer(
        "👨‍💻 Dasturchi: <b>Jasurbek Jo'lanboyev G'ayrat o'g'li</b>\n\n"
        "📩 Telegram: @Vscoderr\n"
        "📹 YouTube: https://www.youtube.com/@Jasurbek_Jolanboyev\n"
        "🔗 Instagram: https://www.instagram.com/jasurbek.official.uz\n"
        "🔗 Linkedin: https://www.linkedin.com/in/jasurbek-jo-lanboyev-74b758351"
    )

# =========================
# 💬 Feedback
# =========================
@dp.message(F.text == "💬 Fikr bildirish")
async def feedback_start(message: types.Message, state: FSMContext):
    await message.answer("✍️ Fikringizni yozib yuboring:", reply_markup=cancel_kb)
    await state.set_state(FeedbackForm.text)

@dp.message(FeedbackForm.text)
async def feedback_process(message: types.Message, state: FSMContext):
    await state.clear()
    if message.text == "❌ Bekor qilish":
        return await message.answer("❌ Bekor qilindi.", reply_markup=main_menu(message.from_user.id))

    text = (
        f"📩 <b>Yangi feedback</b>\n\n"
        f"👤 {message.from_user.full_name}\n"
        f"🆔 <code>{message.from_user.id}</code>\n\n"
        f"💬 {message.text}"
    )
    for admin_id in admins:
        try:
            await bot.send_message(admin_id, text)
        except:
            pass
    await message.answer("✅ Fikringiz uchun rahmat!", reply_markup=main_menu(message.from_user.id))

# =========================
# 📝 Ro'yxatdan o'tish
# =========================
@dp.message(F.text == "Ro'yxatdan o'tish")
async def start_register(message: types.Message, state: FSMContext):
    if message.from_user.id in registered_users:
        return await message.answer("✅ Siz allaqachon ro‘yxatdan o‘tgansiz!", reply_markup=main_menu(message.from_user.id))
    await message.answer("Ism va familiyangizni kiriting:", reply_markup=cancel_kb)
    await state.set_state(RegisterForm.fullname)

@dp.message(RegisterForm.fullname)
async def process_fullname(message: types.Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        return await cancel_handler(message, state)
    await state.update_data(fullname=message.text.strip())
    await message.answer("Yoshingizni kiriting:", reply_markup=cancel_kb)
    await state.set_state(RegisterForm.age)

@dp.message(RegisterForm.age)
async def process_age(message: types.Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        return await cancel_handler(message, state)
    await state.update_data(age=message.text.strip())
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📞 Telefon raqamni yuborish", request_contact=True)], [KeyboardButton(text="❌ Bekor qilish")]],
        resize_keyboard=True,
    )
    await message.answer("Telefon raqamingizni yuboring:", reply_markup=kb)
    await state.set_state(RegisterForm.phone)

@dp.message(RegisterForm.phone, F.contact)
async def process_phone_contact(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.contact.phone_number)
    await message.answer("O‘zingiz haqingizda qisqacha yozing:", reply_markup=cancel_kb)
    await state.set_state(RegisterForm.about)
@dp.message(RegisterForm.about)
async def process_about(message: types.Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        return await cancel_handler(message, state)

    data = await state.get_data()
    fullname = data.get("fullname")
    age = data.get("age")
    phone = data.get("phone")
    about = message.text.strip()

    # 1️⃣ SQLite bazaga yozish
    add_user_to_db(message.from_user.id, fullname, age, phone, about)
    registered_users.add(message.from_user.id)

    # 2️⃣ Text faylga yozish
    with open("data.txt", "a", encoding="utf-8") as f:
        f.write(f"{message.from_user.id} | {fullname} | {age} | {phone} | {about}\n")

    # 3️⃣ Telegram kanalga yuborish
    text = (
        f"📌 <b>Yangi foydalanuvchi ro‘yxatdan o‘tdi</b>\n\n"
        f"👤 Ismi: {fullname}\n"
        f"🆔 ID: <code>{message.from_user.id}</code>\n"
        f"🎂 Yoshi: {age}\n"
        f"📞 Telefon: {phone}\n"
        f"📝 Haqida: {about}"
    )
    try:
        await bot.send_message(DATABASE_CHANNEL, text)
    except Exception as e:
        logging.error(f"Kanalga yuborishda xatolik: {e}")

    await state.clear()
    await message.answer("✅ Siz muvaffaqiyatli ro‘yxatdan o‘tdingiz!", reply_markup=main_menu(message.from_user.id))


    # 🔓 Guruh cheklovini olib tashlash
    if message.from_user.id in pending_unlock:
        for gid in pending_unlock[message.from_user.id]:
            try:
                await bot.restrict_chat_member(
                    chat_id=gid,
                    user_id=message.from_user.id,
                    permissions=ChatPermissions(can_send_messages=True),
                )
                await bot.send_message(
                    gid,
                    f"🎉 <a href='tg://user?id={message.from_user.id}'>{message.from_user.full_name}</a>, endi guruhda yozishingiz mumkin!"
                )
            except:
                pass
        del pending_unlock[message.from_user.id]

# =========================
# 👮 Guruh nazorati
# =========================
@dp.message()
async def check_group_messages(message: types.Message):
    if message.chat.type in ("group", "supergroup"):
        joined_groups.add(message.chat.id)
        user_id = message.from_user.id

        if user_id not in registered_users:
            try:
                await message.delete()
                await bot.restrict_chat_member(
                    chat_id=message.chat.id,
                    user_id=user_id,
                    permissions=ChatPermissions(can_send_messages=False),
                )
                me = await bot.get_me()
                invite_text = (
                    f"⚠️ <a href='tg://user?id={user_id}'>{message.from_user.full_name}</a>, "
                    f"iltimos avval @{me.username} botida <b>ro‘yxatdan o‘ting</b> "
                    f"so‘ng guruhda yozishingiz mumkin bo‘ladi."
                )
                await bot.send_message(message.chat.id, invite_text)
                if user_id not in pending_unlock:
                    pending_unlock[user_id] = []
                if message.chat.id not in pending_unlock[user_id]:
                    pending_unlock[user_id].append(message.chat.id)
                last_blocked_group[user_id] = message.chat.id
            except Exception as e:
                logging.error(f"Guruh nazoratida xatolik: {e}")

# =========================
# 🔔 Reminder – guruhda ro‘yxatsizlarni eslatish
# =========================
async def reminder_task():
    while True:
        try:
            for gid in joined_groups:
                for user_id in pending_unlock:
                    if gid in pending_unlock[user_id]:
                        try:
                            await bot.send_message(
                                gid,
                                f"⚠️ <a href='tg://user?id={user_id}'>Foydalanuvchi</a>, iltimos botda ro‘yxatdan o‘ting."
                            )
                        except:
                            pass
            await asyncio.sleep(3600)  # har 1 soatda eslatadi
        except Exception as e:
            logging.error(f"Reminder xatolik: {e}")
            await asyncio.sleep(60)

# =========================
# 🔄 Run
# =========================
async def main():
    init_db()
    load_registered_users()
    asyncio.create_task(reminder_task())
    print("🤖 Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
