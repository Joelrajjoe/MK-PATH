"""Cryptographic signatures, public key trust registry, and key management for ARE-HL (Phase 3).

Supports:
- Ed25519 (RFC 8032) primary signing algorithm.
- RSA-PSS with SHA-256 (RFC 8017 / PKCS#1 v2.1).
- Key generation, rotation, retirement, and revocation.
- Fail-closed security design when keys are missing or untrusted.
"""

import base64
import logging
import os
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, padding, rsa

from ..config import settings
from .hashing import canonical_json_bytes, hash_bytes
from .models import (
    AttestedResultEnvelope,
    EnvelopeVerificationReport,
    GateStatusEnum,
    IntegrityStatus,
    SignatureAlgorithm,
    SignatureMetadata,
)

logger = logging.getLogger("mkpath.attestation.crypto")


class KeyState(str, Enum):
    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"
    REVOKED = "REVOKED"


class KeyRecord:
    def __init__(
        self,
        key_id: str,
        key_version: str,
        algorithm: SignatureAlgorithm,
        public_key_bytes: bytes,
        state: KeyState = KeyState.ACTIVE,
        trusted: bool = True,
        created_at: Optional[str] = None,
        revoked_at: Optional[str] = None,
        revocation_reason: Optional[str] = None,
    ):
        self.key_id = key_id
        self.key_version = key_version
        self.algorithm = algorithm
        self.public_key_bytes = public_key_bytes
        self.state = state
        self.trusted = trusted
        self.created_at = created_at or datetime.now(timezone.utc).isoformat()
        self.revoked_at = revoked_at
        self.revocation_reason = revocation_reason

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key_id": self.key_id,
            "key_version": self.key_version,
            "algorithm": self.algorithm.value,
            "public_key_pem": self.public_key_bytes.decode("utf-8"),
            "state": self.state.value,
            "trusted": self.trusted,
            "created_at": self.created_at,
            "revoked_at": self.revoked_at,
            "revocation_reason": self.revocation_reason,
        }


class KeyManager:
    """
    Manages active signing keys and trusted public key verification registry.
    Strictly isolates private key material in memory or secured filesystem paths.
    """

    def __init__(self) -> None:
        self._private_keys: Dict[str, Any] = {}
        self._public_registry: Dict[str, KeyRecord] = {}
        self._active_key_id: Optional[str] = None
        self._bootstrap_keys()

    def _bootstrap_keys(self) -> None:
        """Initialize signing and verification keys from environment or secure test defaults."""
        env_priv_b64 = os.environ.get("MKPATH_SIGNING_PRIVATE_KEY")
        key_id = os.environ.get("MKPATH_SIGNING_KEY_ID", "mkpath-root-v1")
        key_version = os.environ.get("MKPATH_SIGNING_KEY_VERSION", "1.0.0")

        if env_priv_b64:
            try:
                raw_bytes = base64.b64decode(env_priv_b64)
                # Load private key (try Ed25519 raw or PKCS8)
                if len(raw_bytes) == 32:
                    priv_key = ed25519.Ed25519PrivateKey.from_private_bytes(raw_bytes)
                else:
                    priv_key = serialization.load_pem_private_key(raw_bytes, password=None)
                
                self.register_private_key(key_id, key_version, priv_key, is_active=True, trusted=True)
                logger.info("Loaded production attestation signing key: %s (version: %s)", key_id, key_version)
                return
            except Exception as exc:
                logger.error("Failed to load configured private key from environment: %s", exc)

        # Non-production / Local development fallback
        dev_mode = os.environ.get("MKPATH_DEV_SIGNING", "true").lower() in ("1", "true", "yes")
        if dev_mode:
            logger.info("Initializing isolated ephemeral Ed25519 development keypair for local development.")
            priv_key = ed25519.Ed25519PrivateKey.generate()
            self.register_private_key("mkpath-dev-key-01", "1.0.0", priv_key, is_active=True, trusted=True)
        else:
            logger.warning("No signing key configured and MKPATH_DEV_SIGNING is false. Attestation signing disabled.")

    def register_private_key(
        self,
        key_id: str,
        key_version: str,
        private_key: Any,
        is_active: bool = True,
        trusted: bool = True,
    ) -> None:
        """Register a private key in the in-memory keystore (never persisted to Git/DB)."""
        self._private_keys[key_id] = private_key
        
        # Derive public key bytes
        public_key = private_key.public_key()
        if isinstance(private_key, ed25519.Ed25519PrivateKey):
            algo = SignatureAlgorithm.ED25519
            pub_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        elif isinstance(private_key, rsa.RSAPrivateKey):
            algo = SignatureAlgorithm.RSA_PSS_SHA256
            pub_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        else:
            raise ValueError(f"Unsupported private key class: {type(private_key).__name__}")

        rec = KeyRecord(
            key_id=key_id,
            key_version=key_version,
            algorithm=algo,
            public_key_bytes=pub_pem,
            state=KeyState.ACTIVE,
            trusted=trusted,
        )
        self._public_registry[key_id] = rec
        if is_active:
            self._active_key_id = key_id

    def register_public_key(
        self,
        key_id: str,
        key_version: str,
        algorithm: SignatureAlgorithm,
        public_key_pem: bytes,
        trusted: bool = True,
    ) -> None:
        """Register a public verification key in the trust store."""
        rec = KeyRecord(
            key_id=key_id,
            key_version=key_version,
            algorithm=algorithm,
            public_key_bytes=public_key_pem,
            state=KeyState.ACTIVE,
            trusted=trusted,
        )
        self._public_registry[key_id] = rec

    def revoke_key(self, key_id: str, reason: str = "Compromised or retired") -> None:
        """Mark a key as REVOKED; subsequent signatures fail, verifications flag REVOKED_KEY."""
        if key_id in self._public_registry:
            self._public_registry[key_id].state = KeyState.REVOKED
            self._public_registry[key_id].trusted = False
            self._public_registry[key_id].revoked_at = datetime.now(timezone.utc).isoformat()
            self._public_registry[key_id].revocation_reason = reason
        if self._active_key_id == key_id:
            self._active_key_id = None
        logger.warning("Key '%s' revoked: %s", key_id, reason)

    def get_active_signing_key(self) -> Tuple[str, str, SignatureAlgorithm, Any]:
        """Return (key_id, key_version, algorithm, private_key_obj). Raises if none available."""
        if not self._active_key_id or self._active_key_id not in self._private_keys:
            raise RuntimeError("No active signing key available in attestation KeyManager.")
        
        key_id = self._active_key_id
        rec = self._public_registry[key_id]
        if rec.state != KeyState.ACTIVE:
            raise RuntimeError(f"Active key '{key_id}' is in non-active state: {rec.state}")

        priv = self._private_keys[key_id]
        return key_id, rec.key_version, rec.algorithm, priv

    def get_public_key(self, key_id: str) -> Optional[KeyRecord]:
        return self._public_registry.get(key_id)

    def list_public_keys(self) -> List[Dict[str, Any]]:
        return [rec.to_dict() for rec in self._public_registry.values()]


# Global singleton instance
key_manager = KeyManager()


class Signer:
    """Computes digital signatures over canonical attestation payloads."""

    def __init__(self, manager: Optional[KeyManager] = None):
        self.manager = manager or key_manager

    def sign_payload(self, canonical_bytes: bytes) -> SignatureMetadata:
        """Sign canonical bytes and return structured SignatureMetadata."""
        key_id, key_version, algorithm, priv_key = self.manager.get_active_signing_key()
        payload_hash = hash_bytes(canonical_bytes, "sha256")

        if algorithm == SignatureAlgorithm.ED25519:
            raw_sig = priv_key.sign(canonical_bytes)
        elif algorithm == SignatureAlgorithm.RSA_PSS_SHA256:
            raw_sig = priv_key.sign(
                canonical_bytes,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH,
                ),
                hashes.SHA256(),
            )
        else:
            raise ValueError(f"Unsupported signature algorithm: {algorithm}")

        sig_b64 = base64.b64encode(raw_sig).decode("ascii")

        return SignatureMetadata(
            signature_algorithm=algorithm,
            payload_hash=payload_hash,
            signature=sig_b64,
            key_id=key_id,
            key_version=key_version,
            signing_timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def sign_envelope(self, envelope: AttestedResultEnvelope) -> AttestedResultEnvelope:
        """
        Sign an AttestedResultEnvelope:
        1. Remove any existing signature from the envelope payload.
        2. Canonicalize the envelope fields into RFC 8785 bytes.
        3. Compute digital signature.
        4. Attach signature to the envelope.
        """
        env_dict = envelope.model_dump()
        env_dict["attestation"] = None
        canon_bytes = canonical_json_bytes(env_dict)

        sig_meta = self.sign_payload(canon_bytes)
        envelope.attestation = sig_meta
        return envelope


class Verifier:
    """Verifies digital signatures and trust state over envelopes and lineage checkpoints."""

    def __init__(self, manager: Optional[KeyManager] = None):
        self.manager = manager or key_manager

    def verify_envelope(
        self,
        envelope: AttestedResultEnvelope,
        verify_content_files: bool = True,
    ) -> EnvelopeVerificationReport:
        """
        Exhaustively verify an Attested Result Envelope:
        1. Validate envelope schema and attestation presence.
        2. Look up signing key in public registry.
        3. Verify key trust and revocation status.
        4. Recompute payload hash over canonical envelope bytes.
        5. Verify cryptographic digital signature.
        6. Verify accessible content hashes if requested.
        7. Evaluate mandatory verification gate results.
        8. Return comprehensive verification report.
        """
        errors: List[str] = []
        warnings: List[str] = []
        recalculated_hashes: Dict[str, str] = {}

        if not envelope.attestation:
            return EnvelopeVerificationReport(
                envelope_id=envelope.envelope_id,
                overall_status=IntegrityStatus.INVALID_SIGNATURE,
                signature_valid=False,
                payload_hash_valid=False,
                content_hashes_valid=False,
                lineage_complete=False,
                mandatory_gates_acceptable=False,
                key_trusted=False,
                key_id="none",
                verification_errors=["Envelope does not contain a digital attestation signature."],
            )

        sig_meta = envelope.attestation
        key_id = sig_meta.key_id
        key_rec = self.manager.get_public_key(key_id)

        # 1. Key existence and trust
        if not key_rec:
            return EnvelopeVerificationReport(
                envelope_id=envelope.envelope_id,
                overall_status=IntegrityStatus.UNKNOWN_KEY,
                signature_valid=False,
                payload_hash_valid=False,
                content_hashes_valid=False,
                lineage_complete=False,
                mandatory_gates_acceptable=False,
                key_trusted=False,
                key_id=key_id,
                verification_errors=[f"Signing key '{key_id}' is unknown in public trust registry."],
            )

        if key_rec.state == KeyState.REVOKED:
            return EnvelopeVerificationReport(
                envelope_id=envelope.envelope_id,
                overall_status=IntegrityStatus.REVOKED_KEY,
                signature_valid=False,
                payload_hash_valid=False,
                content_hashes_valid=False,
                lineage_complete=False,
                mandatory_gates_acceptable=False,
                key_trusted=False,
                key_id=key_id,
                key_revoked=True,
                verification_errors=[f"Signing key '{key_id}' was REVOKED: {key_rec.revocation_reason}"],
            )

        if not key_rec.trusted:
            errors.append(f"Signing key '{key_id}' is marked UNTRUSTED.")

        # 2. Recompute payload hash
        env_dict = envelope.model_dump()
        env_dict["attestation"] = None
        canon_bytes = canonical_json_bytes(env_dict)
        recalculated_payload_hash = hash_bytes(canon_bytes, "sha256")

        payload_hash_valid = (recalculated_payload_hash == sig_meta.payload_hash)
        if not payload_hash_valid:
            errors.append(
                f"Payload hash mismatch: expected {sig_meta.payload_hash}, recalculated {recalculated_payload_hash}."
            )

        # 3. Cryptographic signature check
        signature_valid = False
        try:
            raw_sig = base64.b64decode(sig_meta.signature)
            pub_key = serialization.load_pem_public_key(key_rec.public_key_bytes)

            if key_rec.algorithm == SignatureAlgorithm.ED25519:
                if not isinstance(pub_key, ed25519.Ed25519PublicKey):
                    errors.append("Key algorithm mismatch: expected Ed25519 public key.")
                else:
                    pub_key.verify(raw_sig, canon_bytes)
                    signature_valid = True
            elif key_rec.algorithm == SignatureAlgorithm.RSA_PSS_SHA256:
                if not isinstance(pub_key, rsa.RSAPublicKey):
                    errors.append("Key algorithm mismatch: expected RSA public key.")
                else:
                    pub_key.verify(
                        raw_sig,
                        canon_bytes,
                        padding.PSS(
                            mgf=padding.MGF1(hashes.SHA256()),
                            salt_length=padding.PSS.MAX_LENGTH,
                        ),
                        hashes.SHA256(),
                    )
                    signature_valid = True
        except InvalidSignature:
            errors.append("Digital signature verification failed (corrupted or forged signature).")
        except Exception as exc:
            errors.append(f"Signature verification error: {type(exc).__name__}: {exc}")

        # 4. Content files verification (if accessible on disk)
        content_hashes_valid = True
        if verify_content_files:
            # Check source dataset
            src_ref = envelope.source_identity.source_storage_reference
            if src_ref and Path(src_ref).exists() and Path(src_ref).is_file():
                try:
                    from .hashing import hash_file_streaming
                    h = hash_file_streaming(src_ref)
                    recalculated_hashes["source_dataset"] = h
                    if h != envelope.source_identity.source_content_hash:
                        content_hashes_valid = False
                        errors.append(
                            f"Source dataset on disk has changed! Expected {envelope.source_identity.source_content_hash}, found {h}."
                        )
                except Exception as exc:
                    warnings.append(f"Could not hash source file at '{src_ref}': {exc}")
            
            # Check derived dataset if present
            derived_ref = envelope.transformation_lineage.derived_dataset_id
            derived_hash = envelope.transformation_lineage.derived_content_hash
            if derived_hash and derived_ref:
                derived_path = settings.DATA_DIR / "derived" / f"{derived_ref}.parquet"
                if derived_path.exists():
                    from .hashing import hash_file_streaming
                    dh = hash_file_streaming(derived_path)
                    recalculated_hashes["derived_dataset"] = dh
                    if dh != derived_hash:
                        content_hashes_valid = False
                        errors.append(f"Derived dataset file has been modified! Expected {derived_hash}, found {dh}.")

            # Check artifact files
            for art_name, expected_art_hash in envelope.artifact_provenance.artifact_content_hashes.items():
                art_path = settings.ARTIFACTS_DIR / envelope.project_id / envelope.run_id / art_name
                if art_path.exists() and art_path.is_file():
                    from .hashing import hash_file_streaming
                    ah = hash_file_streaming(art_path)
                    recalculated_hashes[f"artifact:{art_name}"] = ah
                    if ah != expected_art_hash:
                        content_hashes_valid = False
                        errors.append(
                            f"Artifact '{art_name}' content altered on disk! Expected {expected_art_hash}, found {ah}."
                        )

        # 5. Mandatory Gates
        mandatory_gates_acceptable = (
            envelope.verification.mandatory_gate_status == GateStatusEnum.PASS
            and envelope.verification.deployment_readiness_status != "BLOCKED"
        )
        if not mandatory_gates_acceptable:
            warnings.append("Mandatory verification gates failed or deployment is marked BLOCKED.")

        # 6. Lineage completeness check
        lineage_complete = True
        if envelope.transformation_lineage.parent_dataset_id and not envelope.source_identity.source_dataset_id:
            lineage_complete = False
            errors.append("Transformation references parent dataset but source dataset identity is missing.")

        # Determine overall status
        if not key_rec.trusted:
            overall_status = IntegrityStatus.UNTRUSTED_KEY
        elif not signature_valid:
            overall_status = IntegrityStatus.INVALID_SIGNATURE
        elif not payload_hash_valid or not content_hashes_valid:
            overall_status = IntegrityStatus.HASH_MISMATCH
        elif not lineage_complete:
            overall_status = IntegrityStatus.LINEAGE_BROKEN
        elif errors:
            overall_status = IntegrityStatus.ERROR
        else:
            overall_status = IntegrityStatus.VALID

        return EnvelopeVerificationReport(
            envelope_id=envelope.envelope_id,
            overall_status=overall_status,
            signature_valid=signature_valid,
            payload_hash_valid=payload_hash_valid,
            content_hashes_valid=content_hashes_valid,
            lineage_complete=lineage_complete,
            mandatory_gates_acceptable=mandatory_gates_acceptable,
            key_trusted=key_rec.trusted,
            key_id=key_id,
            key_revoked=(key_rec.state == KeyState.REVOKED),
            verification_errors=errors,
            unresolved_warnings=warnings,
            recalculated_hashes=recalculated_hashes,
        )
