import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, ChatMemberUpdatedFilter, IS_MEMBER, IS_NOT_MEMBER
from aiogram.types import (
    ChatPermissions,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.client.default import DefaultBotProperties

# 🔹 Bot sozlamalari
BOT_TOKEN = "6335576043:AAG9s9vmorxeHakm-uZ5-Jb3SRZGqRX2e7I"
SUPER_ADMIN_ID = 6060353145
DATABASE_CHANNEL = -1003085828839   # To‘g‘ri kanal ID (-100 bilan)

# 🔹 Logging
logging.basicConfig(level=logging.INFO)

# 🔹 Bot va Dispatcher
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher(storage=MemoryStorage())

# 🔹 Ma’lumotlar
registered_users = set()
joined_groups = set()
last_blocked_group = {}  # user_id -> chat_id
admins = {SUPER_ADMIN_ID}


# 🔹 Ro'yxatdan o'tish formasi
class RegisterForm(StatesGroup):
    fullname = State()
    age = State()
    phone = State()
    about = State()


# ✅ /start
@dp.message(Command("start"))
async def start_handler(message: types.Message, state: FSMContext):
    if message.chat.type != "private":
        return

    keyboard = [
        [KeyboardButton(text="Ro'yxatdan o'tish")],
        [KeyboardButton(text="👨‍💻 Dasturchi")],
    ]
    if message.from_user.id in admins:
        keyboard.append([KeyboardButton(text="🛠 Admin panel")])

    kb = ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True
    )

    await message.answer("👋 Salom!\n\nRo‘yxatdan o‘tish yoki bo‘limni tanlang.", reply_markup=kb)


# ✅ Dasturchi haqida
@dp.message(F.text == "👨‍💻 Dasturchi")
async def dev_info(message: types.Message):
    if message.chat.type != "private":
        return
    await message.answer(
        "👨‍💻 Dasturchi: <b>Jasurbek</b>\n\n"
        "📩 Telegram: @serinaqu\n\n"
        "📹 Youtube: https://www.youtube.com/@Jasurbek_Jolanboyev\n\n"
        "🔗 Instagram: https://www.instagram.com/jasurbek.official.uz\n\n"
        "💻 Loyihalar bo‘yicha murojaat qilishingiz mumkin."
    )


# ✅ Ro'yxatdan o'tish
@dp.message(F.text == "Ro'yxatdan o'tish")
async def start_register(message: types.Message, state: FSMContext):
    if message.chat.type != "private":
        return

    if message.from_user.id in registered_users:
        return await message.answer("✅ Siz allaqachon ro‘yxatdan o‘tgansiz!")

    await message.answer("Ism va familiyangizni kiriting:")
    await state.set_state(RegisterForm.fullname)


@dp.message(RegisterForm.fullname)
async def process_fullname(message: types.Message, state: FSMContext):
    await state.update_data(fullname=message.text)
    await message.answer("Yoshingizni kiriting:")
    await state.set_state(RegisterForm.age)


@dp.message(RegisterForm.age)
async def process_age(message: types.Message, state: FSMContext):
    await state.update_data(age=message.text)
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📞 Telefon raqamni yuborish", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer("Telefon raqamingizni tugma orqali yuboring:", reply_markup=kb)
    await state.set_state(RegisterForm.phone)


@dp.message(RegisterForm.phone, F.contact)
async def process_phone_contact(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.contact.phone_number)
    await message.answer("O‘zingiz haqingizda qisqacha yozing:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(RegisterForm.about)


@dp.message(RegisterForm.phone)
async def process_phone_text(message: types.Message, state: FSMContext):
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📞 Telefon raqamni yuborish", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer("❗ Iltimos, telefon raqamingizni <b>tugma orqali</b> yuboring.", reply_markup=kb)


@dp.message(RegisterForm.about)
async def process_about(message: types.Message, state: FSMContext):
    global DATABASE_CHANNEL
    await state.update_data(about=message.text)
    data = await state.get_data()

    fullname = data.get("fullname")
    age = data.get("age")
    phone = data.get("phone")
    about = data.get("about")

    text = (
        f"📝 Yangi foydalanuvchi:\n\n"
        f"👤 Ism Familiya: {fullname}\n"
        f"📅 Yosh: {age}\n"
        f"📱 Telefon: {phone}\n"
        f"ℹ️ Qo‘shimcha: {about}\n"
        f"🔗 Telegram: @{message.from_user.username if message.from_user.username else 'yo‘q'}\n"
        f"🆔 ID: <code>{message.from_user.id}</code>"
    )

    try:
        await bot.send_message(DATABASE_CHANNEL, text)
    except Exception as e:
        logging.error(f"Kanalga yuborishda xato: {e}")
        return await message.answer("❌ Kanalga yuborishda xato. Botni kanalga admin qilib qo‘ying.")

    registered_users.add(message.from_user.id)
    await message.answer("✅ Siz muvaffaqiyatli ro‘yxatdan o‘tdingiz!")

    chat_id = last_blocked_group.pop(message.from_user.id, None)
    if chat_id:
        try:
            await bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=message.from_user.id,
                permissions=ChatPermissions(can_send_messages=True)
            )
            await bot.send_message(chat_id, f"✅ {message.from_user.full_name}, endi guruhda yozishingiz mumkin!")
        except Exception as e:
            logging.error(f"Cheklovni yechishda xato: {e}")

    await state.clear()


# ✅ Guruhdagi xabarlarni tekshirish
@dp.message()
async def check_group_messages(message: types.Message):
    if message.chat.type in ["group", "supergroup"]:
        user_id = message.from_user.id
        if user_id not in registered_users:
            last_blocked_group[user_id] = message.chat.id
            try:
                await message.delete()
                await bot.restrict_chat_member(
                    chat_id=message.chat.id,
                    user_id=user_id,
                    permissions=ChatPermissions(can_send_messages=False)
                )
            except Exception as e:
                logging.error(f"O‘chirish/cheklashda xato: {e}")

            mention = (
                f"@{message.from_user.username}"
                if message.from_user.username
                else f'<a href="tg://user?id={user_id}">{message.from_user.full_name}</a>'
            )
            try:
                await bot.send_message(
                    message.chat.id,
                    f"⚠️ {mention}, avval botda ro‘yxatdan o‘ting 👉 @Vscoder_bot"
                )
            except Exception as e:
                logging.error(f"Ogohlantirish xabarida xato: {e}")


# ✅ Bot guruhga qo'shilganda
@dp.my_chat_member(ChatMemberUpdatedFilter(IS_NOT_MEMBER >> IS_MEMBER))
async def bot_joined(update: types.ChatMemberUpdated):
    if update.new_chat_member.user.id == (await bot.get_me()).id:
        joined_groups.add(update.chat.id)


# ✅ Bot guruhdan chiqarilganda
@dp.my_chat_member(ChatMemberUpdatedFilter(IS_MEMBER >> IS_NOT_MEMBER))
async def bot_left(update: types.ChatMemberUpdated):
    if update.new_chat_member.user.id == (await bot.get_me()).id:
        joined_groups.discard(update.chat.id)


# ✅ Admin panel faqat /admin komandasi orqali
@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.chat.type != "private":
        return
    if message.from_user.id not in admins:
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Statistika", callback_data="stats")],
        [InlineKeyboardButton(text="📢 Xabar yuborish", callback_data="broadcast")],
        [InlineKeyboardButton(text="👥 Guruhlar", callback_data="groups")],
        [InlineKeyboardButton(text="➕ Admin qo‘shish", callback_data="add_admin")],
    ])
    await message.answer("🛠 Admin panel", reply_markup=kb)


# ✅ Admin panel tugmasi orqali
@dp.message(F.text == "🛠 Admin panel")
async def admin_panel_text(message: types.Message):
    if message.chat.type != "private":
        return
    if message.from_user.id not in admins:
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Statistika", callback_data="stats")],
        [InlineKeyboardButton(text="📢 Xabar yuborish", callback_data="broadcast")],
        [InlineKeyboardButton(text="👥 Guruhlar", callback_data="groups")],
        [InlineKeyboardButton(text="➕ Admin qo‘shish", callback_data="add_admin")],
    ])
    await message.answer("🛠 Admin panel", reply_markup=kb)


# 📊 Statistika
@dp.callback_query(F.data == "stats")
async def stats(call: types.CallbackQuery):
    if call.from_user.id not in admins:
        return
    await call.answer()
    await call.message.answer(f"📊 Foydalanuvchilar soni: {len(registered_users)}")


# 👥 Guruhlar
@dp.callback_query(F.data == "groups")
async def groups(call: types.CallbackQuery):
    if call.from_user.id not in admins:
        return
    await call.answer()
    if not joined_groups:
        return await call.message.answer("❌ Hozircha guruhga qo‘shilmaganman.")
    txt = "👥 Bot qo‘shilgan guruhlar:\n\n"
    for g in list(joined_groups):
        try:
            chat = await bot.get_chat(g)
            txt += f"• {chat.title} (<code>{g}</code>)\n"
        except Exception as e:
            logging.error(f"Guruh ma'lumotini olishda xato: {e}")
            joined_groups.discard(g)
    await call.message.answer(txt)


# 📢 Broadcast
class BroadcastState(StatesGroup):
    text = State()

@dp.callback_query(F.data == "broadcast")
async def broadcast_start(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id not in admins:
        return
    await call.answer()
    await call.message.answer("✍️ Yuboriladigan xabarni kiriting:")
    await state.set_state(BroadcastState.text)


@dp.message(BroadcastState.text)
async def process_broadcast(message: types.Message, state: FSMContext):
    if message.from_user.id not in admins:
        return
    text = message.text
    count = 0
    for user_id in list(registered_users):
        try:
            await bot.send_message(user_id, text)
            count += 1
        except:
            pass
    await message.answer(f"✅ Xabar {count} ta foydalanuvchiga yuborildi.")
    await state.clear()


# ➕ Admin qo‘shish
class AddAdminState(StatesGroup):
    user_id = State()

@dp.callback_query(F.data == "add_admin")
async def add_admin_start(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id not in admins:
        return
    await call.answer()
    await call.message.answer("➕ Yangi adminning Telegram ID raqamini yuboring:")
    await state.set_state(AddAdminState.user_id)


@dp.message(AddAdminState.user_id)
async def add_admin_process(message: types.Message, state: FSMContext):
    if message.from_user.id not in admins:
        return
    try:
        new_admin = int(message.text.strip())
        admins.add(new_admin)
        await message.answer(f"✅ <code>{new_admin}</code> adminlar ro‘yxatiga qo‘shildi.")
    except:
        await message.answer("❌ Xato ID")
    await state.clear()


# 🔹 Botni ishga tushirish
async def main():
    print("🤖 Bot ishga tushdi...")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())