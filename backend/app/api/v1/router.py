from fastapi import APIRouter

from app.api.v1.booking_catalog import router as booking_catalog_router
from app.api.v1.contracts import router as contracts_router
from app.api.v1.availability import router as availability_router
from app.api.v1.me import router as me_router
from app.api.v1.management_stores import router as management_stores_router
from app.api.v1.management_catalog import router as management_catalog_router
from app.api.v1.members import router as members_router
from app.api.v1.reservations import router as reservations_router


router = APIRouter()
router.include_router(me_router)
router.include_router(members_router)
router.include_router(booking_catalog_router)
router.include_router(availability_router)
router.include_router(reservations_router)
router.include_router(contracts_router)
router.include_router(management_stores_router)
router.include_router(management_catalog_router)
