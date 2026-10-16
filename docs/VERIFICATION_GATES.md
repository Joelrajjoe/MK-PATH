# MK-Path Verification Gates Architecture
## Verification Contracts, Gate Hierarchy, and Deployment Blocking

This document defines the verification gate contracts, evaluation algorithms, and containment mechanisms implemented across the MK-Path platform.

---

## 1. Overview and Core Philosophy

In MK-Path, **unverified data or unverified models must never be promoted to a trusted state or deployed**. Verification is not an advisory badge; it is a cryptographic, state-enforced gate that determines whether downstream pipeline execution, reporting, and deployment artifact packaging are permitted to proceed.

```
Incoming Dataset / Agent Action
              │
              ▼
    [Gate 1: Schema & Type Gate]
              │ (PASS)
              ▼
   [Gate 2: Null & Integrity Gate]
              │ (PASS)
              ▼
   [Gate 3: Value & Domain Range Gate]
              │ (PASS)
              ▼
   [Gate 4: Statistical & Multiverse Stability (PMSG)]
              │ (PASS)
              ▼
   [Gate 5: Information Governance & Tenant Isolation]
              │ (PASS)
              ▼
   [Gate 6: Evidence & Provenance Linkage Gate]
              │
    ┌─────────┴─────────┐
    ▼                   ▼
 [PASS]              [FAIL]
    │                   │
    ▼                   ▼
[Generate Deployment] [HALT & CONTAIN]
- deployment_manifest - Block downstream pipeline
- model_api.py        - Withhold deployment artifacts
- production weights  - Log audit incident to Atlas
```

---

## 2. Gate Specifications & Contracts

### Gate 1: Schema & Dtype Verification (`VG_SCHEMA`)
- **Target File**: `backend/app/verification/engine.py`
- **Contract**: Ensures all required business columns exist and adhere to declared physical types.
- **Rules**:
  - Mandatory columns `['record_id', 'group_id', 'numerator_val', 'denominator_val', 'metric_value']` must be present.
  - Numeric columns must be float or integer types, never coerced from raw strings or malformed objects.
- **Failure Severity**: `HIGH`
- **FIB-VG Coverage**: `FIB-DAT-001`, `FIB-DAT-002`, `FIB-DAT-005`.

### Gate 2: Null & Completeness Gate (`VG_NULL_KEY`)
- **Target File**: `backend/app/verification/engine.py`
- **Contract**: Ensures mandatory business keys and critical analytical fields have 0% nullity.
- **Rules**:
  - `record_id.isnull().sum() == 0`
  - Overall record nullity must not exceed configured threshold ($< 5\%$).
- **Failure Severity**: `HIGH`
- **FIB-VG Coverage**: `FIB-DAT-003`.

### Gate 3: Data Loss & Row Cardinality Gate (`VG_ROW_COUNT`)
- **Target File**: `backend/app/verification/engine.py`
- **Contract**: Verifies that transformations do not silently drop, truncate, or duplicate records without provenance flags.
- **Rules**:
  - Row drop rate must equal $0.0\%$. Slicing or dropping $30\%$ of records triggers an immediate critical failure.
- **Failure Severity**: `CRITICAL`
- **FIB-VG Coverage**: `FIB-DAT-004`.

### Gate 4: Plan-Multiverse Stability Gate (PMSG) (`VG_MULTIVERSE_STABILITY`)
- **Target File**: `backend/app/analytics/pmsg.py`
- **Contract**: Evaluates whether analytical metrics remain robust across alternative modeling, filtering, and imputation choices.
- **Rules**:
  - Coefficient of Variation ($CV$) across multiverse simulation branches must satisfy $CV \le 0.15$.
  - Directional stability must satisfy concordance $\ge 90\%$.
- **Failure Severity**: `HIGH`
- **FIB-VG Coverage**: `FIB-ANA-003`.

### Gate 5: Ratio & Denominator Distortion Gate (`VG_RATIO_CALC`)
- **Target File**: `backend/app/verification/engine.py`
- **Contract**: Protects against altered or zero denominators in key analytical ratios.
- **Rules**:
  - Explicit recalculated check: $|(\text{numerator} / \text{denominator}) - \text{observed\_metric}| < 10^{-6}$.
- **Failure Severity**: `CRITICAL`
- **FIB-VG Coverage**: `FIB-ANA-001`.

### Gate 6: Information Governance & Tenant Isolation Gate (`VG_GOVERNANCE`)
- **Target File**: `backend/app/verification/engine.py`
- **Contract**: Enforces strict tenant boundaries and column classification access policies.
- **Rules**:
  - Columns classified as PII (`SSN`, `CREDIT_CARD`, `PASSWORD`) are strictly barred from analytical output.
  - Cross-tenant dataset references (`proj_beta_foreign_tenant` requested by `proj_alpha`) are rejected with `HTTP 403 Forbidden`.
- **Failure Severity**: `CRITICAL`
- **FIB-VG Coverage**: `FIB-SEM-001`, `FIB-SEM-003`.

### Gate 7: Verifier Anti-Tamper & Aggregation Gate (`VG_ANTI_TAMPER`)
- **Target File**: `backend/app/verification/engine.py`
- **Contract**: Prevents downstream aggregators from masking gate failures or converting a `FAIL` to `PASS`.
- **Rules**:
  - Overall status is an irreversible logical conjunction: $\text{Overall} = \bigwedge_{i} \text{Gate}_i$.
  - Any single critical failure forces `Overall = FAIL`.
- **Failure Severity**: `CRITICAL`
- **FIB-VG Coverage**: `FIB-BYP-001`, `FIB-BYP-002`, `FIB-BYP-003`.

---

## 3. Deployment-Blocking Containment Mechanism

The deployment gate acts as the hard barrier preventing unverified models from entering production:

```python
# Real code implementation in backend/app/engineering/ml_engineer.py
def generate_deployment_artifacts(project_id: str, verification_result: Dict[str, Any]) -> Dict[str, Any]:
    gate_status = verification_result.get("overall_status", "FAIL")
    if gate_status != "PASS":
        # Containment action: Deployment blocked
        return {
            "deployment_permitted": False,
            "blocked": True,
            "reason": f"Verification gate status is {gate_status}; critical failures present.",
            "artifacts_generated": []
        }
    
    # Safe to generate artifacts
    ...
```

### Proved in Regression Tests:
`test_critical_failure_blocks_ml_deployment_artifacts` in `backend/tests/test_fib_vg.py` verifies that when an injected fault causes `VG_ROW_COUNT` or `VG_SCHEMA` to fail:
1. `deployment_permitted` is evaluated to `False`.
2. `blocked` is evaluated to `True`.
3. Zero files (`deployment_manifest.json`, `model_api.py`) are created in the project's artifact directory.

---

## 4. Cryptographic Attestation & Artifact Integrity Gate (Option C ARE-HL)

Option C introduces Gate 8: **Cryptographic Attestation & Artifact Integrity Verification**:
- **Target Files**: `backend/app/attestation/service.py`, `backend/app/engineering/ml_engineer.py`
- **Contract**:
  1. No analytical result may receive an active `SIGNED` attestation envelope if any mandatory or critical verification gate evaluated to `FAIL`. If a critical failure is detected, the envelope is permanently sealed with `attestation_status: "BLOCKED"`.
  2. Artifact downloads and container deployments are gated by `verify_artifact_deployment_readiness`. All files (`model.pkl`, `api/main.py`, `api/schema.py`, `README.md`) must strictly match the streaming SHA-256 hashes recorded in `metadata.json` and attested in the `ArtifactProvenance` block of the envelope.
  3. Any physical byte tampering or corruption on disk transitions the artifact status to `TAMPERED_BLOCKED` and revokes download/deployment authorization.
