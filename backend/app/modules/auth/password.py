import hashlib
import hmac
import secrets


def hash_password(password: str) -> str:
    """将密码转换成加盐哈希，用于数据库保存。"""
    salt = secrets.token_bytes(16)

    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=16384,
        r=8,
        p=1,
        dklen=32,
    )

    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """校验输入密码是否匹配数据库中的哈希。"""
    try:
        algorithm, salt_hex, digest_hex = stored_hash.split("$")
        if algorithm != "scrypt":
            return False

        digest = hashlib.scrypt(
            password.encode("utf-8"),
            salt=bytes.fromhex(salt_hex),
            n=16384,
            r=8,
            p=1,
            dklen=32,
        )

        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False