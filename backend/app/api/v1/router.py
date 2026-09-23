from fastapi import APIRouter

from app.api.v1.me import router as me_router
from app.api.v1.members import router as members_router


router = APIRouter()
router.include_router(me_router)
router.include_router(members_router)
