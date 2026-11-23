# Price Model Experiment

This directory contains a deliberately small, dependency-free experiment for the first Campus Book Loop price model.

The current model is **trained on synthetic data only**. It exists to demonstrate:

- a deterministic data generator;
- a transparent rule baseline;
- a reproducible feature matrix and ridge regression fit;
- held-out evaluation;
- an inspectable JSON model artifact used by the API.

It is not evidence of real-world pricing accuracy.

## Run

From the repository root:

```bash
python ml/train_price_model.py
```

The script writes:

- `apps/api/app/resources/price_model.json`
- `docs/evaluation-results.json`
- `docs/evaluation-results.md`

## Recommendation evaluation

`evaluate_recommender.py` compares popularity, content and hybrid ranking on
synthetic course-affinity interactions:

```bash
python ml/evaluate_recommender.py
```

It writes `docs/evaluation-recommender.json` and `.md` with Recall@10,
NDCG@10 and coverage. The interactions are synthetic and generated from
course preferences, so the content-aware methods win by construction. Each
user's last interaction is held out in chronological order. The numbers
demonstrate the evaluation pipeline, not real student behaviour.

The pricing experiment sorts synthetic listings by publication date and splits
on a day boundary, so training and validation never share a date. This checks
the time-split pipeline; synthetic data has no real seasonal drift.

## Next step

Replace the synthetic generator with an authorized, de-identified data card before making any real-market claim. Keep the rule baseline and time-based validation split when the real dataset is introduced.
