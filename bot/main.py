# main.py
import asyncio
import logging
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
        "📩 Telegram: @Vscoderr\n\n"
        "📹 YouTube: https://www.youtube.com/@Jasurbek_Jolanboyev\n\n"
        "🔗 Instagram: https://www.instagram.com/jasurbek.official.uz\n\n"
        "🔗 Linkedin: https://www.linkedin.com/in/jasurbek-jo-lanboyev-74b758351?utm_source=share&utm_campaign=share_via&utm_content=profile&utm_medium=android_app"
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

    group_info = ""
    if message.from_user.id in last_blocked_group:
        gid = last_blocked_group[message.from_user.id]
        try:
            chat = await bot.get_chat(gid)
            link = chat.invite_link or f"https://t.me/c/{str(gid)[4:]}"
            group_info = f"\n🏷 Guruh: {chat.title}\n🔗 Link: {link}"
        except:
            pass

    text = (
        f"📝 <b>Yangi foydalanuvchi</b>\n\n"
        f"👤 Ism Familiya: {fullname}\n"
        f"📅 Yosh: {age}\n"
        f"📱 Telefon: {phone}\n"
        f"ℹ️ Qo‘shimcha: {about}\n"
        f"🆔 ID: <code>{message.from_user.id}</code>{group_info}"
    )
    try:
        await bot.send_message(DATABASE_CHANNEL, text)
    except:
        pass

    registered_users.add(message.from_user.id)
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
# 📊 Admin panel
# =========================
@dp.message(F.text == "📊 Statistika")
async def admin_stats(message: types.Message):
    if message.from_user.id not in admins:
        return await message.answer("❌ Siz admin emassiz.")
    await message.answer(
        f"📊 Statistika:\n"
        f"👥 Foydalanuvchilar: <b>{len(registered_users)}</b>\n"
        f"💬 Guruhlar: <b>{len(joined_groups)}</b>\n"
        f"👮 Adminlar: <b>{len(admins)}</b>"
    )

@dp.message(F.text == "👥 Guruhlar")
async def admin_groups(message: types.Message):
    if message.from_user.id not in admins:
        return await message.answer("❌ Siz admin emassiz.")
    if not joined_groups:
        return await message.answer("❌ Hozircha guruhga qo‘shilmaganman.")
    txt = "👥 Bot qo‘shilgan guruhlar:\n\n"
    for g in list(joined_groups):
        try:
            chat = await bot.get_chat(g)
            txt += f"• {chat.title} (<code>{g}</code>)\n"
        except:
            pass
    await message.answer(txt)

# 📢 Broadcast
@dp.message(F.text == "📢 Broadcast (barchaga)")
async def start_broadcast(message: types.Message, state: FSMContext):
    if message.from_user.id not in admins:
        return await message.answer("❌ Siz admin emassiz.")
    await message.answer("✍️ Barchaga yuboriladigan xabarni kiriting:", reply_markup=cancel_kb)
    await state.set_state(BroadcastState.text)

@dp.message(BroadcastState.text)
async def do_broadcast_all(message: types.Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        return await cancel_handler(message, state)
    count = 0
    for uid in registered_users:
        try:
            await bot.send_message(uid, message.text)
            count += 1
        except:
            pass
    await state.clear()
    await message.answer(f"✅ Xabar {count} ta foydalanuvchiga yuborildi.", reply_markup=main_menu(message.from_user.id))

# ✉️ DM
@dp.message(F.text == "✉️ DM (ID bo‘yicha)")
async def start_dm(message: types.Message, state: FSMContext):
    if message.from_user.id not in admins:
        return await message.answer("❌ Siz admin emassiz.")
    await message.answer("🎯 Qabul qiluvchi ID yuboring:", reply_markup=cancel_kb)
    await state.set_state(DMState.target_id)

@dp.message(DMState.target_id)
async def dm_get_id(message: types.Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        return await cancel_handler(message, state)
    try:
        await state.update_data(target_id=int(message.text.strip()))
        await message.answer("✍️ Ushbu ID ga yuboriladigan xabarni kiriting:", reply_markup=cancel_kb)
        await state.set_state(DMState.text)
    except:
        await message.answer("❌ Noto‘g‘ri ID.")

@dp.message(DMState.text)
async def dm_send_text(message: types.Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        return await cancel_handler(message, state)
    data = await state.get_data()
    target_id = data["target_id"]
    try:
        await bot.send_message(target_id, f"📬 Admin xabari:\n\n{message.text}")
        await message.answer(f"✅ Xabar {target_id} ga yuborildi.")
    except Exception as e:
        await message.answer(f"❌ Xabar yuborilmadi: {e}")
    await state.clear()

# ➕ Admin qo‘shish
@dp.message(F.text == "➕ Admin qo‘shish")
async def start_add_admin(message: types.Message, state: FSMContext):
    if message.from_user.id not in admins:
        return await message.answer("❌ Siz admin emassiz.")
    await message.answer("➕ Yangi admin ID yuboring:", reply_markup=cancel_kb)
    await state.set_state(AddAdminState.user_id)

@dp.message(AddAdminState.user_id)
async def add_admin_process(message: types.Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        return await cancel_handler(message, state)
    try:
        new_admin = int(message.text.strip())
        admins.add(new_admin)
        await message.answer(f"✅ <code>{new_admin}</code> admin sifatida qo‘shildi.", reply_markup=main_menu(message.from_user.id))
    except:
        await message.answer("❌ Xato ID.")
    await state.clear()

# ➖ Adminni olib tashlash
@dp.message(F.text == "➖ Adminni olib tashlash")
async def start_remove_admin(message: types.Message, state: FSMContext):
    if message.from_user.id not in admins:
        return await message.answer("❌ Siz admin emassiz.")
    await message.answer("➖ Olib tashlanadigan admin ID yuboring:", reply_markup=cancel_kb)
    await state.set_state(RemoveAdminState.user_id)

@dp.message(RemoveAdminState.user_id)
async def remove_admin_process(message: types.Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        return await cancel_handler(message, state)
    try:
        remove_admin = int(message.text.strip())

        # 🚫 Asosiy adminni olib tashlash mumkin emas
        if remove_admin in owners:
            await message.answer("❌ Asosiy adminni olib tashlash mumkin emas.", reply_markup=main_menu(message.from_user.id))
        elif remove_admin in admins:
            admins.remove(remove_admin)
            await message.answer(f"✅ <code>{remove_admin}</code> adminlikdan olib tashlandi.", reply_markup=main_menu(message.from_user.id))
        else:
            await message.answer("❌ Bu ID admin emas.")
    except:
        await message.answer("❌ Xato ID.")
    await state.clear()

# =========================
# 👮 Guruh nazorati
# =========================
@dp.message()
async def check_group_messages(message: types.Message):
    if message.chat.type in ("group", "supergroup"):
        joined_groups.add(message.chat.id)
        user_id = message.from_user.id

        # Agar ro‘yxatdan o‘tmagan bo‘lsa
        if user_id not in registered_users:
            try:
                # Xabarni o‘chirish
                await message.delete()

                # Foydalanuvchini vaqtincha cheklash
                await bot.restrict_chat_member(
                    chat_id=message.chat.id,
                    user_id=user_id,
                    permissions=ChatPermissions(can_send_messages=False),
                )

                # Ro‘yxatdan o‘tishga chaqirish
                me = await bot.get_me()
                invite_text = (
                    f"⚠️ <a href='tg://user?id={user_id}'>{message.from_user.full_name}</a>, "
                    f"iltimos avval @{me.username} botida <b>ro‘yxatdan o‘ting</b> "
                    f"so‘ng guruhda yozishingiz mumkin bo‘ladi."
                )
                await bot.send_message(message.chat.id, invite_text)

                # pending_unlock ro‘yxatiga qo‘shish
                if user_id not in pending_unlock:
                    pending_unlock[user_id] = []
                if message.chat.id not in pending_unlock[user_id]:
                    pending_unlock[user_id].append(message.chat.id)

                # oxirgi bloklangan guruhni saqlash
                last_blocked_group[user_id] = message.chat.id

            except Exception as e:
                logging.error(f"Guruh nazoratida xatolik: {e}")

# =========================
# 🔄 Run
# =========================
async def main():
    print("🤖 Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
