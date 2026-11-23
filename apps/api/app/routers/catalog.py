from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Textbook
from app.schemas import TextbookRead

router = APIRouter(prefix="/textbooks", tags=["catalog"])


@router.get("", response_model=list[TextbookRead])
def list_textbooks(
    q: str | None = Query(default=None, max_length=100),
    course_code: str | None = Query(default=None, max_length=40),
    major: str | None = Query(default=None, max_length=120),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[TextbookRead]:
    statement = select(Textbook)
    if q:
        term = f"%{q.strip()}%"
        statement = statement.where(
            or_(
                Textbook.title.ilike(term),
                Textbook.author.ilike(term),
                Textbook.isbn.ilike(term),
                Textbook.course_name.ilike(term),
            )
        )
    if course_code:
        statement = statement.where(Textbook.course_code == course_code)
    if major:
        statement = statement.where(Textbook.major == major)
    textbooks = db.scalars(
        statement.order_by(Textbook.course_code, Textbook.title).limit(limit).offset(offset)
    ).all()
    return [TextbookRead.model_validate(item) for item in textbooks]


@router.get("/{textbook_id}", response_model=TextbookRead)
def get_textbook(textbook_id: str, db: Session = Depends(get_db)) -> TextbookRead:
    textbook = db.get(Textbook, textbook_id)
    if textbook is None:
        raise HTTPException(status_code=404, detail="Textbook not found")
    return TextbookRead.model_validate(textbook)
