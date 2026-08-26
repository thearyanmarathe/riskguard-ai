# RiskGuard AI — Phase 2 Baseline Classifiers

Source dataset: `data/raw/creditcard.csv`  
The raw CSV was read only. No data was written to `data/raw/`.

## Duplicate investigation

`pandas.DataFrame.duplicated(keep="first")` identifies **1,081 duplicate rows**: records identical to an earlier row.

| Duplicate class | Rows | Proportion of duplicate rows |
| --- | ---: | ---: |
| Legitimate (`Class == 0`) | 1,062 | 98.2424% |
| Fraudulent (`Class == 1`) | 19 | 1.7576% |

There are 1,854 rows when counting both original and repeated members of duplicate groups. Exact duplicates were removed **only in memory before splitting**, leaving 283,726 unique records. This avoids the same record leaking into both training and test data, which can inflate evaluation results. The raw dataset remains unchanged.

## Reproducible split

- Random seed: 42
- Stratified split: 80% train / 20% test after in-memory deduplication
- Train rows: 226,980 — legitimate: 226,602; fraudulent: 378
- Test rows: 56,746 — legitimate: 56,651; fraudulent: 95

Scaling is fitted by the Logistic Regression pipeline on training data only. The test set is used only for final evaluation.

## Evaluation on the untouched test set

| Model | Precision | Recall | F1-score | PR-AUC / Average Precision |
| --- | ---: | ---: | ---: | ---: |
| Logistic Regression | 0.056386 | 0.873684 | 0.105935 | 0.671924 |
| XGBoost | 0.914634 | 0.789474 | 0.847458 | 0.821925 |

### Logistic Regression confusion matrix

| Actual / predicted | Legitimate | Fraudulent |
| --- | ---: | ---: |
| Legitimate | 55,262 | 1,389 |
| Fraudulent | 12 | 83 |

### XGBoost confusion matrix

| Actual / predicted | Legitimate | Fraudulent |
| --- | ---: | ---: |
| Legitimate | 56,644 | 7 |
| Fraudulent | 20 | 75 |

## Comparison and limitations

XGBoost has the higher Average Precision on this split, so it is the stronger baseline for ranking likely fraud cases. Accuracy is not a primary metric here: a model predicting every transaction as legitimate would be about 99.833% accurate while detecting no fraud.

The models use their default 0.5 decision threshold for precision, recall, and F1. Threshold selection, calibration, cross-validation, and hyperparameter tuning are intentionally outside this baseline phase.
