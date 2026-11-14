import hashlib
import hmac
import os


def hash_password(pw: str) -> str:
    salt = os.urandom(16)
    key = hashlib.scrypt(pw.encode(), salt=salt, n=2**14, r=8, p=1, dklen=64)
    return salt.hex() + ":" + key.hex()


def check_password(pw: str, stored: str) -> bool:
    salt, key = stored.split(":")
    got = hashlib.scrypt(pw.encode(), salt=bytes.fromhex(salt), n=2**14, r=8, p=1, dklen=64)
    return hmac.compare_digest(got, bytes.fromhex(key))


def sha(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def client_ip(request) -> str:
    """The caller's address. Behind Vercel's proxy the real address is the first entry of X-Forwarded-For; elsewhere that header is not trusted."""
    from . import config
    if config.ON_VERCEL:
        first = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        if first:
            return first
    return request.client.host if request.client else ""
