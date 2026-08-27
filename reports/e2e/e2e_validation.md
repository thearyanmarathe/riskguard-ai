# RiskGuard AI — Phase 14 End-to-End Validation

This is a read-only validation of existing saved assessments, Investigator integration, optional-provider fallback, FastAPI, and Streamlit display helpers. No model training, behavioral generation, scoring changes, or raw-data writes were performed.

**Checks passed:** 9  
**Checks failed:** 0

## Results

| Check | Status | Details |
| --- | --- | --- |
| Saved assessment integrity | PASS | saved LOW/MEDIUM/HIGH assessments contain required fields |
| Risk invariants | PASS | formula and LOW/MEDIUM/HIGH ranges preserved; saved scores allow 0.01 for two-decimal persistence rounding |
| Deterministic Investigator and fallback | PASS | deterministic Investigator succeeds for all representative rows |
| Mock AI provider boundary | PASS | valid output accepted; invalid, tampered, and disallowed-action outputs fell back |
| FastAPI end-to-end | PASS | health, representative rows, validation errors, 404, fallback, and response allowlist passed |
| Streamlit display path | PASS | dashboard module imports and saved LOW/MEDIUM/HIGH display path is valid |
| Model integrity and explainability | PASS | artifact loaded; 30-feature contract, saved probabilities, and explainability outputs valid |
| Deterministic reproducibility | PASS | two deterministic runs produced equivalent reports |
| Raw CSV hash integrity | PASS | SHA-256 unchanged: 76274b691b16a6c49d3f159c883398e03ccd6d1ee12d9d8ee38f4b4b98551a89 |

## Representative outcomes

| Source row | Existing level | Existing score | Existing ML probability |
| ---: | --- | ---: | ---: |
| 28727 | LOW | 20.95 | 0.01587517 |
| 233005 | MEDIUM | 40.13 | 0.00224222 |
| 215984 | HIGH | 95.00 | 0.99998750 |

## Security and boundary observations

- No real AI API call was made; missing provider configuration used deterministic fallback.
- Mocked valid AI output was accepted only as an explanation; invalid actions and score/level tampering fell back safely.
- FastAPI did not call OpenAI directly; it used `ApplicationInvestigator` and the existing guarded provider path.
- The API response contained no provider key, filesystem path, traceback, raw CSV, or arbitrary provider fields.
- Streamlit was validated through its existing import and saved-assessment rule display path; no dashboard redesign or API dependency was introduced.

## Limitations and bugs

No blocking bugs were found. Observed non-blocking inconsistency: saved risk scores are rounded to two decimals, so formula recomputation can differ by up to 0.01 (for example, 20.95 versus 20.9525102). This validation does not provide authentication, deployment, browser-level Streamlit testing, production behavioral history, or live-provider testing.

## Reproducibility

Deterministic Investigator outputs were equivalent across two runs. Any model probability comparison allows only a small numerical tolerance for floating-point representation.
