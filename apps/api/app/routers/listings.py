from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import BookListing, Textbook, User
from app.schemas import ImageUploadResponse, ListingCreate, ListingRead
from app.services.storage import ImageValidationError, save_listing_image

router = APIRouter(prefix="/listings", tags=["listings"])


def to_listing_read(listing: BookListing, textbook: Textbook, seller: User) -> ListingRead:
    return ListingRead(
        id=listing.id,
        seller_id=listing.seller_id,
        seller_name=seller.display_name,
        textbook_id=textbook.id,
        textbook_title=textbook.title,
        course_name=textbook.course_name,
        major=textbook.major,
        edition=textbook.edition,
        new_price=textbook.new_price,
        condition_grade=listing.condition_grade,
        asking_price=listing.asking_price,
        note=listing.note,
        image_url=listing.image_url,
        status=listing.status,
        created_at=listing.created_at,
    )


@router.get("", response_model=list[ListingRead])
def list_listings(
    q: str | None = Query(default=None, max_length=100),
    course_code: str | None = Query(default=None, max_length=40),
    limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[ListingRead]:
    statement = (
        select(BookListing, Textbook, User)
        .join(Textbook, BookListing.textbook_id == Textbook.id)
        .join(User, BookListing.seller_id == User.id)
        .where(BookListing.status == "active")
    )
    if q:
        term = f"%{q.strip()}%"
        statement = statement.where(
            Textbook.title.ilike(term)
            | Textbook.course_name.ilike(term)
            | Textbook.isbn.ilike(term)
        )
    if course_code:
        statement = statement.where(Textbook.course_code == course_code)
    rows = db.execute(
        statement.order_by(BookListing.created_at.desc()).limit(limit)
    ).all()
    return [to_listing_read(listing, textbook, seller) for listing, textbook, seller in rows]


@router.post(
    "/images",
    response_model=ImageUploadResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["listings"],
)
async def upload_listing_image(
    file: UploadFile = File(...),
    _user: User = Depends(get_current_user),
) -> ImageUploadResponse:
    data = await file.read(settings.max_image_bytes + 1)
    if len(data) > settings.max_image_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"The image exceeds the {settings.max_image_bytes // (1024 * 1024)} MB limit",
        )
    try:
        stored = save_listing_image(data, file.content_type)
    except ImageValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=str(exc),
        ) from exc
    return ImageUploadResponse(
        image_url=stored.image_url,
        content_type=stored.content_type,
        byte_size=stored.byte_size,
    )


@router.post("", response_model=ListingRead, status_code=status.HTTP_201_CREATED)
def create_listing(
    payload: ListingCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ListingRead:
    textbook = db.get(Textbook, payload.textbook_id)
    if textbook is None:
        raise HTTPException(status_code=404, detail="Textbook not found")
    if payload.asking_price > textbook.new_price * 0.9:
        raise HTTPException(
            status_code=422,
            detail="Asking price must not exceed 90% of the current new-book price",
        )
    listing = BookListing(
        seller_id=user.id,
        textbook_id=textbook.id,
        condition_grade=payload.condition_grade,
        asking_price=payload.asking_price,
        note=payload.note.strip(),
        image_url=payload.image_url,
        status="active",
    )
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return to_listing_read(listing, textbook, user)


@router.get("/{listing_id}", response_model=ListingRead)
def get_listing(listing_id: str, db: Session = Depends(get_db)) -> ListingRead:
    row = db.execute(
        select(BookListing, Textbook, User)
        .join(Textbook, BookListing.textbook_id == Textbook.id)
        .join(User, BookListing.seller_id == User.id)
        .where(BookListing.id == listing_id)
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    return to_listing_read(*row)
