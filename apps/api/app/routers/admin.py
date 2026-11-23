from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_role
from app.models import AuditEvent, BookListing, Order, Textbook, User
from app.routers.listings import to_listing_read
from app.schemas import (
    AdminOrderRead,
    ListingModeration,
    ListingRead,
    OrderRead,
    OrderRefund,
)
from app.services.order_service import _order_title, serialize_order

router = APIRouter(prefix="/admin", tags=["admin"])

ListingStatus = Literal["active", "removed", "reserved", "sold"]
OrderStatus = Literal["pending_payment", "paid", "completed", "cancelled", "refunded"]


@router.get("/listings", response_model=list[ListingRead])
def admin_listings(
    status: ListingStatus | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
) -> list[ListingRead]:
    statement = (
        select(BookListing, Textbook, User)
        .join(Textbook, BookListing.textbook_id == Textbook.id)
        .join(User, BookListing.seller_id == User.id)
        .order_by(BookListing.created_at.desc())
        .limit(limit)
    )
    if status:
        statement = statement.where(BookListing.status == status)
    rows = db.execute(statement).all()
    return [to_listing_read(*row) for row in rows]


@router.get("/orders", response_model=list[AdminOrderRead])
def admin_orders(
    status: OrderStatus | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
) -> list[AdminOrderRead]:
    statement = select(Order).order_by(Order.created_at.desc()).limit(limit)
    if status:
        statement = statement.where(Order.status == status)
    orders = db.scalars(statement).all()
    return [
        AdminOrderRead(
            **serialize_order(order, _order_title(db, order)).model_dump(),
            buyer_name=order.buyer.display_name,
            seller_name=order.seller.display_name,
        )
        for order in orders
    ]


@router.patch("/listings/{listing_id}", response_model=dict)
def moderate_listing(
    listing_id: str,
    payload: ListingModeration,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role("admin")),
) -> dict:
    listing = db.get(BookListing, listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.status in {"reserved", "sold"}:
        raise HTTPException(
            status_code=409, detail="A reserved or sold listing cannot be moderated"
        )
    previous = listing.status
    listing.status = payload.status
    db.add(
        AuditEvent(
            actor_id=admin.id,
            action="listing.moderated",
            entity_type="listing",
            entity_id=listing.id,
            payload={"from": previous, "to": payload.status, "reason": payload.reason},
        )
    )
    db.commit()
    return {"id": listing.id, "status": listing.status}


@router.post("/orders/{order_id}/refund", response_model=OrderRead)
def refund_order(
    order_id: str,
    payload: OrderRefund,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role("admin")),
) -> OrderRead:
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status != "paid":
        raise HTTPException(status_code=409, detail="Only paid orders can be refunded")
    order.status = "refunded"
    order.updated_at = datetime.now(UTC)
    listing = db.get(BookListing, order.listing_id)
    if listing:
        listing.status = "active"
    db.add(
        AuditEvent(
            actor_id=admin.id,
            action="order.refunded_sandbox",
            entity_type="order",
            entity_id=order.id,
            payload={"reason": payload.reason, "provider": "sandbox"},
        )
    )
    db.commit()
    db.refresh(order)
    return serialize_order(order, _order_title(db, order))


@router.get("/metrics", response_model=dict)
def metrics(
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
) -> dict:
    active_listings = db.query(BookListing).filter(BookListing.status == "active").count()
    completed_orders = db.query(Order).filter(Order.status == "completed").count()
    textbooks = db.query(Textbook).count()
    return {
        "textbooks": textbooks,
        "active_listings": active_listings,
        "completed_orders": completed_orders,
    }
