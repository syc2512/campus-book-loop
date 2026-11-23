"""Train a small synthetic-data price model without external dependencies."""

from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

FEATURE_NAMES = [
    "intercept",
    "condition_norm",
    "condition_norm_squared",
    "category_factor",
    "demand_factor",
    "has_notes",
    "edition_current",
    "log_new_price",
]
CATEGORY_FACTORS = [0.9, 1.0, 1.08, 1.16, 1.22]
NEW_PRICES = [39.8, 49.0, 56.0, 69.0, 79.0, 88.0, 96.0]
BASE_DATE = date(2025, 1, 1)
HORIZON_DAYS = 660
ARTIFACT_PATH = Path("apps/api/app/resources/price_model.json")
RESULTS_JSON_PATH = Path("docs/evaluation-results.json")
RESULTS_MD_PATH = Path("docs/evaluation-results.md")


@dataclass(frozen=True)
class Sample:
    condition_grade: int
    category_factor: float
    demand_factor: float
    has_notes: bool
    edition_current: bool
    new_price: float
    target_ratio: float
    listed_at: int


def listed_date(day_offset: int) -> date:
    return BASE_DATE + timedelta(days=day_offset)


def condition_factor(grade: int) -> float:
    return 0.1 + grade * 0.065


def make_features(sample: Sample) -> list[float]:
    condition_norm = sample.condition_grade / 10
    return [
        1.0,
        condition_norm,
        condition_norm**2,
        sample.category_factor,
        sample.demand_factor,
        1.0 if sample.has_notes else 0.0,
        1.0 if sample.edition_current else 0.0,
        math.log1p(sample.new_price) / 10,
    ]


def generate_samples(count: int = 3600, seed: int = 20261122) -> list[Sample]:
    generator = random.Random(seed)
    samples: list[Sample] = []
    for _ in range(count):
        condition_grade = max(1, min(10, round(generator.gauss(7.4, 1.9))))
        category_factor = generator.choice(CATEGORY_FACTORS)
        demand_factor = round(generator.uniform(0.75, 1.45), 2)
        has_notes = generator.random() < 0.58
        edition_current = generator.random() < 0.86
        new_price = generator.choice(NEW_PRICES)
        true_ratio = (
            condition_factor(condition_grade)
            * category_factor
            * demand_factor
            * (0.88 if has_notes else 1.0)
            * (1.0 if edition_current else 0.72)
        )
        observed_ratio = true_ratio + generator.gauss(0, 0.028)
        observed_ratio = max(0.08, min(0.86, observed_ratio))
        listed_at = generator.randint(0, HORIZON_DAYS)
        samples.append(
            Sample(
                condition_grade=condition_grade,
                category_factor=category_factor,
                demand_factor=demand_factor,
                has_notes=has_notes,
                edition_current=edition_current,
                new_price=new_price,
                target_ratio=observed_ratio,
                listed_at=listed_at,
            )
        )
    return samples


def solve_linear_system(matrix: list[list[float]], vector: list[float]) -> list[float]:
    size = len(vector)
    augmented = [row[:] + [vector[index]] for index, row in enumerate(matrix)]
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) < 1e-12:
            raise ValueError("Singular matrix")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        divisor = augmented[column][column]
        augmented[column] = [value / divisor for value in augmented[column]]
        for row in range(size):
            if row == column:
                continue
            multiplier = augmented[row][column]
            augmented[row] = [
                value - multiplier * pivot_value
                for value, pivot_value in zip(
                    augmented[row], augmented[column], strict=True
                )
            ]
    return [augmented[index][-1] for index in range(size)]


def fit_ridge(rows: list[Sample], alpha: float = 0.08) -> list[float]:
    features = [make_features(row) for row in rows]
    width = len(FEATURE_NAMES)
    cross_product = [[0.0 for _ in range(width)] for _ in range(width)]
    cross_target = [0.0 for _ in range(width)]
    for x, row in zip(features, rows, strict=True):
        for left in range(width):
            cross_target[left] += x[left] * row.target_ratio
            for right in range(width):
                cross_product[left][right] += x[left] * x[right]
    for index in range(width):
        cross_product[index][index] += alpha
    return solve_linear_system(cross_product, cross_target)


def predict(weights: list[float], sample: Sample) -> float:
    raw = sum(
        weight * value
        for weight, value in zip(weights, make_features(sample), strict=True)
    )
    return max(0.08, min(0.86, raw))


def rule_prediction(sample: Sample) -> float:
    return max(
        0.08,
        min(
            0.86,
            condition_factor(sample.condition_grade)
            * sample.category_factor
            * sample.demand_factor
            * (0.88 if sample.has_notes else 1.0)
            * (1.0 if sample.edition_current else 0.72),
        ),
    )


def metrics(samples: list[Sample], predictor) -> dict[str, float]:
    absolute_errors = []
    percentage_errors = []
    targets = []
    for sample in samples:
        predicted_ratio = predictor(sample)
        predicted_price = sample.new_price * predicted_ratio
        actual_price = sample.new_price * sample.target_ratio
        absolute_errors.append(abs(predicted_price - actual_price))
        percentage_errors.append(abs(predicted_price - actual_price) / actual_price)
        targets.append(actual_price)
    mean_actual = sum(targets) / len(targets)
    total_variance = sum((value - mean_actual) ** 2 for value in targets)
    residual = sum(
        (
            sample.new_price * predictor(sample)
            - sample.new_price * sample.target_ratio
        )
        ** 2
        for sample in samples
    )
    return {
        "mae": round(sum(absolute_errors) / len(samples), 4),
        "mape": round(sum(percentage_errors) / len(samples), 4),
        "r2": round(1 - residual / total_variance, 4),
    }


def main() -> None:
    random.seed(20261122)
    samples = generate_samples()
    # Time-based split on day boundaries so train and validation never share a
    # listing date.
    samples.sort(key=lambda row: row.listed_at)
    days = sorted({row.listed_at for row in samples})
    cutoff_day = days[int(len(days) * 0.8)]
    train_rows = [row for row in samples if row.listed_at < cutoff_day]
    valid_rows = [row for row in samples if row.listed_at >= cutoff_day]
    train_range = (listed_date(train_rows[0].listed_at), listed_date(train_rows[-1].listed_at))
    valid_range = (listed_date(valid_rows[0].listed_at), listed_date(valid_rows[-1].listed_at))
    weights = fit_ridge(train_rows)
    ridge_predictor = lambda row: predict(weights, row)  # noqa: E731
    rule_results = metrics(valid_rows, rule_prediction)
    model_results = metrics(valid_rows, ridge_predictor)

    artifact = {
        "version": "synthetic-ridge-v2",
        "data_source": "synthetic",
        "feature_order": FEATURE_NAMES,
        "weights": [round(weight, 8) for weight in weights],
        "training_rows": len(train_rows),
        "validation_rows": len(valid_rows),
        "split_strategy": "time",
        "train_date_range": [value.isoformat() for value in train_range],
        "validation_date_range": [value.isoformat() for value in valid_range],
        "random_seed": 20261122,
    }
    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT_PATH.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    results = {
        "status": "synthetic-only",
        "notice": "Do not use these values as evidence of real-market accuracy.",
        "dataset": {
            "name": "deterministic synthetic textbook pricing data",
            "samples": len(samples),
            "train_samples": len(train_rows),
            "validation_samples": len(valid_rows),
            "split_strategy": "time",
            "train_date_range": [value.isoformat() for value in train_range],
            "validation_date_range": [value.isoformat() for value in valid_range],
            "random_seed": 20261122,
        },
        "rule_baseline": rule_results,
        "ridge_model": model_results,
        "model_version": artifact["version"],
    }
    RESULTS_JSON_PATH.write_text(
        json.dumps(results, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    markdown = f"""# 估价模型合成数据实验结果

> **重要声明：以下结果来自合成数据，仅验证训练与评估管线，不能作为真实市场准确率。**

## 数据

- 样本量：{len(samples)}
- 训练集：{len(train_rows)}（{train_range[0]} 至 {train_range[1]}）
- 验证集：{len(valid_rows)}（{valid_range[0]} 至 {valid_range[1]}）
- 切分方式：按合成发布时间排序，前 80% 训练、后 20% 验证
- 随机种子：20261122
- 模型：Ridge 线性回归
- 基线：标准化手册中的乘法规则

## 结果

| 方案 | MAE（元） | MAPE | R² |
| --- | ---: | ---: | ---: |
| 规则基线 | {rule_results["mae"]:.4f} | {rule_results["mape"]:.2%} | \
{rule_results["r2"]:.4f} |
| Ridge 模型 | {model_results["mae"]:.4f} | {model_results["mape"]:.2%} | \
{model_results["r2"]:.4f} |

## 解释边界

生成过程的规则与基线高度相似，因此这组实验不能证明模型优于业务规则。合成数据也没有真实的季节、版本更替或市场漂移，时间切分只验证“按时间排序、只用过去预测未来”的管线；接入真实数据前，必须重新检查泄漏、分布漂移和分组误差。
"""
    RESULTS_MD_PATH.write_text(markdown, encoding="utf-8")
    print(f"Wrote {ARTIFACT_PATH}")
    print(f"Wrote {RESULTS_JSON_PATH}")
    print(f"Wrote {RESULTS_MD_PATH}")
    print(f"Rule baseline: {rule_results}")
    print(f"Ridge model: {model_results}")


if __name__ == "__main__":
    main()
