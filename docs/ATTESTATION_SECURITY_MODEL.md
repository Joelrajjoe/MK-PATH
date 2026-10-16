# MK-PATH Option C — Attestation Security Model & Threat Assessment

## 1. Threat Model & Adversarial Assumptions

Option C (ARE-HL) was engineered under the assumption of an untrusted or compromised environment where data in transit, data at rest, or database records might be subjected to intentional or accidental tampering:

| Threat Scenario | Attack Vector | Countermeasure in Option C |
| :--- | :--- | :--- |
| **Silent Data Corruption / Disk Bit-Rot** | Raw files or Parquet datasets altered by storage degradation. | Streaming SHA-256 file hashing detects bit changes; verifier flags `HASH_MISMATCH`. |
| **Malicious Model Weight Replacement** | Adversary replaces `model.pkl` with a backdoored pickle file. | `verify_artifact_deployment_readiness` recomputes SHA-256 against manifest; blocks download/deployment (`TAMPERED_BLOCKED`). |
| **History Rewriting / Event Deletion** | Malicious actor modifies an event in the database to hide flawed healing. | Hash-chained lineage `SHA256(canonical(event) \|\| prev_hash)` breaks downstream hashes; verifier flags `LINEAGE_BROKEN`. |
| **Signature Forgery** | Attacker attempts to forge envelope signature without private key. | Asymmetric Ed25519 / RSA-PSS cryptographic validation; fails with `INVALID_SIGNATURE`. |
| **Compromised Key Abuse** | A stolen signing key is used to sign fraudulent attestations. | Key revocation registry marks key as `REVOKED`; verifications fail closed with `REVOKED_KEY`. |
| **Verification Gate Bypass** | Actor attempts to deploy model despite critical leakage gate failure. | Fail-closed gate enforcement: `attestation_status` marked `BLOCKED`, deployment readiness marked `BLOCKED`, API blocks download. |
| **Replay Attacks** | Attacker substitutes old envelope into a new project run. | Envelope payload strictly binds `project_id`, `run_id`, `created_at`, and source file hashes. |

---

## 2. Fail-Closed Security Design

Option C operates under a strict **fail-closed** architecture:
1. **Unknown Key**: If an envelope was signed by a key ID not present in the public key registry, verification immediately terminates with `UNKNOWN_KEY`.
2. **Revoked Key**: If an envelope was signed by a revoked key, verification fails with `REVOKED_KEY` and human review is required.
3. **Missing Files**: If physical dataset files or artifacts referenced in an envelope are missing from storage, verification fails with `MISSING_CONTENT`.
4. **Mandatory Gate Failure**: If any critical or high-severity gate (e.g. `data_quality_gate`, `data_leakage_gate`, or PMSG stability) fails, the envelope attestation is permanently sealed as `BLOCKED`.
5. **Atlas Durability Enforcement**: When `require_atlas=True`, if MongoDB Atlas is unavailable or degraded, envelope creation does NOT fall back to local in-memory/JSON storage; it raises `AtlasPersistenceError` and fails closed.

---

## 3. Cryptographic Primitives

- **Digital Signatures**:
  - Primary: **Ed25519** (RFC 8032) providing 128-bit security level, fast verification, and constant-time execution resistant to side-channel timing attacks.
  - Secondary/Enterprise: **RSA-PSS** (2048-bit minimum key size) with SHA-256 digest and MGF1 masking (RFC 8017 / PKCS#1 v2.1).
- **Hashing**:
  - NIST-approved **SHA-256** (FIPS PUB 180-4) computed over chunked 64 KB streaming buffers for file assets and UTF-8 byte streams for canonical JSON objects.
- **Canonicalization**:
  - IETF **RFC 8785** (JSON Canonicalization Scheme) ensuring byte-level invariance across implementations.
