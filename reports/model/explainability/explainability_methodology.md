# RiskGuard AI — Phase 8 Model Explainability

## Scope and method

This analysis loads `reports/model/xgboost_baseline.json` without fitting, retraining, tuning, or replacing it. It reproduces the Phase 2 model input contract exactly: `Time`, `V1`–`V28`, and `Amount`. Synthetic behavioral fields are not read as model features.

Global importance uses XGBoost's native **gain** importance: the average gain from splits using each feature, as provided by `get_score(importance_type="gain")`. Importance is a model statistic, not causation.

Individual explanations use XGBoost's native `pred_contribs=True` mechanism. Contributions are in raw-margin/log-odds space and sum with the bias term to the model margin. A positive contribution pushes the model toward the fraud class; a negative contribution pushes it away. These are model explanations and do not establish that a feature caused fraud.

## Global feature importance

| global_rank | feature | gain | gain_share_percent |
| ---: | ---: | ---: | ---: |
| 1 | V14 | 7692.874512 | 48.400623 |
| 2 | V10 | 995.020691 | 6.260289 |
| 3 | V4 | 966.796387 | 6.082713 |
| 4 | V8 | 608.274231 | 3.827029 |
| 5 | V12 | 568.492249 | 3.576736 |

The complete ranked table is in `global_feature_importance.csv`. `V14` is the most important feature by gain in this artifact, followed by `V10`, `V4`, `V8`, and `V12`. The V features are anonymized/transformed; no real-world meaning is assigned to them.

## Individual transaction explanations

The requested demonstrated source rows were all available. LOW/MEDIUM/HIGH labels below are the existing Phase 3 risk-engine labels; this explainability layer does not calculate or alter risk scores.

### LOW — source row 28727

Time: 35129.00; Amount: 1.00; ML fraud probability: 0.01587517.

Top positive contributors (toward fraud class):

| feature | contribution_margin |
| ---: | ---: |
| V14 | 3.590232 |
| V8 | 0.084560 |
| V11 | 0.014158 |
| V1 | 0.012442 |

Top negative contributors (away from fraud class):

| feature | contribution_margin |
| ---: | ---: |
| V15 | -1.089477 |
| V10 | -1.087544 |
| V7 | -0.835265 |
| V28 | -0.769584 |
| V22 | -0.765532 |
### MEDIUM — source row 233005

Time: 147404.00; Amount: 2.31; ML fraud probability: 0.00224221.

Top positive contributors (toward fraud class):

| feature | contribution_margin |
| ---: | ---: |
| V14 | 1.239342 |
| V4 | 1.229327 |
| V28 | 0.332187 |
| V18 | 0.105878 |
| V27 | 0.090659 |

Top negative contributors (away from fraud class):

| feature | contribution_margin |
| ---: | ---: |
| V8 | -2.177649 |
| V22 | -1.602616 |
| V10 | -1.512029 |
| V1 | -1.136557 |
| V6 | -0.892037 |
### HIGH — source row 215984

Time: 140308.00; Amount: 592.90; ML fraud probability: 0.99998748.

Top positive contributors (toward fraud class):

| feature | contribution_margin |
| ---: | ---: |
| V14 | 3.488233 |
| V10 | 2.245667 |
| V12 | 2.101354 |
| V4 | 1.027917 |
| V17 | 0.766342 |

Top negative contributors (away from fraud class):

| feature | contribution_margin |
| ---: | ---: |
| V8 | -0.781965 |
| V27 | -0.585138 |
| V24 | -0.556833 |
| V23 | -0.431718 |
| V5 | -0.424945 |

Full feature-level contributions for all 30 features per example are in `individual_feature_contributions.csv`, and structured summaries are in `example_transaction_explanations.json`.

## Global versus individual importance

The globally highest-gain feature, `V14`, is the top positive contributor for all three selected examples. `V10` is globally second and is a strong negative contributor for LOW and MEDIUM but a strong positive contributor for HIGH. `V4` is also globally important and appears among the strongest positive contributors for MEDIUM and HIGH. This shows that global and individual importance can overlap without being identical; the comparison is descriptive, not causal.

## Prediction and separation checks

- The saved artifact loaded successfully with 30 expected features.
- Predictions before and after contribution calculation were unchanged; maximum probability delta was 0.000e+00.
- Native contribution sums reconstructed model probabilities within 9.313e-09 absolute error.
- No training, fitting, thresholding, risk-engine, behavioral-rule, investigator, or dashboard code was invoked or modified.
- `data/raw/creditcard.csv` was read only.

## Limitations

- `V1`–`V28` are anonymized/transformed features, so real-world meanings must not be invented.
- Feature contribution is a model explanation, not a causal explanation.
- XGBoost feature importance can differ by importance method; this report uses gain.
- An explanation does not prove fraud.
- The model remains a baseline and is not a production-validated fraud system.
