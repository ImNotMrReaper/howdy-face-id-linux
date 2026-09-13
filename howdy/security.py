"""
Howdy Biometric Security & Cryptographic Key Management Engine
Standard: AES-256-GCM Authenticated Encryption with Associated Data (AEAD)
Key Derivation: HKDF-SHA256 with /etc/machine-id hardware binding
"""

import os
import json
import secrets
import stat
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes

HOWDY_DIR = "/lib/security/howdy"
KEY_FILE = os.path.join(HOWDY_DIR, "security.key")
MACHINE_ID_FILE = "/etc/machine-id"
MAGIC_HEADER = b"HOWDY_ENC_V1\x00"

def _get_or_create_master_key() -> bytes:
    """Retrieve or generate the 256-bit cryptographically secure master key"""
    if os.path.exists(KEY_FILE):
        try:
            with open(KEY_FILE, "rb") as f:
                key = f.read().strip()
                if len(key) == 32:
                    return key
        except Exception:
            pass

    # Generate new random 32-byte (256-bit) secret
    new_key = secrets.token_bytes(32)
    tmp_file = KEY_FILE + ".tmp"
    with open(tmp_file, "wb") as f:
        f.write(new_key)
    os.chmod(tmp_file, stat.S_IRUSR) # 0400 - read-only for root
    os.replace(tmp_file, KEY_FILE)
    return new_key

def _get_cipher() -> AESGCM:
    """Derive machine-unique AES-256-GCM cipher bound to this hardware"""
    master_key = _get_or_create_master_key()
    mach_id = b"default_machine_salt"
    if os.path.exists(MACHINE_ID_FILE):
        try:
            with open(MACHINE_ID_FILE, "rb") as f:
                mach_id = f.read().strip()
        except Exception:
            pass

    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"howdy_biometric_salt_v1",
        info=b"howdy_face_aes256_gcm"
    )
    derived_key = hkdf.derive(master_key + b":" + mach_id)
    return AESGCM(derived_key)

def load_user_models(user: str) -> list:
    """Load and transparently decrypt user face models from disk"""
    model_path = os.path.join(HOWDY_DIR, "models", f"{user}.dat")
    if not os.path.exists(model_path):
        return []

    with open(model_path, "rb") as f:
        payload = f.read()

    if not payload:
        return []

    # Check for AES-256-GCM Magic Header
    if payload.startswith(MAGIC_HEADER):
        try:
            cipher = _get_cipher()
            header_len = len(MAGIC_HEADER)
            nonce = payload[header_len:header_len + 12]
            ciphertext = payload[header_len + 12:]
            decrypted = cipher.decrypt(nonce, ciphertext, None)
            return json.loads(decrypted.decode("utf-8"))
        except Exception as e:
            print(f"[Security Error] Failed to decrypt face models for {user}: {e}", file=sys.stderr)
            return []
    else:
        # Legacy plaintext JSON - load and immediately encrypt on disk
        try:
            models = json.loads(payload.decode("utf-8"))
            save_user_models(user, models)
            return models
        except Exception:
            return []

def save_user_models(user: str, models: list) -> None:
    """Encrypt face models with AES-256-GCM and atomically save to disk"""
    models_dir = os.path.join(HOWDY_DIR, "models")
    os.makedirs(models_dir, exist_ok=True)
    model_path = os.path.join(models_dir, f"{user}.dat")

    cipher = _get_cipher()
    data = json.dumps(models).encode("utf-8")
    nonce = os.urandom(12)
    ciphertext = cipher.encrypt(nonce, data, None)
    payload = MAGIC_HEADER + nonce + ciphertext

    tmp_path = model_path + ".tmp"
    with open(tmp_path, "wb") as f:
        f.write(payload)

    # Restrict permissions: 0600 - root read/write only
    os.chmod(tmp_path, stat.S_IRUSR | stat.S_IWUSR)
    os.replace(tmp_path, model_path)
