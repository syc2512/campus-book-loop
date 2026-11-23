import json
import math
from pathlib import Path

from app.core.config import settings
from app.schemas import PriceEstimateRequest, PriceEstimateResponse

CATEGORY_FACTORS = {
    "公共课": 1.0,
    "专业课": 1.08,
    "考研资料": 1.16,
    "笔记/真题": 1.22,
    "通识读物": 0.9,
}


def _condition_factor(grade: int) -> float:
    return round(0.1 + grade * 0.065, 4)


def _rule_ratio(request: PriceEstimateRequest) -> tuple[float, dict[str, float]]:
    factors = {
        "condition": _condition_factor(request.condition_grade),
        "category": CATEGORY_FACTORS.get(request.category, 1.0),
        "demand": request.demand_factor,
        "notes": 0.88 if request.has_notes else 1.0,
        "edition": 1.0 if request.edition_current else 0.72,
    }
    ratio = (
        factors["condition"]
        * factors["category"]
        * factors["demand"]
        * factors["notes"]
        * factors["edition"]
    )
    return max(0.08, min(0.86, ratio)), factors


def _load_model() -> dict | None:
    path = Path(__file__).resolve().parents[1] / "resources" / "price_model.json"
    if not path.exists():
        alt_path = Path(settings.model_dir) / "price_model.json"
        path = alt_path
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def estimate_price(request: PriceEstimateRequest) -> PriceEstimateResponse:
    rule_ratio, factors = _rule_ratio(request)
    model = _load_model()
    source = "rule_v1"
    version = "rule-v1"
    ratio = rule_ratio

    if model:
        feature_values = [
            1.0,
            request.condition_grade / 10,
            (request.condition_grade / 10) ** 2,
            factors["category"],
            request.demand_factor,
            1.0 if request.has_notes else 0.0,
            1.0 if request.edition_current else 0.0,
            math.log1p(request.new_price) / 10,
        ]
        weights = model.get("weights", [])
        if isinstance(weights, list) and len(weights) == len(feature_values):
            predicted = sum(
                value * weight
                for value, weight in zip(feature_values, weights, strict=True)
            )
            ratio = max(0.08, min(0.86, float(predicted)))
            source = "synthetic_price_model"
            version = str(model.get("version", "synthetic-v1"))
            factors["rule_ratio"] = round(rule_ratio, 4)
            factors["model_ratio"] = round(ratio, 4)

    mid = round(request.new_price * ratio, 2)
    low = round(max(1.0, mid * 0.9), 2)
    high = round(min(request.new_price * 0.9, mid * 1.1), 2)
    return PriceEstimateResponse(
        suggested_price=mid,
        low_price=low,
        high_price=high,
        source=source,
        model_version=version,
        factors={key: round(value, 4) for key, value in factors.items()},
        disclaimer=(
            "估价仅用于参考。合成模型结果不能代表真实市场准确率，最终价格需买卖双方确认。"
        ),
    )
