import json
import hmac
import hashlib

# Sovereign Key (In production, this sits in a secure Hardware Security Module)
EDGE_SECRET_KEY = b"kushaldrishti-msde-edge-key-2026"

def sign_payload(body: dict, prev_sig: str = "GENESIS") -> str:
    """Generates a tamper-proof HMAC-SHA256 signature for the telemetry packet."""
    payload_str = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return hmac.new(EDGE_SECRET_KEY, (prev_sig + payload_str).encode(), hashlib.sha256).hexdigest()

def verify_signature(packet: dict) -> bool:
    """Verifies that the packet was not altered by a corrupt centre manager during transit."""
    provided_sig = packet.get("sig")
    prev_sig = packet.get("prev_sig", "GENESIS")
    
    # Reconstruct the body without the signatures
    body = {k: v for k, v in packet.items() if k not in ("sig", "prev_sig")}
    expected_sig = sign_payload(body, prev_sig)
    
    return hmac.compare_digest(provided_sig, expected_sig)