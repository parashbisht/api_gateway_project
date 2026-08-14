from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Literal

from app.db.session import get_db
from app.deps import rate_limited_identity
from app.models.product import Product
from app.models.user import User
from app.schemas.product import ProductCreate, ProductOut
from app.schemas.pagination import PaginationParams
router = APIRouter()


@router.post("/products", response_model=ProductOut, status_code=201)
def create_product(
    payload: ProductCreate,
    db: Session = Depends(get_db),
    current_identity: User = Depends(rate_limited_identity),
):
    product = Product(**payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product




@router.get("/products")
def list_products(
    pagination: PaginationParams = Depends(),
    sort_by: Literal["id", "name", "price", "created_at"] = "id",
    db: Session = Depends(get_db),
    current_identity: User = Depends(rate_limited_identity),
):
    total = db.query(Product).count()
    sort_column = getattr(Product, sort_by)
    products = (
        db.query(Product)
        .order_by(sort_column)
        .offset(pagination.offset)
        .limit(pagination.limit)
        .all()
    )
    return {
        "total": total,
        "limit": pagination.limit,
        "offset": pagination.offset,
        "items": [ProductOut.model_validate(p) for p in products],
    }

@router.get("/products/{product_id}", response_model=ProductOut)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_identity: User = Depends(rate_limited_identity),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product