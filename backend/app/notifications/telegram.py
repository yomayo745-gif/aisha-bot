from aiogram import Bot
from app.core.config import settings
from app.bot.keyboards.admin_kb import get_new_order_keyboard
from app.models.models import Order
import logging

logger = logging.getLogger(__name__)

async def notify_admin_new_order(order: Order, items_text: str, customer_telegram_id: int = None, image_url: str = None):
    """
    Sends a new order notification to the admin via Telegram with product photo.
    """
    if not settings.BOT_TOKEN or settings.BOT_TOKEN == "dummy_token":
        logger.warning("BOT_TOKEN is not configured. Cannot send notification.")
        return

    import os
    admin_ids_str = os.getenv("ADMIN_TELEGRAM_IDS", settings.ADMIN_TELEGRAM_IDS)
    if not admin_ids_str:
        logger.warning("ADMIN_TELEGRAM_IDS is not configured. Cannot send notification.")
        return
        
    admin_ids = [int(id_str.strip()) for id_str in admin_ids_str.split(",") if id_str.strip().isdigit()]
    
    bot = Bot(token=settings.BOT_TOKEN)
    
    delivery_str = "Ha" if order.requires_delivery else "Yo'q"
    assembly_str = "Ha" if order.requires_assembly else "Yo'q"
    
    text = (
        f"🛍 <b>YANGI BUYURTMA</b>\n\n"
        f"🆔 <b>Buyurtma:</b> {order.order_number}\n\n"
        f"👤 <b>Mijoz:</b> {order.customer_name}\n"
        f"📞 <b>Telefon:</b> {order.customer_phone}\n"
        f"📍 <b>Manzil:</b> {order.customer_address or 'Kiritilmagan'}\n\n"
        f"🛒 <b>Mahsulotlar:</b>\n{items_text}\n"
        f"💰 <b>Jami summa:</b> {order.total_amount:,.0f} so'm\n\n"
        f"🚚 <b>Yetkazib berish:</b> {delivery_str}\n"
        f"🔧 <b>Montaj:</b> {assembly_str}\n"
    )
    if order.customer_note:
        text += f"📝 <b>Izoh:</b> {order.customer_note}\n"

    import os
    from aiogram.types import FSInputFile, URLInputFile

    photo_to_send = None
    if image_url:
        image_url = image_url.replace("aishamebel-production.up.railway.app", "aisha-mebel-production.up.railway.app")
        if "/uploads/" in image_url:
            local_rel = image_url.split("/uploads/")[1]
            local_path = os.path.join("uploads", local_rel)
            if os.path.exists(local_path):
                photo_to_send = FSInputFile(local_path)
            else:
                photo_to_send = URLInputFile(image_url)
        elif image_url.startswith("http://") or image_url.startswith("https://"):
            photo_to_send = URLInputFile(image_url)
        else:
            photo_to_send = image_url

    try:
        for admin_id in admin_ids:
            try:
                sent = False
                if photo_to_send:
                    try:
                        await bot.send_photo(
                            chat_id=admin_id,
                            photo=photo_to_send,
                            caption=text[:1024],
                            reply_markup=get_new_order_keyboard(order.id, customer_telegram_id, order.customer_phone),
                            parse_mode="HTML"
                        )
                        sent = True
                        logger.info(f"Photo notification sent to admin {admin_id} for order {order.id}")
                    except Exception as pe:
                        logger.warning(f"Could not send photo to admin {admin_id}: {pe}")
                        
                if not sent:
                    await bot.send_message(
                        chat_id=admin_id,
                        text=text,
                        reply_markup=get_new_order_keyboard(order.id, customer_telegram_id, order.customer_phone),
                        parse_mode="HTML"
                    )
                    logger.info(f"Text notification sent to admin {admin_id} for order {order.id}")
            except Exception as ae:
                logger.error(f"Failed to deliver notification to admin {admin_id}: {ae}")
    finally:
        await bot.session.close()

async def notify_admin_individual_order(
    customer_name: str,
    customer_phone: str,
    furniture_type: str,
    dimensions: str = None,
    material: str = None,
    colors: str = None,
    customer_note: str = None,
    customer_telegram_id: int = None,
    reference_image_url: str = None
):
    if not settings.BOT_TOKEN or settings.BOT_TOKEN == "dummy_token":
        return
    admin_ids_str = settings.ADMIN_TELEGRAM_IDS
    if not admin_ids_str:
        return
    admin_ids = [int(id_str.strip()) for id_str in admin_ids_str.split(",") if id_str.strip().isdigit()]
    bot = Bot(token=settings.BOT_TOKEN)
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton, FSInputFile
    builder = InlineKeyboardBuilder()
    if customer_telegram_id:
        builder.row(InlineKeyboardButton(text="💬 Mijoz bilan bog'lanish", url=f"tg://user?id={customer_telegram_id}"))
    
    text = (
        "📐 <b>YANGI INDIVIDUAL BUYURTMA!</b>\n\n"
        f"👤 <b>Mijoz:</b> {customer_name}\n"
        f"📞 <b>Telefon:</b> {customer_phone}\n\n"
        f"🛋 <b>Mebel turi:</b> {furniture_type}\n"
        f"📏 <b>O'lchamlari:</b> {dimensions or 'Kelishiladi'}\n"
        f"🪵 <b>Material:</b> {material or 'Kelishiladi'}\n"
        f"🎨 <b>Rangi/Dizayn:</b> {colors or 'Kelishiladi'}\n"
    )
    if customer_note:
        text += f"📝 <b>Mijoz izohi:</b> {customer_note}\n"

    photo_to_send = None
    if reference_image_url:
        import os
        from aiogram.types import URLInputFile
        reference_image_url = reference_image_url.replace("aishamebel-production.up.railway.app", "aisha-mebel-production.up.railway.app")
        if "/uploads/" in reference_image_url:
            local_rel = reference_image_url.split("/uploads/")[1]
            local_path = os.path.join("uploads", local_rel)
            if os.path.exists(local_path):
                photo_to_send = FSInputFile(local_path)
            else:
                photo_to_send = URLInputFile(reference_image_url)
        elif reference_image_url.startswith("http://") or reference_image_url.startswith("https://"):
            photo_to_send = URLInputFile(reference_image_url)
        else:
            photo_to_send = reference_image_url
        
    try:
        for admin_id in admin_ids:
            try:
                sent = False
                if photo_to_send:
                    try:
                        await bot.send_photo(
                            chat_id=admin_id,
                            photo=photo_to_send,
                            caption=text[:1024],
                            reply_markup=builder.as_markup() if customer_telegram_id else None,
                            parse_mode="HTML"
                        )
                        sent = True
                        logger.info(f"Individual order photo sent to admin {admin_id}")
                    except Exception as pe:
                        logger.warning(f"Failed to send individual order photo to admin {admin_id}: {pe}")
                if not sent:
                    await bot.send_message(
                        chat_id=admin_id,
                        text=text,
                        reply_markup=builder.as_markup() if customer_telegram_id else None,
                        parse_mode="HTML"
                    )
                    logger.info(f"Individual order text sent to admin {admin_id}")
            except Exception as e:
                logger.error(f"Failed to deliver individual order to admin {admin_id}: {e}")
    finally:
        await bot.session.close()

STATUS_UZ = {
    "new": "Yangi qabul qilindi",
    "contacted": "Bog'lanildi",
    "confirmed": "Tasdiqlandi",
    "in_production": "Ishlab chiqarishda (tayyorlanmoqda)",
    "ready": "Tayyor bo'ldi",
    "delivering": "Yetkazilmoqda (yo'lda)",
    "delivered": "Yetkazib berildi va topshirildi",
    "cancelled": "Bekor qilindi"
}

async def notify_customer_status_change(customer_telegram_id: int, order_number: str, new_status: str, note: str = None):
    if not customer_telegram_id or not settings.BOT_TOKEN or settings.BOT_TOKEN == "dummy_token":
        return
        
    bot = Bot(token=settings.BOT_TOKEN)
    status_label = STATUS_UZ.get(str(new_status).lower(), new_status)
    
    text = (
        f"🛋 <b>AISHA MEBEL</b>\n\n"
        f"Hurmatli mijoz, sizning <b>{order_number}</b> raqamli buyurtmangiz holati yangilandi:\n\n"
        f"📌 <b>Yangi holat:</b> {status_label}\n"
    )
    if note:
        text += f"📝 <b>Izoh:</b> {note}\n"
    text += "\nSavollaringiz bo'lsa, biz bilan bog'lanishingiz mumkin:\n📞 880606040, 934124604"
        
    try:
        await bot.send_message(
            chat_id=customer_telegram_id,
            text=text,
            parse_mode="HTML"
        )
        logger.info(f"Status change notification sent to customer {customer_telegram_id}")
    except Exception as e:
        logger.error(f"Failed to notify customer {customer_telegram_id}: {e}")
    finally:
        await bot.session.close()
