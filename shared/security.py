"""Packet signing shared by the edge node and the cloud. One key per centre, derived from a master secret.

DEMO: the master secret is read from the environment. In a real roll-out each centre gets its own key
at install time and the cloud keeps only a key store, never the master.
"""
import hashlib, hmac, json, os

def master() -> bytes:
    return os.environ.get("KD_MASTER_SECRET", "demo-master-change-me").encode()

def centre_key(centre_code: str) -> bytes:
    return hmac.new(master(), b"centre:" + centre_code.encode(), hashlib.sha256).digest()

def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))

def sign_body(centre_code: str, body: dict, prev_sig: str) -> str:
    return hmac.new(centre_key(centre_code), (prev_sig + canonical(body)).encode(), hashlib.sha256).hexdigest()

def seal(centre_code: str, body: dict, prev_sig: str) -> dict:
    """Return the packet to send: body + prev_sig + sig."""
    return {**body, "prev_sig": prev_sig, "sig": sign_body(centre_code, body, prev_sig)}

def verify(packet: dict) -> bool:
    try:
        body = {k: v for k, v in packet.items() if k not in ("prev_sig", "sig")}
        expected = sign_body(packet["centre_code"], body, packet["prev_sig"])
        return hmac.compare_digest(expected, packet["sig"])
    except (KeyError, TypeError):
        return False
