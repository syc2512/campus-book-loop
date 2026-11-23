from fastapi import APIRouter

from app.schemas import PriceEstimateRequest, PriceEstimateResponse
from app.services.pricing import estimate_price

router = APIRouter(prefix="/pricing", tags=["pricing"])


@router.post("/estimate", response_model=PriceEstimateResponse)
def estimate(payload: PriceEstimateRequest) -> PriceEstimateResponse:
    return estimate_price(payload)
