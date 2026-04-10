import hashlib
import hmac
import secrets
import base64
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class PasswordHasher:
    ITERATIONS = 100000
    HASH_NAME = "sha256"

    @staticmethod
    def hash_password(password: str, salt: Optional[bytes] = None) -> str:
        if salt is None:
            salt = secrets.token_bytes(32)
        pwd_hash = hashlib.pbkdf2_hmac(
            PasswordHasher.HASH_NAME,
            password.encode("utf-8"),
            salt,
            PasswordHasher.ITERATIONS,
        )
        return f"{salt.hex()}${pwd_hash.hex()}"

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        try:
            salt_hex, hash_hex = hashed.split("$")
            salt = bytes.fromhex(salt_hex)
            stored_hash = bytes.fromhex(hash_hex)
            pwd_hash = hashlib.pbkdf2_hmac(
                PasswordHasher.HASH_NAME,
                password.encode("utf-8"),
                salt,
                PasswordHasher.ITERATIONS,
            )
            return hmac.compare_digest(pwd_hash, stored_hash)
        except (ValueError, AttributeError):
            return False


class CredentialEncryption:
    @staticmethod
    def _get_encryption_key() -> bytes:
        import platform
        import os
        import getpass

        try:
            user = getpass.getuser()
        except Exception:
            user = os.environ.get("USER") or os.environ.get("USERNAME") or "unknown"
        machine_id = f"{platform.node()}-{platform.machine()}-{user}"
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"pennerbot-v1",
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(machine_id.encode()))
        return key

    @staticmethod
    def encrypt(plaintext: str) -> str:
        try:
            key = CredentialEncryption._get_encryption_key()
            f = Fernet(key)
            encrypted = f.encrypt(plaintext.encode())
            return encrypted.decode()
        except Exception as e:
            raise ValueError(f"Encryption failed: {e}")

    @staticmethod
    def decrypt(encrypted: str) -> str:
        try:
            key = CredentialEncryption._get_encryption_key()
            f = Fernet(key)
            decrypted = f.decrypt(encrypted.encode())
            return decrypted.decode()
        except Exception as e:
            raise ValueError(f"Decryption failed: {e}")


def sanitize_cookie_value(value: str) -> str:
    dangerous_chars = [";", "\n", "\r", "\x00"]
    for char in dangerous_chars:
        value = value.replace(char, "")
    return value.strip()
