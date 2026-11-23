from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import RecommendationResponse
from app.services.recommendation import recommend

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("", response_model=RecommendationResponse)
def get_recommendations(
    seed_textbook_id: str | None = Query(default=None),
    course_code: str | None = Query(default=None, max_length=40),
    limit: int = Query(default=6, ge=1, le=20),
    db: Session = Depends(get_db),
) -> RecommendationResponse:
    return recommend(
        db,
        seed_textbook_id=seed_textbook_id,
        course_code=course_code,
        limit=limit,
    )
