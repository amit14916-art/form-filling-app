import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from mcp.server.fastmcp import FastMCP
from swarm_core.crypto_utils import derive_key, encrypt_value, decrypt_value

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MCPVaultServer")

mcp = FastMCP("SecureVault")

# Global in-memory vault storage (stores encrypted tokens)
_vault = {}

@mcp.tool()
async def vault_store_secret(key: str, value: str, passphrase: str) -> str:
    """
    Encrypts a secret value with a key derived from the passphrase, and stores it in the vault.
    """
    try:
        if not key or not value or not passphrase:
            return "ERROR: Missing key, value, or passphrase."
        
        derived_key = derive_key(passphrase)
        encrypted_token = encrypt_value(value, derived_key)
        _vault[key] = encrypted_token
        
        logger.info(f"[MCPVaultServer] Successfully stored encrypted secret for key: '{key}'")
        return f"SUCCESS: Secret for '{key}' stored securely."
    except Exception as e:
        logger.error(f"[MCPVaultServer] Store failed: {e}")
        return f"ERROR: Store failed: {str(e)}"

@mcp.tool()
async def vault_retrieve_secret(key: str, passphrase: str) -> str:
    """
    Decrypts and retrieves a stored secret using the correct passphrase.
    """
    try:
        if not key or not passphrase:
            return "ERROR: Missing key or passphrase."
        
        if key not in _vault:
            return f"ERROR: Key '{key}' not found in vault."
            
        derived_key = derive_key(passphrase)
        encrypted_token = _vault[key]
        decrypted_value = decrypt_value(encrypted_token, derived_key)
        
        logger.info(f"[MCPVaultServer] Successfully retrieved and decrypted secret for key: '{key}'")
        return decrypted_value
    except Exception as e:
        logger.error(f"[MCPVaultServer] Retrieval failed: {e}")
        return f"ERROR: Retrieval failed (check if passphrase is correct): {str(e)}"

@mcp.tool()
async def vault_clear_secrets() -> str:
    """
    Clears all stored secrets from the in-memory vault.
    """
    _vault.clear()
    logger.info("[MCPVaultServer] Vault cleared.")
    return "SUCCESS: All secrets cleared from vault."

if __name__ == "__main__":
    mcp.run()
