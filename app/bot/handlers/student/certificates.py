from aiogram import F, Router
from aiogram.types import CallbackQuery, FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession
import os
import logging

router = Router(name="student_certificates")
logger = logging.getLogger(__name__)


@router.message(F.text == "\U0001f4dc Sertifikatlarim")
async def my_certificates_list(message: Message, session: AsyncSession):
    """O'quvchining barcha sertifikatlarini ko'rsatish."""
    from app.database.repositories.certificate_repo import CertificateRepository
    from app.database.repositories.user_repo import UserRepository

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("Avval ro'yxatdan o'ting!")
        return

    cert_repo = CertificateRepository(session)
    certs = await cert_repo.get_by_user_id(user.id)

    if not certs:
        await message.answer(
            "\U0001f4dc <b>Sertifikatlarim</b>\n\n"
            "Hali sertifikatingiz yo'q.\n\n"
            "\U0001f3af Test topshirib, <b>70% va undan yuqori</b> natija to'plasangiz, "
            "avtomatik ravishda Diplom beriladi!",
            parse_mode="HTML"
        )
        return

    text = "\U0001f4dc <b>Mening Diplomlarim</b>\n\n"
    buttons = []

    for i, cert in enumerate(certs[:10], 1):
        result = cert.result
        test_title = ""
        if result and result.test:
            test_title = result.test.title[:40]
        elif result:
            test_title = f"Test #{result.test_id}"

        issued = cert.issued_at.strftime("%d.%m.%Y") if cert.issued_at else "Noma'lum"
        percent = result.percentage if result else 0

        if percent >= 90:
            tier = "\U0001f947 I Darajali G'olib"
        elif percent >= 75:
            tier = "\U0001f948 II Darajali G'olib"
        elif percent >= 60:
            tier = "\U0001f949 III Darajali G'olib"
        else:
            tier = "\U0001f4dc Ishtirokchi"

        text += (
            f"<b>{i}.</b> {tier}\n"
            f"   \U0001f4cb <i>{test_title}</i>\n"
            f"   \U0001f4ca {percent}% | \U0001f4c5 {issued}\n"
            f"   \U0001f522 ID: <code>{cert.certificate_number}</code>\n\n"
        )
        buttons.append([
            InlineKeyboardButton(
                text=f"\U0001f4e5 {i}-Diplomni yuklab olish",
                callback_data=f"download_cert:{cert.certificate_number}"
            )
        ])

    if len(certs) > 10:
        text += f"\n<i>(Jami {len(certs)} ta sertifikat)</i>"

    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")


@router.callback_query(F.data.startswith("download_cert:"))
async def download_certificate_callback(callback: CallbackQuery, session: AsyncSession):
    """O'quvchi o'zining sertifikatini yuklab oladi."""
    await callback.answer("\U0001f4e5 Diplom tayyorlanmoqda...")
    cert_id = callback.data.split(":", 1)[1]

    from app.database.repositories.certificate_repo import CertificateRepository
    from app.database.repositories.user_repo import UserRepository

    cert_repo = CertificateRepository(session)
    cert = await cert_repo.get_by_certificate_number(cert_id)

    if not cert:
        await callback.message.answer("\u26a0\ufe0f Sertifikat topilmadi.")
        return

    # Fayl mavjudligini tekshiramiz
    cert_path = cert.pdf_path if cert.pdf_path else f"/tmp/certificates/certificate_{cert_id}.png"

    if not os.path.exists(cert_path):
        # Qayta generatsiya
        try:
            from app.services.certificate_generator import generate_certificate
            from app.database.repositories.result_repo import ResultRepository
            result_repo = ResultRepository(session)
            result = await result_repo.get_by_id(cert.result_id)
            if result:
                user_repo = UserRepository(session)
                user = await user_repo.get_by_id(result.user_id)
                full_name = user.full_name if user else "O'quvchi"
                total = result.correct_count + result.incorrect_count + result.unanswered_count
                exam_title = "MATEMATIKA VA IQ TEST"
                if result.test:
                    exam_title = result.test.title[:60]
                cert_path = generate_certificate(
                    full_name=full_name,
                    percent=int(result.percentage),
                    correct=result.correct_count,
                    total=max(total, 1),
                    cert_id=cert_id,
                    date_str=cert.issued_at.strftime("%d.%m.%Y") if cert.issued_at else None,
                    exam_title=exam_title,
                )
        except Exception as e:
            logger.error(f"Sertifikat qayta generatsiya xatoligi: {e}")
            await callback.message.answer(f"\u274c Xatolik: {e}")
            return

    try:
        await callback.message.answer_photo(
            FSInputFile(cert_path),
            caption=(
                f"\U0001f3c6 <b>Sizning Diplomingiz!</b>\n\n"
                f"\U0001f522 ID: <code>{cert_id}</code>\n"
                f"\U0001f4e5 Saqlang va do'stlaringizga ulashing!"
            ),
            parse_mode="HTML"
        )
    except Exception:
        try:
            await callback.message.answer_document(
                FSInputFile(cert_path),
                caption=f"\U0001f3c6 Diplom | ID: <code>{cert_id}</code>",
                parse_mode="HTML"
            )
        except Exception as e2:
            await callback.message.answer(f"\u274c Yuborishda xatolik: {e2}")
