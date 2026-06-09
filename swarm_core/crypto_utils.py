import base64
import os
from typing import Dict, Any, List
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Default salt for demonstration purposes; in production, this should be unique per task
DEFAULT_SALT = b"\x00" * 16

def derive_key(passphrase: str, salt: bytes = DEFAULT_SALT) -> str:
    """
    Derives a cryptographically secure 32-byte key from a user's passphrase
    suitable for use with Fernet.
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100_000,
    )
    key_bytes = kdf.derive(passphrase.encode("utf-8"))
    return base64.urlsafe_b64encode(key_bytes).decode("utf-8")

def encrypt_value(value: str, key: str) -> str:
    """
    Encrypts a string value using the provided Fernet key.
    Returns the ciphertext as a base64 encoded string.
    """
    if not value:
        return ""
    f = Fernet(key.encode("utf-8"))
    encrypted_bytes = f.encrypt(value.encode("utf-8"))
    return encrypted_bytes.decode("utf-8")

def decrypt_value(token: str, key: str) -> str:
    """
    Decrypts a base64 Fernet token using the provided key.
    Returns the original string.
    """
    if not token:
        return ""
    f = Fernet(key.encode("utf-8"))
    decrypted_bytes = f.decrypt(token.encode("utf-8"))
    return decrypted_bytes.decode("utf-8")

def encrypt_pii_fields(data: Dict[str, Any], fields: List[str], key: str) -> Dict[str, Any]:
    """
    Encrypts specific PII fields in a dictionary in-place and returns a copy.
    """
    encrypted_data = data.copy()
    for field in fields:
        if field in encrypted_data:
            val = encrypted_data[field]
            if isinstance(val, str):
                encrypted_data[field] = encrypt_value(val, key)
            elif isinstance(val, (int, float, bool)):
                # Convert primitive types to string before encryption
                encrypted_data[field] = encrypt_value(str(val), key)
            elif isinstance(val, dict):
                # Recursively encrypt nested dictionaries
                encrypted_data[field] = encrypt_pii_fields(val, list(val.keys()), key)
    return encrypted_data

def decrypt_pii_fields(data: Dict[str, Any], fields: List[str], key: str) -> Dict[str, Any]:
    """
    Decrypts specific encrypted fields in a dictionary in-place and returns a copy.
    """
    decrypted_data = data.copy()
    for field in fields:
        if field in decrypted_data:
            val = decrypted_data[field]
            if isinstance(val, str):
                decrypted_data[field] = decrypt_value(val, key)
            elif isinstance(val, dict):
                decrypted_data[field] = decrypt_pii_fields(val, list(val.keys()), key)
    return decrypted_data
