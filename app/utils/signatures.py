import hashlib
import hmac


def verify_hmac_signature(raw_body: bytes, secret_key: str, signature_header: str) -> bool:
    """
    Verifies HMAC-SHA256 signature against raw request body using constant-time comparison.
    Header format: "sha256=<hex_digest>" or plain "<hex_digest>"
    """
    if not signature_header or not secret_key:
        return False

    expected_sig = hmac.new(
        secret_key.encode("utf-8"),
        raw_body,
        hashlib.sha256
    ).hexdigest()

    provided_sig = signature_header.strip()
    if provided_sig.startswith("sha256="):
        provided_sig = provided_sig[7:]

    return hmac.compare_digest(expected_sig.lower(), provided_sig.lower())
