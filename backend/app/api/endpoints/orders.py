from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import uuid
from app.db.database import get_db
from app.models.models import Order, OrderItem, IndividualOrder, UserRole
from app.schemas.schemas import OrderResponse, OrderCreate, IndividualOrderCreate, IndividualOrderResponse
from app.api.deps import get_current_admin, get_optional_user
from app.notifications.telegram import notify_admin_new_order, notify_customer_status_change, notify_admin_individual_order
from app.models.models import OrderStatusHistory, User
from app.schemas.order_update import OrderStatusUpdate
from sqlalchemy.orm import selectinload

router = APIRouter()

@router.post("/upload-photo")
async def upload_order_photo(file: UploadFile = File(...)):
    import os
    import uuid
    os.makedirs("uploads/orders", exist_ok=True)
    ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    filename = f"{uuid.uuid4().hex}.{ext}"
    file_path = os.path.join("uploads/orders", filename)
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    from app.core.config import settings
    base_url = settings.PUBLIC_URL
    return {"image_url": f"{base_url}/uploads/orders/{filename}"}

@router.post("/custom")
async def create_custom_order(
    order_in: IndividualOrderCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user)
):
    new_ind_order = IndividualOrder(
        customer_id=current_user.id if current_user else None,
        customer_name=order_in.customer_name,
        customer_phone=order_in.customer_phone,
        furniture_type=order_in.furniture_type,
        dimensions=order_in.dimensions,
        material=order_in.material,
        colors=order_in.colors,
        design=order_in.design,
        quantity=order_in.quantity,
        reference_image_url=order_in.reference_image_url,
        customer_note=order_in.customer_note
    )
    db.add(new_ind_order)
    await db.commit()
    await db.refresh(new_ind_order)
    
    tg_id = current_user.telegram_id if current_user else None
    background_tasks.add_task(
        notify_admin_individual_order,
        order_in.customer_name,
        order_in.customer_phone,
        order_in.furniture_type,
        order_in.dimensions,
        order_in.material,
        order_in.colors,
        order_in.customer_note,
        tg_id,
        order_in.reference_image_url
    )
    
    return {
        "status": "success",
        "message": "Individual buyurtmangiz qabul qilindi!",
        "order_id": new_ind_order.id
    }

@router.post("/", response_model=OrderResponse)
async def create_order(
    order_in: OrderCreate, 
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user)
):
    from app.models.models import Product
    order_number = f"ORD-{str(uuid.uuid4().int)[:6]}"
    
    total_amount = 0
    items = []
    
    first_image_url = None
    for item_in in order_in.items:
        product = await db.get(Product, item_in.product_id)
        if product:
            if not first_image_url:
                from app.models.models import ProductImage
                img_res = await db.execute(select(ProductImage).filter(ProductImage.product_id == product.id))
                p_img = img_res.scalars().first()
                if p_img:
                    first_image_url = p_img.image_url
            subtotal = product.price * item_in.quantity
            total_amount += subtotal
            items.append(
                OrderItem(
                    product_id=product.id,
                    product_name=product.name,
                    unit_price=product.price,
                    quantity=item_in.quantity,
                    subtotal=subtotal
                )
            )
            
    customer_id = current_user.id if current_user else None
    if not customer_id and order_in.customer_phone:
        clean_phone = order_in.customer_phone.replace("+", "").replace(" ", "").strip()
        if len(clean_phone) >= 7:
            u_res = await db.execute(
                select(User).filter(
                    (User.phone == order_in.customer_phone) |
                    (User.phone.endswith(clean_phone[-7:]))
                )
            )
            found_u = u_res.scalars().first()
            if found_u:
                customer_id = found_u.id

    new_order = Order(
        order_number=order_number,
        customer_id=customer_id,
        customer_name=order_in.customer_name,
        customer_phone=order_in.customer_phone,
        customer_address=order_in.customer_address,
        location_lat=order_in.location_lat,
        location_lon=order_in.location_lon,
        requires_delivery=order_in.requires_delivery,
        requires_assembly=order_in.requires_assembly,
        customer_note=order_in.customer_note,
        total_amount=total_amount,
    )
    db.add(new_order)
    await db.flush()
    
    items_text = ""
    for item in items:
        item.order_id = new_order.id
        db.add(item)
        items_text += f"- {item.product_name} ({item.quantity} ta) - {item.subtotal:,.0f} so'm\n"
        
    await db.commit()
    
    res = await db.execute(
        select(Order).options(selectinload(Order.items)).filter(Order.id == new_order.id)
    )
    order_with_items = res.scalar_one()
    
    tg_id = current_user.telegram_id if current_user else None
    if not tg_id and customer_id:
        u_cust = await db.get(User, customer_id)
        if u_cust:
            tg_id = u_cust.telegram_id

    background_tasks.add_task(
        notify_admin_new_order, 
        order_with_items, 
        items_text,
        tg_id,
        first_image_url
    )
    
    return order_with_items

@router.put("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: int,
    status_update: OrderStatusUpdate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    order = await db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    order.status = status_update.status
    
    # History
    history = OrderStatusHistory(
        order_id=order.id,
        status=status_update.status,
        note=status_update.note,
        created_by_id=current_admin.id
    )
    db.add(history)
    await db.commit()
    
    res = await db.execute(
        select(Order).options(selectinload(Order.items)).filter(Order.id == order.id)
    )
    order_with_items = res.scalar_one()
    
    # Notify Customer
    customer = None
    if order_with_items.customer_id:
        customer = await db.get(User, order_with_items.customer_id)
    if not customer and order_with_items.customer_phone:
        clean_phone = order_with_items.customer_phone.replace("+", "").replace(" ", "").strip()
        if len(clean_phone) >= 7:
            u_res = await db.execute(
                select(User).filter(
                    (User.phone == order_with_items.customer_phone) |
                    (User.phone.endswith(clean_phone[-7:]))
                )
            )
            customer = u_res.scalars().first()

    if customer and customer.telegram_id:
        background_tasks.add_task(
            notify_customer_status_change, 
            customer.telegram_id, 
            order_with_items.order_number, 
            status_update.status.value, 
            status_update.note
        )
            
    return order_with_items

@router.delete("/{order_id}")
async def delete_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user)
):
    order = await db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Buyurtma topilmadi")
        
    is_owner = False
    if current_user:
        if current_user.role == UserRole.ADMIN or order.customer_id == current_user.id:
            is_owner = True
        elif current_user.phone and order.customer_phone and current_user.phone in order.customer_phone:
            is_owner = True

    if not is_owner and current_user is None:
        is_owner = True
        
    if not is_owner:
        raise HTTPException(status_code=403, detail="Ruxsat berilmagan")
        
    await db.delete(order)
    await db.commit()
    return {"status": "success", "message": "Buyurtma o'chirildi"}

@router.delete("/custom/{order_id}")
async def delete_custom_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user)
):
    order = await db.get(IndividualOrder, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Individual buyurtma topilmadi")
        
    is_owner = False
    if current_user:
        if current_user.role == UserRole.ADMIN or order.customer_id == current_user.id:
            is_owner = True
        elif current_user.phone and order.customer_phone and current_user.phone in order.customer_phone:
            is_owner = True

    if not is_owner and current_user is None:
        is_owner = True

    if not is_owner:
        raise HTTPException(status_code=403, detail="Ruxsat berilmagan")

    await db.delete(order)
    await db.commit()
    return {"status": "success", "message": "Individual buyurtma o'chirildi"}

@router.get("/", response_model=List[OrderResponse])
async def get_orders(
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user)
):
    if not current_user:
        return []
        
    query = select(Order).options(selectinload(Order.items)).order_by(Order.created_at.desc())
    
    if current_user.role != UserRole.ADMIN:
        query = query.filter(
            (Order.customer_id == current_user.id) | 
            (Order.customer_phone == current_user.phone)
        )
        
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/custom", response_model=List[IndividualOrderResponse])
async def get_my_custom_orders(
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user)
):
    if not current_user:
        return []
    
    query = select(IndividualOrder).order_by(IndividualOrder.created_at.desc())
    if current_user.role != UserRole.ADMIN:
        query = query.filter(
            (IndividualOrder.customer_id == current_user.id) |
            (IndividualOrder.customer_phone == current_user.phone)
        )
    result = await db.execute(query)
    return result.scalars().all()
