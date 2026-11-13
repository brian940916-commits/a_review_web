"""密碼雜湊的小工具；帳號密碼不以明文存進資料庫。"""
import hashlib
import hmac
import secrets


def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 600000)
    return salt + ":" + digest.hex()


def check_password(password, stored):
    salt, expected = stored.split(":")
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 600000)
    return hmac.compare_digest(digest.hex(), expected)
