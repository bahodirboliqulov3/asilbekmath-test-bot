from aiogram import F, Router
from aiogram.types import CallbackQuery, FSInputFile, Message
from sqlalchemy.ext.asyncio import AsyncSession
from app.bot.filters.admin_filter import IsAdminFilter
from app.database.repositories.certificate_repo import CertificateRepository
from app.database.repositories.user_repo import AdminRepository
import os

router = Router(name="student_certificates")


@router.callback_query(F.data.startswith("download_cert:"))
async def download_certificate_callback(callback: CallbackQuery, session: AsyncSession):
    """O'quvchi o'zining sertifikatini qayta yuklab oladi."""
    await callback.answer()
    cert_id = callback.data.split(":", 1)[1]

    cert_repo = CertificateRepository(session)
    cert = await cert_repo.get_by_certificate_number(cert_id)

    if not cert:
        await callback.message.answer("⚠️ Sertifikat topilmadi.")
        return

    # Fayl mavjudligini tekshir, yo'q bo'lsa qayta yaratamiz
    pdf_path = cert.pdf_path if cert.pdf_path else f"/tmp/certificates/certificate_{cert_id}.png"
    if not os.path.exists(pdf_path):
        await callback.message.answer("🔄 Sertifikat qayta yaratilmoqda...")
        try:
            from app.services.certificate_generator import generate_certificate
            from app.database.repositories.result_repo import ResultRepository
            from app.database.repositories.user_repo import AdminRepository as UserRepo
            result_repo = ResultRepository(session)
            result = await result_repo.get_by_id(cert.result_id)
            if result:
                user_repo = UserRepo(session)
                user = await user_repo.get_by_id(result.user_id)
                pdf_path = generate_certificate(
                    full_name=user.full_name if user else "O'quvchi",
                    percent=result.percentage,
                    correct=result.correct_count,
                    total=result.total_count,
                    cert_id=cert_id,
                    date_str=cert.issued_at.strftime("%d.%m.%Y") if cert.issued_at else None,
                )
        except Exception as e:
            await callback.message.answer(f"❌ Xatolik: {e}")
            return

    try:
        await callback.message.answer_photo(
            FSInputFile(pdf_path),
            caption=(
                f"🏆 <b>Sizning Diplomingiz!</b>\n\n"
                f"🔢 ID: <code>{cert_id}</code>\n"
                f"📅 Sertifikat saqlab qo'ying va do'stlaringizga yuboring!"
            ),
            parse_mode="HTML"
        )
    except Exception:
        await callback.message.answer_document(
            FSInputFile(pdf_path),
            caption=f"🏆 Sizning Diplomingiz! ID: <code>{cert_id}</code>",
            parse_mode="HTML"
        )
