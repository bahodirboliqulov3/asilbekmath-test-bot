import logging
from collections.abc import Awaitable, Callable
from typing import Any, Dict
from aiogram import BaseMiddleware, Bot
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, TelegramObject, Update
from sqlalchemy.ext.asyncio import AsyncSession
from app.bot.storage.subscription_tracker import SubscriptionTracker
from app.config import settings
from app.services.auth_service import AuthService
from app.services.channel_service import ChannelService

logger = logging.getLogger(__name__)


class RequiredChannelMiddleware(BaseMiddleware):
    """
    In-Memory tezkori obuna tekshiruvi (0ms kechikish).
    Telegram API'ni har bir xabarda qayta-qayta chaqirib qotib qolishni oldini oladi.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        real_event = event
        if isinstance(event, Update):
            real_event = event.message or event.callback_query or event.chat_member or event.my_chat_member
            if not real_event:
                return await handler(event, data)

        if not isinstance(real_event, (Message, CallbackQuery)):
            return await handler(event, data)

        user = data.get("event_from_user")
        bot: Bot = data.get("bot")
        session: AsyncSession = data.get("session")

        if not user or not bot or not session:
            return await handler(event, data)

        # 1. Adminlarni hech qachon bloklamaslik
        auth_service = AuthService(session)
        is_admin = (user.id == settings.OWNER_ID) or await auth_service.is_admin(user.id)
        if is_admin:
            return await handler(event, data)

        # 2. /start, /admin buyruqlari va tekshirish tugmalariga ruxsat berish
        if isinstance(real_event, Message) and real_event.text and (real_event.text.startswith("/start") or real_event.text.startswith("/admin")):
            return await handler(event, data)
        if isinstance(real_event, CallbackQuery) and (
            real_event.data == "check_channel_subs" 
            or (real_event.data and real_event.data.startswith("check_channel_subs"))
            or (real_event.data and real_event.data.startswith("adm_"))
            or real_event.data in ["cancel", "noop"]
        ):
            return await handler(event, data)

        # 3. ⚡ TEZKOR IN-MEMORY TEKSHIRUV: Agar foydalanuvchi tasdiqlangan bo'lsa (0ms kechikish)
        if SubscriptionTracker.is_verified(user.id):
            return await handler(event, data)

        # 4. Agar hali tekshirilmagan yoki obuna bo'lmagan bo'lsa: API orqali tekshirish
        channel_service = ChannelService(session)
        is_subbed, unsubs = await channel_service.check_user_subscriptions(bot, user.id)

        if is_subbed:
            SubscriptionTracker.mark_subscribed(user.id)
            return await handler(event, data)

        SubscriptionTracker.mark_unsubscribed(user.id)

        if unsubs:
            buttons = []
            for ch in unsubs:
                buttons.append([InlineKeyboardButton(text=f"📢 {ch.title}", url=ch.invite_link)])
            buttons.append([
                InlineKeyboardButton(text="✅ A'zo bo'ldim, tekshirish", callback_data="check_channel_subs")
            ])
            kb = InlineKeyboardMarkup(inline_keyboard=buttons)

            msg_text = (
                "⛔ <b>Botdan foydalanish uchun quyidagi kanallarga a'zo bo'ling!</b>\n\n"
                "A'zo bo'lgach, <b>✅ A'zo bo'ldim, tekshirish</b> tugmasini bosing."
            )

            if isinstance(real_event, Message):
                await real_event.answer(msg_text, reply_markup=kb, parse_mode="HTML")
            elif isinstance(real_event, CallbackQuery):
                await real_event.answer("⛔ Avval kanallarga a'zo bo'ling!", show_alert=True)
                try:
                    await bot.send_message(chat_id=user.id, text=msg_text, reply_markup=kb, parse_mode="HTML")
                except Exception:
                    pass
            return

        return await handler(event, data)
