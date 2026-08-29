from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def get_student_main_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text="\u2705 Javobni tekshirish")],
        [KeyboardButton(text="\U0001f4ca Natijalarim"), KeyboardButton(text="\U0001f3c6 Reyting")],
        [KeyboardButton(text="\U0001f4dc Sertifikatlarim"), KeyboardButton(text="\U0001f4d8 Qo'llanma")],
        [KeyboardButton(text="\U0001f464 Profilim")],
    ]
    if is_admin:
        keyboard.append([KeyboardButton(text="\U0001f468\u200d\U0001f4bc Admin Paneli")])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def get_admin_main_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text="\u2795 Yangi test yaratish"), KeyboardButton(text="\U0001f511 Tezkor kalit qo'shish")],
        [KeyboardButton(text="\U0001f4dd Testlar boshqaruvi"), KeyboardButton(text="\U0001f4ca Statistika")],
        [KeyboardButton(text="\U0001f465 O'quvchilar"), KeyboardButton(text="\u2699\ufe0f Sozlamalar")],
        [KeyboardButton(text="\U0001f4e2 Xabar yuborish"), KeyboardButton(text="\U0001f3e0 O'quvchi rejimi")],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="\u274c Bekor qilish")],
            [KeyboardButton(text="\U0001f3e0 Bosh menyu")]
        ],
        resize_keyboard=True
    )


def get_phone_request_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="\U0001f4de Telefon raqamni yuborish", request_contact=True)],
            [KeyboardButton(text="\u2b05\ufe0f Ortga"), KeyboardButton(text="\u274c Bekor qilish")]
        ],
        resize_keyboard=True
    )


def get_step_back_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="\u2b05\ufe0f Ortga"), KeyboardButton(text="\u274c Bekor qilish")]
        ],
        resize_keyboard=True
    )
