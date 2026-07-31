from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import rate_limited_identity
from app.models.product import Product
from app.models.user import User
from app.schemas.product import ProductCreate, ProductOut

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


@router.get("/products", response_model=list[ProductOut])
def list_products(
    db: Session = Depends(get_db),
    current_identity: User = Depends(rate_limited_identity),
):
    return db.query(Product).all()


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