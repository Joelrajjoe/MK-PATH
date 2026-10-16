"""Tamper-evident hash-chained lineage graph and signed chain-head checkpoints (Phase 5).

Chaining formula:
  event_hash = SHA256(canonical_event_bytes || previous_event_hash)
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from ..audit import record_audit
from .crypto import Signer, Verifier, key_manager
from .hashing import canonical_json_bytes, hash_bytes
from .models import ChainCheckpoint, LineageEvent, LineageEventType


GENESIS_PREVIOUS_HASH = "0" * 64


class LineageChainError(ValueError):
    """Raised when lineage integrity is broken or a hash mismatch is found."""
    pass


def compute_event_hash(event: LineageEvent, previous_hash: str) -> str:
    """Compute deterministic SHA-256 hash over canonical event fields and previous event hash."""
    d = event.model_dump()
    d["event_hash"] = ""  # Exclude self hash
    canon_bytes = canonical_json_bytes(d)
    bound_payload = canon_bytes + previous_hash.encode("ascii")
    return hash_bytes(bound_payload, "sha256")


class LineageTracker:
    """Manages append-only, tamper-evident lineage event chains and signed checkpoints."""

    def __init__(self, signer: Optional[Signer] = None, verifier: Optional[Verifier] = None):
        self.signer = signer or Signer()
        self.verifier = verifier or Verifier()

    def create_event(
        self,
        *,
        project_id: str,
        run_id: str,
        event_type: LineageEventType,
        sequence_number: int,
        previous_event_hash: Optional[str] = None,
        parent_event_id: Optional[str] = None,
        input_artifacts: Optional[List[Dict[str, str]]] = None,
        output_artifacts: Optional[List[Dict[str, str]]] = None,
        actor: str = "mkpath.system",
        details: Optional[Dict[str, Any]] = None,
    ) -> LineageEvent:
        """Construct, hash-chain, and finalize a LineageEvent."""
        prev_h = previous_event_hash or GENESIS_PREVIOUS_HASH
        event_id = f"evt_{uuid.uuid4().hex[:12]}"
        
        event = LineageEvent(
            event_id=event_id,
            project_id=project_id,
            run_id=run_id,
            sequence_number=sequence_number,
            event_type=event_type,
            parent_event_id=parent_event_id,
            previous_event_hash=prev_h,
            input_artifacts=input_artifacts or [],
            output_artifacts=output_artifacts or [],
            actor=actor,
            details=details or {},
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        event.event_hash = compute_event_hash(event, prev_h)
        return event

    def verify_chain(self, events: List[LineageEvent]) -> Tuple[bool, List[str]]:
        """
        Traverse and verify cryptographic continuity of an event chain:
        1. Sequence numbers must be strictly increasing.
        2. First event must reference GENESIS_PREVIOUS_HASH or recognized checkpoint.
        3. Each event's previous_event_hash must match preceding event's event_hash.
        4. Each event's event_hash must exactly match recomputed hash.
        """
        if not events:
            return True, []

        errors: List[str] = []
        # Sort events by sequence number
        sorted_events = sorted(events, key=lambda e: e.sequence_number)

        for i, ev in enumerate(sorted_events):
            # Check sequence continuity
            if i > 0 and ev.sequence_number != sorted_events[i - 1].sequence_number + 1:
                errors.append(
                    f"Sequence discontinuity: event {ev.event_id} has sequence {ev.sequence_number}, "
                    f"expected {sorted_events[i - 1].sequence_number + 1}."
                )

            # Check previous hash link
            if i == 0:
                expected_prev = GENESIS_PREVIOUS_HASH
            else:
                expected_prev = sorted_events[i - 1].event_hash

            if ev.previous_event_hash != expected_prev:
                errors.append(
                    f"Broken hash chain at event {ev.event_id}: previous_event_hash was {ev.previous_event_hash}, "
                    f"expected {expected_prev}."
                )

            # Recompute event hash
            recalc_hash = compute_event_hash(ev, ev.previous_event_hash)
            if recalc_hash != ev.event_hash:
                errors.append(
                    f"Tampered event content detected at {ev.event_id}: recorded hash {ev.event_hash}, "
                    f"recalculated {recalc_hash}."
                )

        is_valid = (len(errors) == 0)
        return is_valid, errors

    def create_chain_checkpoint(
        self,
        project_id: str,
        chain_id: str,
        events: List[LineageEvent],
        previous_checkpoint_hash: Optional[str] = None,
    ) -> ChainCheckpoint:
        """Issue a digitally signed checkpoint anchor over the current chain head."""
        if not events:
            raise LineageChainError("Cannot checkpoint an empty lineage event chain.")

        is_valid, errors = self.verify_chain(events)
        if not is_valid:
            raise LineageChainError(f"Cannot checkpoint invalid or tampered chain: {errors}")

        sorted_events = sorted(events, key=lambda e: e.sequence_number)
        last_event = sorted_events[-1]
        checkpoint_id = f"chk_{uuid.uuid4().hex[:12]}"
        key_id, key_version, algo, _ = self.signer.manager.get_active_signing_key()

        checkpoint_data = {
            "checkpoint_id": checkpoint_id,
            "project_id": project_id,
            "chain_id": chain_id,
            "sequence_number": last_event.sequence_number,
            "final_event_hash": last_event.event_hash,
            "previous_checkpoint_hash": previous_checkpoint_hash,
            "key_id": key_id,
            "key_version": key_version,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        canon_bytes = canonical_json_bytes(checkpoint_data)
        sig_meta = self.signer.sign_payload(canon_bytes)

        return ChainCheckpoint(
            checkpoint_id=checkpoint_id,
            project_id=project_id,
            chain_id=chain_id,
            sequence_number=last_event.sequence_number,
            final_event_hash=last_event.event_hash,
            previous_checkpoint_hash=previous_checkpoint_hash,
            checkpoint_timestamp=checkpoint_data["timestamp"],
            key_id=key_id,
            key_version=key_version,
            signature=sig_meta.signature,
        )

    def verify_checkpoint(self, checkpoint: ChainCheckpoint) -> Tuple[bool, List[str]]:
        """Verify the digital signature of a chain checkpoint."""
        key_rec = self.verifier.manager.get_public_key(checkpoint.key_id)
        if not key_rec:
            return False, [f"Checkpoint signing key '{checkpoint.key_id}' unknown."]
        if key_rec.state.value == "REVOKED":
            return False, [f"Checkpoint signing key '{checkpoint.key_id}' is revoked."]

        chk_data = {
            "checkpoint_id": checkpoint.checkpoint_id,
            "project_id": checkpoint.project_id,
            "chain_id": checkpoint.chain_id,
            "sequence_number": checkpoint.sequence_number,
            "final_event_hash": checkpoint.final_event_hash,
            "previous_checkpoint_hash": checkpoint.previous_checkpoint_hash,
            "key_id": checkpoint.key_id,
            "key_version": checkpoint.key_version,
            "timestamp": checkpoint.checkpoint_timestamp,
        }
        canon_bytes = canonical_json_bytes(chk_data)
        
        # Verify signature
        try:
            import base64
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.primitives.asymmetric import ed25519
            raw_sig = base64.b64decode(checkpoint.signature)
            pub = serialization.load_pem_public_key(key_rec.public_key_bytes)
            pub.verify(raw_sig, canon_bytes)
            return True, []
        except Exception as exc:
            return False, [f"Checkpoint signature verification failed: {exc}"]


lineage_tracker = LineageTracker()
