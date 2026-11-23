from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import AuditEvent, BookListing, Order, Textbook, User
from app.schemas import OrderCreate, OrderRead

COMMISSION_RATE = 0.03


def serialize_order(order: Order, textbook_title: str) -> OrderRead:
    return OrderRead(
        id=order.id,
        listing_id=order.listing_id,
        textbook_title=textbook_title,
        buyer_id=order.buyer_id,
        seller_id=order.seller_id,
        amount=order.amount,
        commission_amount=order.commission_amount,
        status=order.status,
        idempotency_key=order.idempotency_key,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


def _order_title(db: Session, order: Order) -> str:
    row = db.execute(
        select(Textbook.title)
        .join(BookListing, BookListing.textbook_id == Textbook.id)
        .where(BookListing.id == order.listing_id)
    ).scalar_one_or_none()
    return row or "Unknown textbook"


def create_order(db: Session, buyer: User, payload: OrderCreate) -> tuple[Order, bool]:
    existing = db.scalar(select(Order).where(Order.idempotency_key == payload.idempotency_key))
    if existing:
        if existing.buyer_id != buyer.id:
            raise HTTPException(status_code=409, detail="Idempotency key belongs to another buyer")
        return existing, True

    listing = db.get(BookListing, payload.listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.status != "active":
        raise HTTPException(status_code=409, detail="Listing is no longer available")
    if listing.seller_id == buyer.id:
        raise HTTPException(status_code=400, detail="You cannot buy your own listing")

    order = Order(
        listing_id=listing.id,
        buyer_id=buyer.id,
        seller_id=listing.seller_id,
        amount=listing.asking_price,
        commission_amount=round(listing.asking_price * COMMISSION_RATE, 2),
        status="pending_payment",
        idempotency_key=payload.idempotency_key,
    )
    listing.status = "reserved"
    db.add(order)
    db.flush()
    db.add(
        AuditEvent(
            actor_id=buyer.id,
            action="order.created",
            entity_type="order",
            entity_id=order.id,
            payload={"listing_id": listing.id, "amount": order.amount},
        )
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        existing = db.scalar(select(Order).where(Order.idempotency_key == payload.idempotency_key))
        if existing and existing.buyer_id == buyer.id:
            return existing, True
        raise HTTPException(status_code=409, detail="The listing was just reserved") from exc
    db.refresh(order)
    return order, False


def list_orders(db: Session, user: User) -> list[OrderRead]:
    orders = db.scalars(
        select(Order)
        .where(or_(Order.buyer_id == user.id, Order.seller_id == user.id))
        .order_by(Order.created_at.desc())
    ).all()
    return [serialize_order(order, _order_title(db, order)) for order in orders]


def pay_order(db: Session, order_id: str, user: User) -> OrderRead:
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.buyer_id != user.id:
        raise HTTPException(status_code=403, detail="Only the buyer can pay this order")
    if order.status != "pending_payment":
        raise HTTPException(status_code=409, detail=f"Cannot pay an order in {order.status}")
    order.status = "paid"
    order.updated_at = datetime.now(UTC)
    db.add(
        AuditEvent(
            actor_id=user.id,
            action="order.paid_sandbox",
            entity_type="order",
            entity_id=order.id,
            payload={"provider": "sandbox", "amount": order.amount},
        )
    )
    db.commit()
    db.refresh(order)
    return serialize_order(order, _order_title(db, order))


def complete_order(db: Session, order_id: str, user: User) -> OrderRead:
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.buyer_id != user.id:
        raise HTTPException(status_code=403, detail="Only the buyer can confirm handover")
    if order.status != "paid":
        raise HTTPException(status_code=409, detail=f"Cannot complete an order in {order.status}")
    order.status = "completed"
    order.updated_at = datetime.now(UTC)
    listing = db.get(BookListing, order.listing_id)
    if listing:
        listing.status = "sold"
    db.add(
        AuditEvent(
            actor_id=user.id,
            action="order.completed",
            entity_type="order",
            entity_id=order.id,
            payload={"amount": order.amount},
        )
    )
    db.commit()
    db.refresh(order)
    return serialize_order(order, _order_title(db, order))


def cancel_order(db: Session, order_id: str, user: User) -> OrderRead:
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    if user.id not in {order.buyer_id, order.seller_id}:
        raise HTTPException(status_code=403, detail="You cannot cancel this order")
    if order.status != "pending_payment":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Paid orders must use the administrator refund flow",
        )
    order.status = "cancelled"
    order.updated_at = datetime.now(UTC)
    listing = db.get(BookListing, order.listing_id)
    if listing:
        listing.status = "active"
    db.add(
        AuditEvent(
            actor_id=user.id,
            action="order.cancelled",
            entity_type="order",
            entity_id=order.id,
            payload={},
        )
    )
    db.commit()
    db.refresh(order)
    return serialize_order(order, _order_title(db, order))
