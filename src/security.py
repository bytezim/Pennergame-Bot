"""
Security utilities for password hashing and cookie management.

Features:
- Password hashing for local bot access (PasswordHasher)
- AES-256 encryption for stored credentials (CredentialEncryption)
- Cookie sanitization
"""

import hashlib
import hmac
import secrets
import base64
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class PasswordHasher:
    """
    Password hashing utility using PBKDF2-SHA256.

    Note: This is a basic implementation. For production, use:
    - argon2-cffi (recommended)
    - bcrypt
    - passlib
    """

    ITERATIONS = 100000
    HASH_NAME = "sha256"

    @staticmethod
    def hash_password(password: str, salt: Optional[bytes] = None) -> str:
        """
        Hash password with PBKDF2-SHA256.

        Args:
            password: Plain text password
            salt: Optional salt (generated if not provided)

        Returns:
            Hashed password in format: salt$hash
        """
        if salt is None:
            salt = secrets.token_bytes(32)

        pwd_hash = hashlib.pbkdf2_hmac(
            PasswordHasher.HASH_NAME,
            password.encode("utf-8"),
            salt,
            PasswordHasher.ITERATIONS,
        )

        # Store as: salt$hash (both hex-encoded)
        return f"{salt.hex()}${pwd_hash.hex()}"

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """
        Verify password against hash.

        Args:
            password: Plain text password
            hashed: Hashed password (salt$hash format)

        Returns:
            True if password matches
        """
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

            # Constant-time comparison
            return hmac.compare_digest(pwd_hash, stored_hash)
        except (ValueError, AttributeError):
            return False


class CredentialEncryption:
    """
    AES-256 encryption for sensitive credentials.
    
    Uses Fernet (symmetric encryption) with a key derived from machine-specific data.
    This prevents plaintext storage while allowing decryption for auto-login.
    
    Note: This is obfuscation, not protection against determined attackers with
    filesystem access. For true security, use OS keyring or hardware tokens.
    """
    
    @staticmethod
    def _get_encryption_key() -> bytes:
        """
        Generate encryption key from machine-specific data.
        Same machine = same key = can decrypt credentials.
        """
        import platform
        import os
        import getpass

        # Determine current user in a container-safe way
        try:
            user = getpass.getuser()
        except Exception:
            user = os.environ.get("USER") or os.environ.get("USERNAME") or "unknown"

        # Combine machine-specific identifiers
        machine_id = f"{platform.node()}-{platform.machine()}-{user}"
        
        # Derive key using PBKDF2HMAC
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"pennerbot-v1",  # Static salt (acceptable for machine-bound encryption)
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(machine_id.encode()))
        return key
    
    @staticmethod
    def encrypt(plaintext: str) -> str:
        """
        Encrypt plaintext string.
        
        Args:
            plaintext: String to encrypt
            
        Returns:
            Encrypted string (base64-encoded)
        """
        try:
            key = CredentialEncryption._get_encryption_key()
            f = Fernet(key)
            encrypted = f.encrypt(plaintext.encode())
            return encrypted.decode()
        except Exception as e:
            raise ValueError(f"Encryption failed: {e}")
    
    @staticmethod
    def decrypt(encrypted: str) -> str:
        """
        Decrypt encrypted string.
        
        Args:
            encrypted: Encrypted string (base64-encoded)
            
        Returns:
            Decrypted plaintext
        """
        try:
            key = CredentialEncryption._get_encryption_key()
            f = Fernet(key)
            decrypted = f.decrypt(encrypted.encode())
            return decrypted.decode()
        except Exception as e:
            raise ValueError(f"Decryption failed: {e}")


def sanitize_cookie_value(value: str) -> str:
    """
    Sanitize cookie value to prevent injection.

    Args:
        value: Cookie value

    Returns:
        Sanitized value
    """
    # Remove potentially dangerous characters
    dangerous_chars = [";", "\n", "\r", "\0"]
    for char in dangerous_chars:
        value = value.replace(char, "")

    return value.strip()
