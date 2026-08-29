from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery, FSInputFile,
    InlineKeyboardButton, InlineKeyboardMarkup, Message,
)
from sqlalchemy.ext.asyncio import AsyncSession
import os
import uuid
import logging
from datetime import datetime

router = Router(name="student_certificates")
logger = logging.getLogger(__name__)


@router.message(
    StateFilter("*"),
    F.text.in_([
        "📜 Sertifikatlarim",
        "📜 Sertifikatlar",
        "Sertifikatlarim",
        "Sertifikatlar",
        "/certificates",
        "/sertifikatlar",
        "/sertifikat",
    ])
)
async def my_certificates_list(message: Message, state: FSMContext, session: AsyncSession):
    """O'quvchining barcha sertifikatlarini ro'yxatini ko'rsatadi."""
    await state.clear()
    from app.database.repositories.certificate_repo import CertificateRepository
    from app.database.repositories.user_repo import UserRepository

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer(
            "⚠️ Avval ro'yxatdan o'ting!\n"
            "/start buyrug'ini yuboring."
        )
        return

    cert_repo = CertificateRepository(session)
    certs = await cert_repo.get_user_certificates(user.id)

    if not certs:
        await message.answer(
            "📜 <b>Sertifikatlarim</b>\n\n"
            "Sizda hali sertifikat yo'q.\n\n"
            "🎯 Test topshirib, <b>70% va undan yuqori</b> "
            "natija to'plasangiz, avtomatik ravishda Diplom beriladi!\n\n"
            "✅ <i>Testga kirish uchun \"Javobni tekshirish\" tugmasini bosing.</i>",
            parse_mode="HTML"
        )
        return

    text = "📜 <b>Mening Diplomlarim</b>\n\n"
    buttons = []

    for i, cert in enumerate(certs[:10], 1):
        test_title = ""
        if cert.test:
            test_title = cert.test.title[:40]

        issued = cert.issued_at.strftime("%d.%m.%Y") if cert.issued_at else "Noma'lum"
        pct = int(cert.percentage or 0)

        if pct >= 90:
            tier = "🥇 I Darajali G'olib"
        elif pct >= 75:
            tier = "🥈 II Darajali G'olib"
        else:
            tier = "🥉 III Darajali G'olib"

        text += (
            f"<b>{i}.</b> {tier}\n"
            f"   📋 <i>{test_title}</i>\n"
            f"   📊 {pct}% | 📅 {issued}\n"
            f"   🔢 ID: <code>{cert.certificate_number}</code>\n\n"
        )
        buttons.append([
            InlineKeyboardButton(
                text=f"📥 {i}-Diplomni yuklab olish",
                callback_data=f"download_cert:{cert.certificate_number}"
            )
        ])

    if len(certs) > 10:
        text += f"\n<i>(Jami {len(certs)} ta sertifikat, oxirgi 10 tasi ko'rsatilmoqda)</i>"

    kb = InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("download_cert:"))
async def download_certificate_callback(callback: CallbackQuery, session: AsyncSession):
    """O'quvchi o'zining sertifikatini yuklab oladi."""
    await callback.answer("📥 Diplom tayyorlanmoqda...")
    cert_id = callback.data.split(":", 1)[1]

    from app.database.repositories.certificate_repo import CertificateRepository
    from app.database.repositories.result_repo import ResultRepository
    from app.database.repositories.user_repo import UserRepository

    cert_repo = CertificateRepository(session)
    cert = await cert_repo.get_by_number(cert_id)

    if not cert:
        await callback.message.answer(
            "⚠️ Sertifikat topilmadi.\n"
            f"ID: <code>{cert_id}</code>",
            parse_mode="HTML"
        )
        return

    cert_path = cert.pdf_path or f"/tmp/certificates/certificate_{cert_id}.png"

    if not os.path.exists(cert_path):
        try:
            from app.services.certificate_generator import generate_certificate
            result_repo = ResultRepository(session)
            user_repo = UserRepository(session)
            result = await result_repo.get_by_id(cert.result_id)
            user = await user_repo.get_by_id(cert.user_id)

            full_name = user.full_name if user else "O'quvchi"
            total = 40
            correct = 0
            pct = int(cert.percentage or 70)

            if result:
                correct = result.correct_count
                total = max(
                    result.correct_count + result.incorrect_count + result.unanswered_count,
                    1
                )

            exam_title = cert.test.title[:60] if cert.test else "MATEMATIKA VA IQ TEST"
            date_str = cert.issued_at.strftime("%d.%m.%Y") if cert.issued_at else datetime.now().strftime("%d.%m.%Y")

            cert_path = generate_certificate(
                full_name=full_name,
                percent=pct,
                correct=correct,
                total=total,
                cert_id=cert_id,
                date_str=date_str,
                exam_title=exam_title,
            )
        except Exception as e:
            logger.error(f"Sertifikat qayta generatsiya xatoligi: {e}")
            await callback.message.answer(
                "❌ Diplomni tayyorlashda xatolik yuz berdi.\n"
                "Iltimos keyinroq urinib ko'ring yoki adminga murojaat qiling."
            )
            return

    try:
        await callback.message.answer_photo(
            FSInputFile(cert_path),
            caption=(
                "🏆 <b>Sizning Diplomingiz!</b>\n\n"
                f"🔢 <b>Sertifikat ID:</b> <code>{cert_id}</code>\n"
                f"📊 <b>Natija:</b> {int(cert.percentage or 0)}%\n\n"
                "📥 Saqlang va do'stlaringizga ulashing!"
            ),
            parse_mode="HTML"
        )
    except Exception:
        try:
            await callback.message.answer_document(
                FSInputFile(cert_path),
                caption=f"🏆 <b>Diplom</b> | ID: <code>{cert_id}</code>",
                parse_mode="HTML"
            )
        except Exception as e2:
            await callback.message.answer(f"❌ Yuborishda xatolik: {e2}")
