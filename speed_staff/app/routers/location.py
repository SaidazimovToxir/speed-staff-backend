from fastapi import APIRouter
from fastapi.responses import JSONResponse
from app.utils.locations import UZBEKISTAN_REGIONS

router = APIRouter(prefix="/api/locations", tags=["Locations"])

@router.get("/regions")
async def get_regions():
    """
    Returns a static list of all Uzbekistan regions and their respective districts
    with localizations (uz, ru, en). Fast response with zero database overhead.
    """
    return JSONResponse(content={"success": True, "data": UZBEKISTAN_REGIONS})
