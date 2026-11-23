from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import OrderCreate, OrderRead
from app.services.order_service import (
    _order_title,
    cancel_order,
    complete_order,
    create_order,
    list_orders,
    pay_order,
    serialize_order,
)

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("", response_model=list[OrderRead])
def get_orders(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[OrderRead]:
    return list_orders(db, user)


@router.post("", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
def post_order(
    payload: OrderCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OrderRead:
    order, _ = create_order(db, user, payload)
    return serialize_order(order, _order_title(db, order))


@router.post("/{order_id}/pay", response_model=OrderRead)
def pay(
    order_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OrderRead:
    return pay_order(db, order_id, user)


@router.post("/{order_id}/complete", response_model=OrderRead)
def complete(
    order_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OrderRead:
    return complete_order(db, order_id, user)


@router.post("/{order_id}/cancel", response_model=OrderRead)
def cancel(
    order_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OrderRead:
    return cancel_order(db, order_id, user)
