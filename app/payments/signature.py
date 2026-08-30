import hashlib
import hmac


def compute_signature(payload_bytes, secret):
    return hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()


def verify_signature(payload_bytes, signature, secret):
    if not signature:
        return False
    expected = compute_signature(payload_bytes, secret)
    return hmac.compare_digest(expected, signature)
