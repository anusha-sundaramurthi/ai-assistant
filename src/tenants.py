import json
import os
import uuid
import secrets
from datetime import datetime

TENANTS_FILE = "tenants.json"

def _load() -> dict:
    if not os.path.exists(TENANTS_FILE):
        return {}
    with open(TENANTS_FILE, "r") as f:
        return json.load(f)

def _save(data: dict):
    with open(TENANTS_FILE, "w") as f:
        json.dump(data, f, indent=2)

def create_tenant(name: str, config: dict = {}) -> dict:
    """Create a new widget tenant. Returns widget_id and api_key."""
    tenants = _load()
    widget_id = str(uuid.uuid4())[:8]
    api_key   = secrets.token_urlsafe(32)
    tenants[widget_id] = {
        "widget_id":   widget_id,
        "name":        name,
        "api_key":     api_key,
        "collection":  f"tenant_{widget_id}",
        "config":      config,
        "created_at":  datetime.utcnow().isoformat()
    }
    _save(tenants)
    return tenants[widget_id]

def get_tenant(widget_id: str) -> dict | None:
    return _load().get(widget_id)

def get_tenant_by_api_key(api_key: str) -> dict | None:
    for tenant in _load().values():
        if tenant["api_key"] == api_key:
            return tenant
    return None

def list_tenants() -> list:
    return list(_load().values())

def update_tenant_config(widget_id: str, config: dict) -> dict | None:
    tenants = _load()
    if widget_id not in tenants:
        return None
    tenants[widget_id]["config"] = config
    _save(tenants)
    return tenants[widget_id]

def delete_tenant(widget_id: str) -> bool:
    tenants = _load()
    if widget_id not in tenants:
        return False
    del tenants[widget_id]
    _save(tenants)
    return True