from hashlib import sha256
from hmac import compare_digest


def hash_password(password: str) -> str:
    return sha256(password.encode("utf-8")).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    return compare_digest(hash_password(password), password_hash or "")
