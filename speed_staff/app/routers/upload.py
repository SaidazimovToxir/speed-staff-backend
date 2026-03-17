import os
import aiofiles
import uuid
from typing import Literal
from fastapi import APIRouter, File, UploadFile, Depends, Form
from PIL import Image
from io import BytesIO

from app.schemas.common import ErrorDetail
from app.dependencies import get_current_user
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.seeker import SeekerDocument
from app.models.user import User

from sqlalchemy import select
from app.models.seeker import SeekerProfile, SeekerDocument
from app.models.employer import EmployerProfile

router = APIRouter(tags=["Uploads"])

UPLOAD_DIR = "./uploads"

os.makedirs(f"{UPLOAD_DIR}/avatars", exist_ok=True)
os.makedirs(f"{UPLOAD_DIR}/resumes", exist_ok=True)
os.makedirs(f"{UPLOAD_DIR}/documents", exist_ok=True)
os.makedirs(f"{UPLOAD_DIR}/logos", exist_ok=True)

async def _resize_and_save_image(file_data: bytes, path: str, max_size: tuple[int, int]):
    try:
        image = Image.open(BytesIO(file_data))
        image.thumbnail(max_size)
        image.save(path)
    except Exception as e:
        raise ValueError(f"Failed to process image: {e}")

@router.post("/avatar")
async def upload_avatar(file: UploadFile = File(...), current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    ext = file.filename.split(".")[-1].lower() if "." in file.filename else ""
    if ext not in ["jpg", "jpeg", "png", "webp"]:
        return ErrorDetail(error_code="INVALID_FILE_TYPE", message="Allowed types: jpg, jpeg, png, webp").model_dump(), 400

    file_data = await file.read()
    if len(file_data) > 5 * 1024 * 1024:
        return ErrorDetail(error_code="FILE_TOO_LARGE", message="Max size: 5MB").model_dump(), 400

    file_id = str(uuid.uuid4())
    file_path = f"{UPLOAD_DIR}/avatars/{file_id}.{ext}"
    url = f"/uploads/avatars/{file_id}.{ext}"

    await _resize_and_save_image(file_data, file_path, (800, 800))
    
    if current_user.role == "seeker":
        result = await db.execute(select(SeekerProfile).where(SeekerProfile.user_id == current_user.id))
        profile = result.scalars().first()
        if profile:
            profile.avatar_url = url
            await db.commit()

    return {"url": f"https://api.speed-staff.uz{url}"}

@router.post("/resume")
async def upload_resume(file: UploadFile = File(...), current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if current_user.role != "seeker":
         return ErrorDetail(error_code="NOT_AUTHORIZED", message="Seeker role required").model_dump(), 403

    ext = file.filename.split(".")[-1].lower() if "." in file.filename else ""
    if ext != "pdf":
        return ErrorDetail(error_code="INVALID_FILE_TYPE", message="Allowed types: pdf").model_dump(), 400

    file_data = await file.read()
    if len(file_data) > 10 * 1024 * 1024:
        return ErrorDetail(error_code="FILE_TOO_LARGE", message="Max size: 10MB").model_dump(), 400

    file_id = str(uuid.uuid4())
    file_path = f"{UPLOAD_DIR}/resumes/{file_id}.pdf"
    url = f"/uploads/resumes/{file_id}.pdf"

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(file_data)
        
    result = await db.execute(select(SeekerProfile).where(SeekerProfile.user_id == current_user.id))
    profile = result.scalars().first()
    if profile:
        profile.resume_url = url
        await db.commit()

    return {"url": f"https://api.speed-staff.uz{url}"}

@router.post("/logo")
async def upload_logo(file: UploadFile = File(...), current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if current_user.role != "employer":
         return ErrorDetail(error_code="NOT_AUTHORIZED", message="Employer role required").model_dump(), 403

    ext = file.filename.split(".")[-1].lower() if "." in file.filename else ""
    if ext not in ["jpg", "jpeg", "png", "webp"]:
        return ErrorDetail(error_code="INVALID_FILE_TYPE", message="Allowed types: jpg, jpeg, png, webp").model_dump(), 400

    file_data = await file.read()
    if len(file_data) > 5 * 1024 * 1024:
        return ErrorDetail(error_code="FILE_TOO_LARGE", message="Max size: 5MB").model_dump(), 400

    file_id = str(uuid.uuid4())
    file_path = f"{UPLOAD_DIR}/logos/{file_id}.{ext}"
    url = f"/uploads/logos/{file_id}.{ext}"

    await _resize_and_save_image(file_data, file_path, (400, 400))
    
    result = await db.execute(select(EmployerProfile).where(EmployerProfile.user_id == current_user.id))
    profile = result.scalars().first()
    if profile:
        profile.logo_url = url
        await db.commit()

    return {"url": f"https://api.speed-staff.uz{url}"}

@router.post("/document")
async def upload_document(
    doc_type: str = Form(...),
    title: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role != "seeker":
         return ErrorDetail(error_code="NOT_AUTHORIZED", message="Seeker role required").model_dump(), 403
         
    result = await db.execute(select(SeekerProfile).where(SeekerProfile.user_id == current_user.id))
    profile = result.scalars().first()
    if not profile:
        return ErrorDetail(error_code="PROFILE_NOT_FOUND", message="Create profile first").model_dump(), 404

    ext = file.filename.split(".")[-1].lower() if "." in file.filename else ""
    if ext not in ["pdf", "jpg", "jpeg", "png"]:
        return ErrorDetail(error_code="INVALID_FILE_TYPE", message="Allowed types: pdf, jpg, png").model_dump(), 400

    file_data = await file.read()
    if len(file_data) > 10 * 1024 * 1024:
        return ErrorDetail(error_code="FILE_TOO_LARGE", message="Max size: 10MB").model_dump(), 400

    file_id = str(uuid.uuid4())
    file_path = f"{UPLOAD_DIR}/documents/{file_id}.{ext}"
    url = f"/uploads/documents/{file_id}.{ext}"

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(file_data)
        
    new_doc = SeekerDocument(
        seeker_id=profile.id,
        doc_type=doc_type,
        title=title,
        file_url=url,
        is_verified=False
    )
    db.add(new_doc)
    await db.commit()

    return {"url": f"https://api.speed-staff.uz{url}", "message": "Document uploaded successfully"}
