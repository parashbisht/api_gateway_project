from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import rate_limited_identity
from app.models.order import Order
from app.models.product import Product
from app.models.user import User
from app.schemas.order import OrderCreate, OrderOut

router = APIRouter()


@router.post("/orders", response_model=OrderOut, status_code=201)
def create_order(
    payload: OrderCreate,
    db: Session = Depends(get_db),
    current_identity: User = Depends(rate_limited_identity),
):
    product = db.query(Product).filter(Product.id == payload.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    order = Order(user_id=current_identity.id, product_id=payload.product_id)
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


@router.get("/orders", response_model=list[OrderOut])
def list_my_orders(
    db: Session = Depends(get_db),
    current_identity: User = Depends(rate_limited_identity),
):
    return db.query(Order).filter(Order.user_id == current_identity.id).all()