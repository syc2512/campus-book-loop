import math
import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BookListing, Textbook
from app.schemas import RecommendationItem, RecommendationResponse, TextbookRead


def _bigrams(value: str) -> set[str]:
    normalized = re.sub(r"\s+", "", value.lower())
    if len(normalized) < 2:
        return {normalized} if normalized else set()
    return {normalized[index : index + 2] for index in range(len(normalized) - 1)}


def _content_similarity(left: str, right: str) -> float:
    a, b = _bigrams(left), _bigrams(right)
    if not a or not b:
        return 0.0
    return len(a & b) / math.sqrt(len(a) * len(b))


@dataclass
class AvailableBook:
    textbook: Textbook
    count: int
    lowest_price: float


def recommend(
    db: Session,
    seed_textbook_id: str | None = None,
    course_code: str | None = None,
    limit: int = 6,
) -> RecommendationResponse:
    listings = db.execute(
        select(BookListing, Textbook)
        .join(Textbook, BookListing.textbook_id == Textbook.id)
        .where(BookListing.status == "active")
    ).all()

    grouped: dict[str, list[tuple[BookListing, Textbook]]] = {}
    for listing, textbook in listings:
        grouped.setdefault(textbook.id, []).append((listing, textbook))

    available = [
        AvailableBook(
            textbook=rows[0][1],
            count=len(rows),
            lowest_price=min(row[0].asking_price for row in rows),
        )
        for rows in grouped.values()
    ]

    seed = db.get(Textbook, seed_textbook_id) if seed_textbook_id else None
    max_count = max((item.count for item in available), default=1)

    scored: list[tuple[float, str, AvailableBook]] = []
    for item in available:
        if seed and item.textbook.id == seed.id:
            continue

        content = 0.0
        if seed:
            content = _content_similarity(
                f"{seed.title}{seed.course_name}{seed.major}{seed.category}",
                f"{item.textbook.title}{item.textbook.course_name}"
                f"{item.textbook.major}{item.textbook.category}",
            )
        course_match = 1.0 if course_code and item.textbook.course_code == course_code else 0.0
        seed_course_match = (
            1.0 if seed and item.textbook.course_code == seed.course_code else 0.0
        )
        popularity = item.count / max_count
        affordability = max(
            0.0,
            min(1.0, 1.0 - item.lowest_price / max(item.textbook.new_price, 0.01)),
        )
        score = (
            content * 0.35
            + seed_course_match * 0.25
            + course_match * 0.2
            + popularity * 0.1
            + affordability * 0.1
        )

        reasons = []
        if seed_course_match:
            reasons.append("同课程")
        if course_match:
            reasons.append("符合筛选课程")
        if content >= 0.12:
            reasons.append("教材内容相近")
        if item.count >= max_count:
            reasons.append("当前供给最活跃")
        if not reasons:
            reasons.append("价格与品相综合推荐")
        scored.append((score, "、".join(reasons), item))

    scored.sort(key=lambda row: (-row[0], row[2].lowest_price, row[2].textbook.title))
    items = [
        RecommendationItem(
            textbook=TextbookRead.model_validate(item.textbook),
            available_count=item.count,
            lowest_price=item.lowest_price,
            reason=reason,
            score=round(score, 4),
        )
        for score, reason, item in scored[:limit]
    ]
    return RecommendationResponse(strategy="content_popularity_baseline", items=items)
