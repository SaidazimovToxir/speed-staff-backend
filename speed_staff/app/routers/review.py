import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.review import Review, SeekerReview, Report
from app.models.employer import EmployerProfile
from app.models.seeker import SeekerProfile
from app.models.application import Application
from app.models.user import User

from app.schemas.review import (
    ReviewCreate, ReviewResponse, SeekerReviewCreate, SeekerReviewResponse,
    ReportCreate, ReportResponse
)
from app.schemas.employer import EmployerProfileShortResponse
from app.schemas.common import ErrorDetail, SuccessResponse, PaginatedResponse, Meta
from app.dependencies import get_current_user

router = APIRouter()

def error_response(code: str, message: str, status_code: int, details=None):
    return JSONResponse(
        status_code=status_code,
        content=ErrorDetail(error_code=code, message=message, details=details).model_dump()
    )


async def recalculate_employer_rating(employer_id: uuid.UUID, db: AsyncSession):
    stmt = select(func.avg(Review.rating), func.count(Review.id)).where(
        Review.employer_id == employer_id,
        Review.is_visible == True
    )
    result = await db.execute(stmt)
    avg_rating, total_reviews = result.first()
    
    avg_rating = float(round(avg_rating, 1)) if avg_rating else 0.0
    total_reviews = total_reviews or 0

    emp_stmt = select(EmployerProfile).where(EmployerProfile.id == employer_id)
    employer = await db.scalar(emp_stmt)
    if employer:
        employer.rating = avg_rating
        employer.total_reviews = total_reviews
        await db.commit()


async def recalculate_seeker_rating(seeker_id: uuid.UUID, db: AsyncSession):
    stmt = select(func.avg(SeekerReview.rating), func.count(SeekerReview.id)).where(
        SeekerReview.seeker_id == seeker_id
    )
    result = await db.execute(stmt)
    avg_rating, total_reviews = result.first()
    
    avg_rating = float(round(avg_rating, 1)) if avg_rating else 0.0
    total_reviews = total_reviews or 0

    seek_stmt = select(SeekerProfile).where(SeekerProfile.id == seeker_id)
    seeker = await db.scalar(seek_stmt)
    if seeker:
        seeker.rating = avg_rating
        seeker.total_reviews = total_reviews
        await db.commit()


# --- Restaurant Reviews (Reviews) ---

@router.get("/employer/{employer_id}", response_model=PaginatedResponse[ReviewResponse])
async def get_employer_reviews(
    employer_id: uuid.UUID,
    page: int = 1,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Review).options(
        selectinload(Review.author)
    ).where(Review.employer_id == employer_id, Review.is_visible == True)

    count_stmt = select(func.count(Review.id)).select_from(stmt.subquery())
    total = await db.scalar(count_stmt)

    stmt = stmt.order_by(Review.created_at.desc())
    offset = (page - 1) * limit
    stmt = stmt.offset(offset).limit(limit)

    result = await db.execute(stmt)
    reviews = result.scalars().all()

    pages = (total + limit - 1) // limit if total else 0
    meta = Meta(page=page, limit=limit, total=total, pages=pages, has_next=page < pages, has_prev=page > 1)

    return PaginatedResponse(items=[ReviewResponse.model_validate(r) for r in reviews], meta=meta)


@router.post("/employer/{employer_id}", response_model=ReviewResponse | ErrorDetail)
async def create_employer_review(
    employer_id: uuid.UUID,
    request: ReviewCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Checking if reviewing own
    if current_user.role == "employer":
        emp_stmt = select(EmployerProfile.id).where(EmployerProfile.user_id == current_user.id)
        current_emp_id = await db.scalar(emp_stmt)
        if current_emp_id == employer_id:
            return error_response("CANNOT_REVIEW_OWN", "Cannot review your own restaurant", 400)

    # Checking duplicate
    dup_stmt = select(Review).where(Review.employer_id == employer_id, Review.author_id == current_user.id)
    if await db.scalar(dup_stmt):
        return error_response("ALREADY_REVIEWED", "You already reviewed this employer", 409)

    review = Review(
        employer_id=employer_id,
        author_id=current_user.id,
        rating=request.rating,
        comment=request.comment
    )
    db.add(review)
    await db.commit()
    await db.refresh(review)

    await recalculate_employer_rating(employer_id, db)

    load_stmt = select(Review).options(selectinload(Review.author)).where(Review.id == review.id)
    res = await db.execute(load_stmt)
    return ReviewResponse.model_validate(res.scalars().first())


@router.delete("/{review_id}", response_model=SuccessResponse | ErrorDetail)
async def delete_review(review_id: uuid.UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if current_user.role != "admin":
        return error_response("NOT_AUTHORIZED", "Only admins can delete reviews", 403)

    stmt = select(Review).where(Review.id == review_id)
    review = await db.scalar(stmt)
    if not review:
        return error_response("REVIEW_NOT_FOUND", "Review not found", 404)

    review.is_visible = False
    await db.commit()
    
    await recalculate_employer_rating(review.employer_id, db)
    return SuccessResponse(message="Review hidden successfully")


# --- Seeker Reviews (Employers Rating Seekers) ---

@router.post("/seeker/{seeker_id}", response_model=SeekerReviewResponse | ErrorDetail)
async def create_seeker_review(
    seeker_id: uuid.UUID,
    request: SeekerReviewCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role != "employer":
        return error_response("NOT_AUTHORIZED", "Only employers can rate seekers", 403)

    emp_stmt = select(EmployerProfile.id).where(EmployerProfile.user_id == current_user.id)
    employer_id = await db.scalar(emp_stmt)
    if not employer_id:
        return error_response("PROFILE_NOT_FOUND", "Employer profile not found", 404)

    # Check eligibility (must have hired the seeker)
    eligibility_stmt = select(func.count(Application.id)).options(selectinload(Application.vacancy)).where(
        Application.seeker_id == seeker_id,
        Application.status == 'hired',
        Application.vacancy.has(employer_id=employer_id) # The application's vacancy must belong to this employer
    )
    if await db.scalar(eligibility_stmt) == 0:
        return error_response("NOT_ELIGIBLE_TO_RATE", "You haven't hired this seeker", 403)

    # Check duplicate
    dup_stmt = select(SeekerReview).where(SeekerReview.seeker_id == seeker_id, SeekerReview.employer_id == employer_id)
    if await db.scalar(dup_stmt):
         return error_response("ALREADY_REVIEWED", "You already rated this seeker", 409)

    s_review = SeekerReview(
        seeker_id=seeker_id,
        employer_id=employer_id,
        rating=request.rating,
        comment=request.comment
    )
    db.add(s_review)
    await db.commit()
    await db.refresh(s_review)

    await recalculate_seeker_rating(seeker_id, db)
    return SeekerReviewResponse.model_validate(s_review)


@router.get("/seeker/{seeker_id}", response_model=PaginatedResponse[SeekerReviewResponse] | ErrorDetail)
async def get_seeker_reviews(
    seeker_id: uuid.UUID,
    page: int = 1,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Depending on your business logic, maybe anyone can view seeker reviews, but the markdown says Employer or Admin
    if current_user.role not in ["employer", "admin"]:
        return error_response("NOT_AUTHORIZED", "Only employers or admins can view seeker reviews", 403)

    stmt = select(SeekerReview).where(SeekerReview.seeker_id == seeker_id)
    
    count_stmt = select(func.count(SeekerReview.id)).select_from(stmt.subquery())
    total = await db.scalar(count_stmt)

    stmt = stmt.order_by(SeekerReview.created_at.desc())
    offset = (page - 1) * limit
    stmt = stmt.offset(offset).limit(limit)

    reviews = await db.scalars(stmt)
    
    pages = (total + limit - 1) // limit if total else 0
    meta = Meta(page=page, limit=limit, total=total, pages=pages, has_next=page < pages, has_prev=page > 1)

    return PaginatedResponse(items=[SeekerReviewResponse.model_validate(r) for r in reviews], meta=meta)


# --- Reports System ---

@router.post("/reports", response_model=SuccessResponse | ErrorDetail)
async def create_report(
    request: ReportCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Prevent duplicate active reports
    dup_stmt = select(Report).where(
        Report.reporter_id == current_user.id,
        Report.target_type == request.target_type,
        Report.target_id == request.target_id,
        Report.status == 'pending'
    )
    if await db.scalar(dup_stmt):
        return error_response("ALREADY_REPORTED", "You already reported this item and it's pending", 409)

    # Validate Target Existence (Skipping complex target validation for brevity unless required by logic)
    # However we'll quickly validate review self-report logic
    if request.target_type == 'review':
        rev_stmt = select(Review.author_id).where(Review.id == request.target_id)
        author_id = await db.scalar(rev_stmt)
        if author_id == current_user.id:
            return error_response("CANNOT_REPORT_OWN", "Cannot report your own review", 400)
            
    report_record = Report(
        reporter_id=current_user.id,
        target_type=request.target_type,
        target_id=request.target_id,
        reason=request.reason,
        description=request.description
    )
    db.add(report_record)

    # Auto-flagging for Reviews if target is a review
    if request.target_type == 'review':
        stmt = select(Review).where(Review.id == request.target_id)
        review = await db.scalar(stmt)
        if review:
            review.is_flagged = True

    await db.commit()
    return SuccessResponse(message="Report submitted successfully")


@router.post("/{review_id}/report", response_model=SuccessResponse | ErrorDetail)
async def report_review_shortcut(
    review_id: uuid.UUID,
    reason: str = Query(..., min_length=1),
    description: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # This is a shortcut for the report endpoint tailored for reviews
    req = ReportCreate(target_type='review', target_id=review_id, reason=reason, description=description)
    return await create_report(request=req, current_user=current_user, db=db)
