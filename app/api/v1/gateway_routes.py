from fastapi import APIRouter
from app.services import user_service, product_service, order_service
router = APIRouter(prefix="/gateway")

router.include_router(user_service.router, tags=["gateway -> user-service"])
router.include_router(product_service.router, tags=["gateway -> product-service"])
router.include_router(order_service.router, tags=["gateway -> order-service"])