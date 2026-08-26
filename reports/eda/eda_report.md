# RiskGuard AI — Phase 1 EDA

Source dataset: `data/raw/creditcard.csv`  
Raw data was read only; this analysis does not modify it.

## Dataset structure

- Rows: 284,807
- Columns: 31
- Column names: Time, V1, V2, V3, V4, V5, V6, V7, V8, V9, V10, V11, V12, V13, V14, V15, V16, V17, V18, V19, V20, V21, V22, V23, V24, V25, V26, V27, V28, Amount, Class

### Data types

| Column | Data type |
| --- | --- |
| Time | float64 |
| V1 | float64 |
| V2 | float64 |
| V3 | float64 |
| V4 | float64 |
| V5 | float64 |
| V6 | float64 |
| V7 | float64 |
| V8 | float64 |
| V9 | float64 |
| V10 | float64 |
| V11 | float64 |
| V12 | float64 |
| V13 | float64 |
| V14 | float64 |
| V15 | float64 |
| V16 | float64 |
| V17 | float64 |
| V18 | float64 |
| V19 | float64 |
| V20 | float64 |
| V21 | float64 |
| V22 | float64 |
| V23 | float64 |
| V24 | float64 |
| V25 | float64 |
| V26 | float64 |
| V27 | float64 |
| V28 | float64 |
| Amount | float64 |
| Class | int64 |

## Missing values

| Field | Value |
| --- | ---: |
| Time | 0 |
| V1 | 0 |
| V2 | 0 |
| V3 | 0 |
| V4 | 0 |
| V5 | 0 |
| V6 | 0 |
| V7 | 0 |
| V8 | 0 |
| V9 | 0 |
| V10 | 0 |
| V11 | 0 |
| V12 | 0 |
| V13 | 0 |
| V14 | 0 |
| V15 | 0 |
| V16 | 0 |
| V17 | 0 |
| V18 | 0 |
| V19 | 0 |
| V20 | 0 |
| V21 | 0 |
| V22 | 0 |
| V23 | 0 |
| V24 | 0 |
| V25 | 0 |
| V26 | 0 |
| V27 | 0 |
| V28 | 0 |
| Amount | 0 |
| Class | 0 |

## Duplicate rows

- Exact duplicate rows: 1,081

## Class balance

- Legitimate transactions (`Class == 0`): 284,315
- Fraudulent transactions (`Class == 1`): 492
- Fraud percentage: 0.172748563062%

## Amount statistics

| Field | Value |
| --- | ---: |
| count | 284807.000000 |
| mean | 88.349619 |
| std | 250.120109 |
| min | 0.000000 |
| 1% | 0.120000 |
| 5% | 0.920000 |
| 25% | 5.600000 |
| 50% | 22.000000 |
| 75% | 77.165000 |
| 95% | 365.000000 |
| 99% | 1017.970000 |
| max | 25691.160000 |

## Time statistics

`Time` ranges from 0 to 172792 seconds, spanning 48.00 hours. It is an elapsed-time field rather than a calendar timestamp, so dates, weekdays, and time zones cannot be inferred.

| Field | Value |
| --- | ---: |
| count | 284807.000000 |
| mean | 94813.859575 |
| std | 47488.145955 |
| min | 0.000000 |
| 1% | 2422.000000 |
| 5% | 25297.600000 |
| 25% | 54201.500000 |
| 50% | 84692.000000 |
| 75% | 139320.500000 |
| 95% | 164143.400000 |
| 99% | 170560.940000 |
| max | 172792.000000 |

## Visualizations

- `class_distribution.png` — transaction counts by target class.
- `amount_distribution.png` — amount histogram through the 99th percentile; values above it remain included in all calculated statistics.
- `transactions_by_hour.png` — transaction volumes by elapsed hour and class.

## Observations and data-quality notes

- The target is strongly imbalanced: only 0.1727% of transactions are labelled fraudulent.
- The amount distribution is right-skewed: the mean (88.35) exceeds the median (22.00), and the maximum is 25691.16.
- Missing values total 0 across all columns, and there are 1,081 exact duplicate rows.
- `Time` is measured in seconds from an unspecified starting point, limiting calendar-based interpretation.
- Features `V1` through `V28` are anonymized/transformed; their original business meaning is not available from this dataset alone.
