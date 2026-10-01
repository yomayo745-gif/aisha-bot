from aiogram import Router, F, types
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from app.db.database import AsyncSessionLocal
from app.models.models import Order, Category, Product, ProductImage
from sqlalchemy import select, func
from app.core.config import settings
from app.bot.keyboards.admin_kb import get_main_admin_keyboard, get_cancel_admin_keyboard
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()

class AddCategory(StatesGroup):
    waiting_for_name = State()

class EditCategory(StatesGroup):
    waiting_for_new_name = State()
    waiting_for_new_icon = State()

class AddProduct(StatesGroup):
    waiting_for_category = State()
    waiting_for_name = State()
    waiting_for_desc = State()
    waiting_for_price = State()
    waiting_for_photo = State()

class EditProduct(StatesGroup):
    waiting_for_new_price = State()
    waiting_for_new_name = State()
    waiting_for_new_desc = State()
    waiting_for_new_photo = State()
    waiting_for_new_stock = State()
    waiting_for_new_video = State()

import os

def is_admin(telegram_id: int) -> bool:
    admin_ids_str = os.getenv("ADMIN_TELEGRAM_IDS", settings.ADMIN_TELEGRAM_IDS)
    if not admin_ids_str:
        return False
    admin_ids = [int(id_str.strip()) for id_str in admin_ids_str.split(",") if id_str.strip().isdigit()]
    return telegram_id in admin_ids

@router.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer(
            f"⛔️ <b>Siz admin emassiz!</b>\nSizning Telegram ID'ingiz: <code>{message.from_user.id}</code>",
            parse_mode="HTML"
        )
        return
    await message.answer(
        "👋 <b>Admin paneliga xush kelibsiz!</b>\n"
        "Quyidagi menyudan kerakli bo'limni tanlang:",
        reply_markup=get_main_admin_keyboard(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "open_admin_panel")
async def callback_admin_panel(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    await callback.message.edit_text(
        "👋 <b>Admin paneliga xush kelibsiz!</b>\n"
        "Quyidagi menyudan kerakli bo'limni tanlang:",
        reply_markup=get_main_admin_keyboard(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "admin_purge_data")
async def purge_data_confirm(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⚠️ Ha, hammasini o'chirib tozalash", callback_data="admin_purge_data_yes"))
    builder.row(InlineKeyboardButton(text="🔙 Bekor qilish", callback_data="admin_back_main"))
    await callback.message.edit_text(
        "⚠️ <b>DIQQAT!</b>\n\nBarcha mavjud mahsulotlar va kategoriyalarni bazadan to'liq o'chirib tashlamoqchimisiz?\nBu amalni qaytarib bo'lmaydi!",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "admin_purge_data_yes")
async def purge_data_execute(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    from sqlalchemy import delete
    from app.models.models import ProductImage, Product, Category
    async with AsyncSessionLocal() as session:
        await session.execute(delete(ProductImage))
        await session.execute(delete(Product))
        await session.execute(delete(Category))
        await session.commit()
    await callback.answer("✅ Barcha ma'lumotlar butunlay tozalandi!", show_alert=True)
    await callback.message.edit_text(
        "✅ <b>Baza butunlay tozalandi!</b>\n\nEndi '🗂 Kategoriyalar' va '🛋 Mahsulotlar' bo'limlari orqali o'zingizning haqiqiy mahsulotlaringizni bittalab qo'shib chiqishingiz mumkin.",
        reply_markup=get_main_admin_keyboard(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "admin_cancel")
async def cancel_admin_action(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "Amal bekor qilindi.\nQuyidagi menyudan kerakli bo'limni tanlang:",
        reply_markup=get_main_admin_keyboard()
    )

@router.callback_query(F.data == "admin_stats")
async def show_stats(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
        
    import datetime
    
    now = datetime.datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    async with AsyncSessionLocal() as session:
        # All time
        total_orders = (await session.execute(select(func.count()).select_from(Order))).scalar() or 0
        total_sum = (await session.execute(select(func.sum(Order.total_amount)))).scalar() or 0
        
        # Monthly
        month_orders = (await session.execute(
            select(func.count()).select_from(Order).filter(Order.created_at >= month_start)
        )).scalar() or 0
        month_sum = (await session.execute(
            select(func.sum(Order.total_amount)).filter(Order.created_at >= month_start)
        )).scalar() or 0
        
        # Today
        today_orders = (await session.execute(
            select(func.count()).select_from(Order).filter(Order.created_at >= today_start)
        )).scalar() or 0
        today_sum = (await session.execute(
            select(func.sum(Order.total_amount)).filter(Order.created_at >= today_start)
        )).scalar() or 0
        
    text = (
        "📊 <b>Barcha Statistikalar</b>\n\n"
        "📅 <b>Bugun:</b>\n"
        f"📦 Buyurtmalar: <b>{today_orders} ta</b>\n"
        f"💰 Tushum: <b>{today_sum:,.0f} so'm</b>\n\n"
        "📆 <b>Shu oyda:</b>\n"
        f"📦 Buyurtmalar: <b>{month_orders} ta</b>\n"
        f"💰 Tushum: <b>{month_sum:,.0f} so'm</b>\n\n"
        "📈 <b>Umumiy (Barcha vaqt):</b>\n"
        f"📦 Buyurtmalar: <b>{total_orders} ta</b>\n"
        f"💰 Tushum: <b>{total_sum:,.0f} so'm</b>\n"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back_main"))
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")

@router.callback_query(F.data == "admin_back_main")
async def back_to_main_admin(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "👋 <b>Admin paneliga xush kelibsiz!</b>\n"
        "Quyidagi menyudan kerakli bo'limni tanlang:",
        reply_markup=get_main_admin_keyboard(),
        parse_mode="HTML"
    )

# --- Categories Management ---
@router.callback_query(F.data == "admin_cats")
async def manage_categories(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Category).filter(Category.is_active == True, Category.is_deleted == False))
        categories = result.scalars().all()
    builder = InlineKeyboardBuilder()
    for cat in categories:
        builder.row(InlineKeyboardButton(text=cat.name, callback_data=f"acat_{cat.id}"))
    builder.row(InlineKeyboardButton(text="➕ Yangi kategoriya qo'shish", callback_data="admin_add_category"))
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back_main"))
    await callback.message.edit_text("🗂 <b>Kategoriyalarni boshqarish:</b>", reply_markup=builder.as_markup(), parse_mode="HTML")

@router.callback_query(F.data.startswith("acat_"))
async def category_details(callback: types.CallbackQuery):
    cat_id = int(callback.data.split("_")[1])
    async with AsyncSessionLocal() as session:
        cat = await session.get(Category, cat_id)
    if not cat: return
    status_text = "🟢 Faol" if cat.is_active else "🔴 Nofaol"
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📝 Nomini o'zgartirish", callback_data=f"ecat_{cat_id}"),
        InlineKeyboardButton(text="🎨 Ikonkani o'zgartirish", callback_data=f"ecaticon_{cat_id}")
    )
    builder.row(
        InlineKeyboardButton(text=f"🔄 Holat: {status_text}", callback_data=f"ecattoggle_{cat_id}"),
        InlineKeyboardButton(text="❌ O'chirish", callback_data=f"dcat_{cat_id}")
    )
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_cats"))
    await callback.message.edit_text(
        f"🗂 <b>Kategoriya:</b> {cat.icon or ''} {cat.name}\n"
        f"<b>Holati:</b> {status_text}\n\n"
        "Nimani o'zgartirmoqchisiz?",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("ecat_"))
async def edit_category(callback: types.CallbackQuery, state: FSMContext):
    cat_id = int(callback.data.split("_")[1])
    await state.update_data(cat_id=cat_id)
    await state.set_state(EditCategory.waiting_for_new_name)
    await callback.message.edit_text("Kategoriya uchun yangi nomni kiriting:", reply_markup=get_cancel_admin_keyboard())

@router.message(EditCategory.waiting_for_new_name)
async def process_edit_category(message: types.Message, state: FSMContext):
    data = await state.get_data()
    async with AsyncSessionLocal() as session:
        cat = await session.get(Category, data["cat_id"])
        cat.name = message.text.strip()
        await session.commit()
    await state.clear()
    await message.answer("✅ Kategoriya nomi o'zgartirildi!", reply_markup=get_main_admin_keyboard())

@router.callback_query(F.data.startswith("ecaticon_"))
async def edit_category_icon(callback: types.CallbackQuery, state: FSMContext):
    cat_id = int(callback.data.split("_")[1])
    await state.update_data(cat_id=cat_id)
    await state.set_state(EditCategory.waiting_for_new_icon)
    await callback.message.edit_text("Kategoriya uchun yangi belgi / emoji kiriting (masalan: 🛋️, 🛏️, 🪑, 🚪):", reply_markup=get_cancel_admin_keyboard())

@router.message(EditCategory.waiting_for_new_icon)
async def process_edit_category_icon(message: types.Message, state: FSMContext):
    data = await state.get_data()
    async with AsyncSessionLocal() as session:
        cat = await session.get(Category, data["cat_id"])
        cat.icon = message.text.strip()
        await session.commit()
    await state.clear()
    await message.answer("✅ Kategoriya belgisi o'zgartirildi!", reply_markup=get_main_admin_keyboard())

@router.callback_query(F.data.startswith("ecattoggle_"))
async def toggle_category_status(callback: types.CallbackQuery):
    cat_id = int(callback.data.split("_")[1])
    async with AsyncSessionLocal() as session:
        cat = await session.get(Category, cat_id)
        if cat:
            cat.is_active = not cat.is_active
            await session.commit()
    await category_details(callback)

@router.callback_query(F.data.startswith("dcat_"))
async def delete_category(callback: types.CallbackQuery):
    cat_id = int(callback.data.split("_")[1])
    async with AsyncSessionLocal() as session:
        cat = await session.get(Category, cat_id)
        if cat:
            cat.is_deleted = True
            cat.is_active = False
            await session.commit()
    await callback.answer("❌ Kategoriya o'chirildi!", show_alert=True)
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Category).filter(Category.is_active == True, Category.is_deleted == False))
        categories = result.scalars().all()
    builder = InlineKeyboardBuilder()
    for cat in categories:
        builder.row(InlineKeyboardButton(text=cat.name, callback_data=f"acat_{cat.id}"))
    builder.row(InlineKeyboardButton(text="➕ Yangi kategoriya qo'shish", callback_data="admin_add_category"))
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back_main"))
    await callback.message.edit_text("🗂 <b>Kategoriyalarni boshqarish:</b>", reply_markup=builder.as_markup(), parse_mode="HTML")

@router.callback_query(F.data == "admin_add_category")
async def add_category_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    await state.set_state(AddCategory.waiting_for_name)
    await callback.message.edit_text("Yangi kategoriya nomini kiriting:", reply_markup=get_cancel_admin_keyboard())

@router.message(AddCategory.waiting_for_name)
async def process_category_name(message: types.Message, state: FSMContext):
    name = message.text.strip()
    async with AsyncSessionLocal() as session:
        new_cat = Category(name=name, icon="🛋️")
        session.add(new_cat)
        await session.commit()
    await state.clear()
    await message.answer(f"✅ <b>{name}</b> kategoriyasi qo'shildi!", reply_markup=get_main_admin_keyboard(), parse_mode="HTML")

# --- Add Product ---
@router.callback_query(F.data == "admin_add_product")
async def add_product_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
        
    # Get categories to show as keyboard
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Category).filter(Category.is_active == True))
        categories = result.scalars().all()
        
    if not categories:
        await callback.answer("Avval kategoriya qo'shing!", show_alert=True)
        return
        
    builder = InlineKeyboardBuilder()
    for cat in categories:
        builder.row(InlineKeyboardButton(text=cat.name, callback_data=f"selcat_{cat.id}"))
    builder.row(InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin_cancel"))
    
    await state.set_state(AddProduct.waiting_for_category)
    await callback.message.edit_text(
        "Mahsulot qaysi kategoriyaga tegishli ekanligini tanlang:",
        reply_markup=builder.as_markup()
    )

@router.callback_query(AddProduct.waiting_for_category, F.data.startswith("selcat_"))
async def process_product_category(callback: types.CallbackQuery, state: FSMContext):
    cat_id = int(callback.data.split("_")[1])
    await state.update_data(category_id=cat_id)
    
    await state.set_state(AddProduct.waiting_for_name)
    await callback.message.edit_text(
        "Mahsulot nomini kiriting:",
        reply_markup=get_cancel_admin_keyboard()
    )

@router.message(AddProduct.waiting_for_name)
async def process_product_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(AddProduct.waiting_for_desc)
    await message.answer("Mahsulot haqida ma'lumot (ta'rifi) ni kiriting:", reply_markup=get_cancel_admin_keyboard())

@router.message(AddProduct.waiting_for_desc)
async def process_product_desc(message: types.Message, state: FSMContext):
    await state.update_data(desc=message.text.strip())
    await state.set_state(AddProduct.waiting_for_price)
    await message.answer("Mahsulot narxini raqamlarda kiriting (so'mda):", reply_markup=get_cancel_admin_keyboard())

@router.message(AddProduct.waiting_for_price)
async def process_product_price(message: types.Message, state: FSMContext):
    if not message.text:
        await message.answer("Iltimos, narxni matn yoki raqam ko'rinishida yuboring!")
        return
    clean_text = message.text.replace(" ", "").replace("'", "").replace(",", "").replace(".", "").strip()
    if not clean_text.isdigit():
        await message.answer("⚠️ Iltimos, narxni faqat raqamlarda kiriting! (masalan: 500000 yoki 1000000)")
        return
    await state.update_data(price=int(clean_text))
    await state.set_state(AddProduct.waiting_for_photo)
    await message.answer("📸 Endi mahsulot rasmini yuboring (galereyangizdan photo qilib):", reply_markup=get_cancel_admin_keyboard())

@router.message(AddProduct.waiting_for_photo, F.photo)
async def process_product_photo(message: types.Message, state: FSMContext):
    photo_file_id = message.photo[-1].file_id
    
    import os
    import uuid
    os.makedirs("uploads/products", exist_ok=True)
    filename = f"{uuid.uuid4().hex}.jpg"
    local_file_path = os.path.join("uploads/products", filename)
    
    try:
        file_obj = await message.bot.get_file(photo_file_id)
        await asyncio.wait_for(message.bot.download_file(file_obj.file_path, local_file_path), timeout=20.0)
        img_url = f"{settings.PUBLIC_URL}/uploads/products/{filename}"
    except Exception as e:
        file_obj = await message.bot.get_file(photo_file_id)
        img_url = f"https://api.telegram.org/file/bot{settings.BOT_TOKEN}/{file_obj.file_path}"
    
    data = await state.get_data()
    
    async with AsyncSessionLocal() as session:
        new_prod = Product(
            category_id=data["category_id"],
            name=data["name"],
            description=data["desc"],
            price=data["price"],
            stock_quantity=10,
            is_active=True
        )
        session.add(new_prod)
        await session.flush()
        
        new_img = ProductImage(
            product_id=new_prod.id,
            image_url=img_url,
            is_main=True
        )
        session.add(new_img)
        await session.commit()
        
    await state.clear()
    await message.answer(
        f"✅ <b>{data['name']}</b> mahsuloti muvaffaqiyatli qo'shildi!",
        reply_markup=get_main_admin_keyboard(),
        parse_mode="HTML"
    )

# --- Product Management ---
@router.callback_query(F.data == "admin_prods")
async def manage_products_cats(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Category).filter(Category.is_active == True, Category.is_deleted == False))
        categories = result.scalars().all()
    builder = InlineKeyboardBuilder()
    for cat in categories:
        builder.row(InlineKeyboardButton(text=cat.name, callback_data=f"apcat_{cat.id}"))
    builder.row(InlineKeyboardButton(text="➕ Yangi mahsulot qo'shish", callback_data="admin_add_product"))
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back_main"))
    await callback.message.edit_text("🛋 <b>Qaysi kategoriyadagi mahsulotlarni ko'rmoqchisiz?</b>", reply_markup=builder.as_markup(), parse_mode="HTML")

@router.callback_query(F.data.startswith("apcat_"))
async def manage_products_list(callback: types.CallbackQuery):
    cat_id = int(callback.data.split("_")[1])
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Product).filter(Product.category_id == cat_id, Product.is_active == True, Product.is_deleted == False))
        products = result.scalars().all()
    builder = InlineKeyboardBuilder()
    for prod in products:
        builder.row(InlineKeyboardButton(text=prod.name, callback_data=f"aprod_{prod.id}"))
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_prods"))
    await callback.message.edit_text("🛋 <b>Mahsulotlar:</b>", reply_markup=builder.as_markup(), parse_mode="HTML")

@router.callback_query(F.data.startswith("aprod_"))
async def product_details(callback: types.CallbackQuery):
    prod_id = int(callback.data.split("_")[1])
    async with AsyncSessionLocal() as session:
        prod = await session.get(Product, prod_id)
    if not prod: return
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📝 Nomi", callback_data=f"eprodn_{prod_id}"),
        InlineKeyboardButton(text="📝 Izohi", callback_data=f"eprodd_{prod_id}"),
        InlineKeyboardButton(text="📝 Narxi", callback_data=f"eprod_{prod_id}")
    )
    builder.row(
        InlineKeyboardButton(text="📦 Ombordagi soni", callback_data=f"eprods_{prod_id}"),
        InlineKeyboardButton(text="🖼 Rasmini yangilash", callback_data=f"eprodphoto_{prod_id}")
    )
    builder.row(
        InlineKeyboardButton(text="📹 Videoni yangilash", callback_data=f"eprodvideo_{prod_id}"),
        InlineKeyboardButton(text="❌ O'chirish", callback_data=f"dprod_{prod_id}")
    )
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"apcat_{prod.category_id}"))
    
    video_status = "Mavjud 🎬" if prod.video_url else "Mavjud emas"
    await callback.message.edit_text(
        f"🛋 <b>Mahsulot:</b> {prod.name}\n"
        f"💰 <b>Narxi:</b> {prod.price:,.0f} so'm\n"
        f"📦 <b>Omborda qolgani:</b> {prod.stock_quantity or 0} dona\n"
        f"📹 <b>Video:</b> {video_status}\n\n"
        f"Nimani o'zgartirmoqchisiz?",
        reply_markup=builder.as_markup(), parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("eprodvideo_"))
async def edit_product_video(callback: types.CallbackQuery, state: FSMContext):
    prod_id = int(callback.data.split("_")[1])
    await state.update_data(prod_id=prod_id)
    await state.set_state(EditProduct.waiting_for_new_video)
    await callback.message.edit_text(
        "📹 <b>Mahsulot videosini yuboring:</b>\n\n"
        "Telegram orqali video fayl yuborishingiz yoki video havolasini (YouTube/MP4 link) matn ko'rinishida yozib yuborishingiz mumkin:",
        reply_markup=get_cancel_admin_keyboard(),
        parse_mode="HTML"
    )

@router.message(EditProduct.waiting_for_new_video, F.video)
async def process_edit_product_video_file(message: types.Message, state: FSMContext):
    video_file_id = message.video.file_id
    import uuid
    os.makedirs("uploads/videos", exist_ok=True)
    filename = f"{uuid.uuid4().hex}.mp4"
    local_file_path = os.path.join("uploads/videos", filename)
    
    try:
        file_obj = await message.bot.get_file(video_file_id)
        await asyncio.wait_for(message.bot.download_file(file_obj.file_path, local_file_path), timeout=20.0)
        video_url = f"{settings.PUBLIC_URL}/uploads/videos/{filename}"
    except Exception as e:
        file_obj = await message.bot.get_file(video_file_id)
        video_url = f"https://api.telegram.org/file/bot{settings.BOT_TOKEN}/{file_obj.file_path}"
        
    data = await state.get_data()
    async with AsyncSessionLocal() as session:
        prod = await session.get(Product, data["prod_id"])
        if prod:
            prod.video_url = video_url
            await session.commit()
            
    await state.clear()
    await message.answer("✅ Mahsulotning qisqa videosi muvaffaqiyatli saqlandi va biriktirildi!", reply_markup=get_main_admin_keyboard())

@router.message(EditProduct.waiting_for_new_video, F.text)
async def process_edit_product_video_text(message: types.Message, state: FSMContext):
    video_url = message.text.strip()
    data = await state.get_data()
    async with AsyncSessionLocal() as session:
        prod = await session.get(Product, data["prod_id"])
        if prod:
            prod.video_url = video_url
            await session.commit()
            
    await state.clear()
    await message.answer("✅ Mahsulot video havolasi saqlandi!", reply_markup=get_main_admin_keyboard())

@router.callback_query(F.data.startswith("eprods_"))
async def edit_product_stock(callback: types.CallbackQuery, state: FSMContext):
    prod_id = int(callback.data.split("_")[1])
    await state.update_data(prod_id=prod_id)
    await state.set_state(EditProduct.waiting_for_new_stock)
    await callback.message.edit_text("Ombordagi yangi miqdorni (sonini) raqamda kiriting:", reply_markup=get_cancel_admin_keyboard())

@router.message(EditProduct.waiting_for_new_stock)
async def process_edit_product_stock(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Faqat musbat raqam kiriting!")
        return
    data = await state.get_data()
    new_stock = int(message.text)
    async with AsyncSessionLocal() as session:
        prod = await session.get(Product, data["prod_id"])
        if prod:
            prod.stock_quantity = new_stock
            await session.commit()
    await state.clear()
    await message.answer(f"✅ Mahsulotning ombordagi miqdori <b>{new_stock} dona</b> qilib yangilandi!", reply_markup=get_main_admin_keyboard(), parse_mode="HTML")

@router.callback_query(F.data.startswith("eprod_"))
async def edit_product_price(callback: types.CallbackQuery, state: FSMContext):
    prod_id = int(callback.data.split("_")[1])
    await state.update_data(prod_id=prod_id)
    await state.set_state(EditProduct.waiting_for_new_price)
    await callback.message.edit_text("Yangi narxni raqamlarda kiriting:", reply_markup=get_cancel_admin_keyboard())

@router.message(EditProduct.waiting_for_new_price)
async def process_edit_product(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Faqat raqam kiriting!")
        return
    data = await state.get_data()
    async with AsyncSessionLocal() as session:
        prod = await session.get(Product, data["prod_id"])
        prod.price = int(message.text)
        await session.commit()
    await state.clear()
    await message.answer("✅ Mahsulot narxi o'zgartirildi!", reply_markup=get_main_admin_keyboard())

@router.callback_query(F.data.startswith("eprodn_"))
async def edit_product_name(callback: types.CallbackQuery, state: FSMContext):
    prod_id = int(callback.data.split("_")[1])
    await state.update_data(prod_id=prod_id)
    await state.set_state(EditProduct.waiting_for_new_name)
    await callback.message.edit_text("Yangi nomni kiriting:", reply_markup=get_cancel_admin_keyboard())

@router.message(EditProduct.waiting_for_new_name)
async def process_edit_product_name(message: types.Message, state: FSMContext):
    data = await state.get_data()
    async with AsyncSessionLocal() as session:
        prod = await session.get(Product, data["prod_id"])
        prod.name = message.text.strip()
        await session.commit()
    await state.clear()
    await message.answer("✅ Mahsulot nomi o'zgartirildi!", reply_markup=get_main_admin_keyboard())

@router.callback_query(F.data.startswith("eprodd_"))
async def edit_product_desc(callback: types.CallbackQuery, state: FSMContext):
    prod_id = int(callback.data.split("_")[1])
    await state.update_data(prod_id=prod_id)
    await state.set_state(EditProduct.waiting_for_new_desc)
    await callback.message.edit_text("Yangi izohni kiriting:", reply_markup=get_cancel_admin_keyboard())

@router.message(EditProduct.waiting_for_new_desc)
async def process_edit_product_desc(message: types.Message, state: FSMContext):
    data = await state.get_data()
    async with AsyncSessionLocal() as session:
        prod = await session.get(Product, data["prod_id"])
        prod.description = message.text.strip()
        await session.commit()
    await state.clear()
    await message.answer("✅ Mahsulot izohi o'zgartirildi!", reply_markup=get_main_admin_keyboard())

@router.callback_query(F.data.startswith("eprodphoto_"))
async def edit_product_photo_start(callback: types.CallbackQuery, state: FSMContext):
    prod_id = int(callback.data.split("_")[1])
    await state.update_data(prod_id=prod_id)
    await state.set_state(EditProduct.waiting_for_new_photo)
    await callback.message.edit_text("Mahsulot uchun yangi rasmni yuboring (galereyangizdan):", reply_markup=get_cancel_admin_keyboard())

@router.message(EditProduct.waiting_for_new_photo, F.photo)
async def process_edit_product_photo(message: types.Message, state: FSMContext):
    photo_file_id = message.photo[-1].file_id
    import os
    import uuid
    os.makedirs("uploads/products", exist_ok=True)
    filename = f"{uuid.uuid4().hex}.jpg"
    local_file_path = os.path.join("uploads/products", filename)
    try:
        file_obj = await message.bot.get_file(photo_file_id)
        await asyncio.wait_for(message.bot.download_file(file_obj.file_path, local_file_path), timeout=20.0)
        img_url = f"{settings.PUBLIC_URL}/uploads/products/{filename}"
    except Exception as e:
        file_obj = await message.bot.get_file(photo_file_id)
        img_url = f"https://api.telegram.org/file/bot{settings.BOT_TOKEN}/{file_obj.file_path}"
    
    data = await state.get_data()
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(ProductImage).filter(ProductImage.product_id == data["prod_id"]))
        img = result.scalars().first()
        if img:
            img.image_url = img_url
        else:
            new_img = ProductImage(product_id=data["prod_id"], image_url=img_url, is_main=True)
            session.add(new_img)
        await session.commit()
    await state.clear()
    await message.answer("✅ Mahsulot rasmi galereyangizdagi yangi rasmga o'zgartirildi!", reply_markup=get_main_admin_keyboard())

@router.callback_query(F.data.startswith("dprod_"))
async def delete_product(callback: types.CallbackQuery):
    prod_id = int(callback.data.split("_")[1])
    async with AsyncSessionLocal() as session:
        prod = await session.get(Product, prod_id)
        if prod:
            prod.is_deleted = True
            prod.is_active = False
            cat_id = prod.category_id
            await session.commit()
            
            result = await session.execute(
                select(Product).filter(
                    Product.category_id == cat_id,
                    Product.is_active == True,
                    Product.is_deleted == False
                )
            )
            products = result.scalars().all()
        else:
            cat_id = None
            products = []
            
    await callback.answer("❌ Mahsulot o'chirildi!", show_alert=True)
    builder = InlineKeyboardBuilder()
    for p in products:
        builder.row(InlineKeyboardButton(text=p.name, callback_data=f"aprod_{p.id}"))
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_prods"))
    await callback.message.edit_text("🛋 <b>Mahsulotlar:</b>", reply_markup=builder.as_markup(), parse_mode="HTML")
