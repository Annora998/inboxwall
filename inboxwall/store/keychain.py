"""InBox Wall v2 - OS Keychain integration."""
import json
import keyring

SERVICE_NAME = "inboxwall"

def save_profile(name: str, host: str, port: int, username: str, password: str):
    """Securely save IMAP credentials to the OS keychain."""
    payload = json.dumps({"host": host, "port": port, "username": username})
    keyring.set_password(SERVICE_NAME, name, payload)
    keyring.set_password(SERVICE_NAME, f"{name}_password", password)

def get_profile(name: str) -> dict | None:
    """Retrieve IMAP credentials from the OS keychain."""
    payload = keyring.get_password(SERVICE_NAME, name)
    if not payload:
        return None
    try:
        data = json.loads(payload)
        data["password"] = keyring.get_password(SERVICE_NAME, f"{name}_password")
        return data
    except Exception:
        return None

def delete_profile(name: str):
    """Remove credentials from the OS keychain."""
    try: keyring.delete_password(SERVICE_NAME, name)
    except Exception: pass
    try: keyring.delete_password(SERVICE_NAME, f"{name}_password")
    except Exception: pass