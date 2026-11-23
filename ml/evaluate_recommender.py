"""Offline evaluation for catalogue recommendation strategies.

The interaction log is synthetic: users prefer one course and occasionally a
second course, so content and course-aware methods have an advantage by
construction. This script proves the evaluation pipeline and makes the
comparison reproducible; it does not estimate real student behaviour.
"""

from __future__ import annotations

import json
import math
import random
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

SEED = 20261122
USER_COUNT = 300
TOP_K = 10
RESULTS_JSON_PATH = Path("docs/evaluation-recommender.json")
RESULTS_MD_PATH = Path("docs/evaluation-recommender.md")

COURSES = [
    ("MATH101", "高等数学", "理工类", "公共课"),
    ("CS101", "程序设计基础", "计算机", "专业课"),
    ("AI101", "人工智能导论", "人工智能", "专业课"),
    ("CS202", "数据结构", "计算机", "专业课"),
    ("ENG101", "大学英语", "全校", "公共课"),
    ("AI201", "机器学习", "人工智能", "专业课"),
    ("STAT201", "概率论与数理统计", "理工类", "公共课"),
    ("ECON101", "西方经济学", "经管类", "专业课"),
]
SUFFIXES = ["教程", "习题集", "实验指导", "导论", "进阶"]


@dataclass(frozen=True)
class Book:
    id: str
    title: str
    course_code: str
    course_name: str
    major: str
    category: str

    @property
    def text(self) -> str:
        return f"{self.title}{self.course_name}{self.major}{self.category}"


@dataclass(frozen=True)
class UserHistory:
    train_ids: frozenset[str]
    test_id: str


def build_catalog() -> list[Book]:
    catalog: list[Book] = []
    for course_index, (code, name, major, category) in enumerate(COURSES):
        for suffix_index, suffix in enumerate(SUFFIXES):
            catalog.append(
                Book(
                    id=f"B{course_index:02d}{suffix_index}",
                    title=f"{name}{suffix}",
                    course_code=code,
                    course_name=name,
                    major=major,
                    category=category,
                )
            )
    return catalog


def build_users(catalog: list[Book], generator: random.Random) -> list[UserHistory]:
    # Modest per-book popularity skew; course preference dominates.
    book_weights = [generator.lognormvariate(0, 0.35) for _ in catalog]
    histories: list[UserHistory] = []
    for _ in range(USER_COUNT):
        preferred = generator.randrange(len(COURSES))
        secondary = generator.choice([i for i in range(len(COURSES)) if i != preferred])
        weights = []
        for book_index, book in enumerate(catalog):
            course_index = int(book.id[1:3])
            if course_index == preferred:
                affinity = 2.8
            elif course_index == secondary:
                affinity = 1.2
            else:
                affinity = 0.22
            weights.append(affinity * book_weights[book_index])

        selected: list[Book] = []
        pool = list(catalog)
        pool_weights = list(weights)
        interaction_count = generator.randint(6, 12)
        for _ in range(interaction_count):
            total = sum(pool_weights)
            threshold = generator.random() * total
            cumulative = 0.0
            chosen_index = len(pool) - 1
            for index, weight in enumerate(pool_weights):
                cumulative += weight
                if threshold <= cumulative:
                    chosen_index = index
                    break
            selected.append(pool.pop(chosen_index))
            pool_weights.pop(chosen_index)

        histories.append(
            UserHistory(
                train_ids=frozenset(book.id for book in selected[:-1]),
                test_id=selected[-1].id,
            )
        )
    return histories


def bigrams(value: str) -> set[str]:
    normalized = re.sub(r"\s+", "", value.lower())
    if len(normalized) < 2:
        return {normalized} if normalized else set()
    return {normalized[index : index + 2] for index in range(len(normalized) - 1)}


def similarity(left: str, right: str) -> float:
    a, b = bigrams(left), bigrams(right)
    if not a or not b:
        return 0.0
    return len(a & b) / math.sqrt(len(a) * len(b))


def rank_books(
    strategy: str,
    history: UserHistory,
    catalog: list[Book],
    by_id: dict[str, Book],
    popularity: Counter[str],
    max_popularity: int,
) -> list[str]:
    seen = history.train_ids
    ordered_seen = sorted(seen)
    profile_text = "".join(by_id[book_id].text for book_id in ordered_seen)
    course_counts = Counter(by_id[book_id].course_code for book_id in ordered_seen)
    top_course = course_counts.most_common(1)[0][0]

    scored: list[tuple[float, str]] = []
    for book in catalog:
        if book.id in seen:
            continue
        content = similarity(profile_text, book.text)
        course_match = 1.0 if book.course_code == top_course else 0.0
        popularity_score = popularity[book.id] / max_popularity if max_popularity else 0.0

        if strategy == "popularity":
            score = popularity_score
        elif strategy == "content":
            score = content + 0.0001 * popularity_score
        else:
            score = 0.6 * content + 0.25 * course_match + 0.15 * popularity_score
        scored.append((score, book.id))

    scored.sort(key=lambda row: (-row[0], row[1]))
    return [book_id for _, book_id in scored[:TOP_K]]


def evaluate(
    strategy: str,
    histories: list[UserHistory],
    catalog: list[Book],
    popularity: Counter[str],
) -> dict[str, float]:
    by_id = {book.id: book for book in catalog}
    max_popularity = max(popularity.values(), default=0)
    recalls: list[float] = []
    ndcgs: list[float] = []
    recommended_books: set[str] = set()

    for history in histories:
        ranking = rank_books(strategy, history, catalog, by_id, popularity, max_popularity)
        recommended_books.update(ranking)
        if history.test_id in ranking:
            rank = ranking.index(history.test_id) + 1
            recalls.append(1.0)
            ndcgs.append(1.0 / math.log2(rank + 1))
        else:
            recalls.append(0.0)
            ndcgs.append(0.0)

    return {
        "recall_at_10": round(sum(recalls) / len(recalls), 4),
        "ndcg_at_10": round(sum(ndcgs) / len(ndcgs), 4),
        "coverage": round(len(recommended_books) / len(catalog), 4),
    }


def main() -> None:
    generator = random.Random(SEED)
    catalog = build_catalog()
    histories = build_users(catalog, generator)
    popularity = Counter(book_id for history in histories for book_id in history.train_ids)

    results = {
        "status": "synthetic-only",
        "notice": (
            "Interactions are generated from course affinity; do not treat "
            "these values as real-world recommendation quality."
        ),
        "dataset": {
            "name": "deterministic synthetic course-affinity interactions",
            "users": len(histories),
            "catalog_items": len(catalog),
            "random_seed": SEED,
            "train_interactions": sum(len(history.train_ids) for history in histories),
            "held_out_items": len(histories),
            "split_strategy": "per-user leave-last-out (chronological interaction order)",
        },
        "metrics": {
            "popularity": evaluate("popularity", histories, catalog, popularity),
            "content": evaluate("content", histories, catalog, popularity),
            "hybrid": evaluate("hybrid", histories, catalog, popularity),
        },
    }

    RESULTS_JSON_PATH.write_text(
        json.dumps(results, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    rows = "\n".join(
        f"| {name} | {values['recall_at_10']:.4f} | "
        f"{values['ndcg_at_10']:.4f} | {values['coverage']:.4f} |"
        for name, values in results["metrics"].items()
    )
    markdown = f"""# 推荐策略合成数据评估

> **重要声明：交互数据由课程偏好规则生成，内容与课程感知方法天然占优。**
> **以下结果只验证评估管线，不能作为真实推荐效果。**

## 数据

- 用户数：{results['dataset']['users']}
- 教材条目：{results['dataset']['catalog_items']}
- 训练交互：{results['dataset']['train_interactions']}
- 留出物品：每位用户 1 本
- 随机种子：{SEED}
- 切分方式：按交互产生顺序，每位用户最后一次交互作为测试物品，其余作为历史

## 策略

- **热门**：按训练集交互次数排序；
- **内容**：用户历史文本与候选教材的二元组余弦相似度；
- **混合**：0.60 × 内容 + 0.25 × 同课程 + 0.15 × 热门度。

## 结果

| 策略 | Recall@10 | NDCG@10 | 覆盖率 |
| --- | ---: | ---: | ---: |
{rows}

## 解释边界

- 合成用户明确偏好某一课程，因此“同课程”和内容相似必然有效，结果不能外推到真实学生；
- 时间切分采用逐用户留出最后一次交互，不是全局时间切分；
- 真实数据需要按全局曝光时间切分，并去重同一用户的重复曝光；
- 没有真实点击、收藏、成交和曝光数据，也没有冷启动用户；
- 覆盖率按被推荐过的不同教材数除以目录大小计算；
- 接入真实行为数据后，需要补充分组误差与基线方差。
"""
    RESULTS_MD_PATH.write_text(markdown, encoding="utf-8")

    print(f"Wrote {RESULTS_JSON_PATH}")
    print(f"Wrote {RESULTS_MD_PATH}")
    for name, values in results["metrics"].items():
        print(f"{name}: {values}")


if __name__ == "__main__":
    main()
