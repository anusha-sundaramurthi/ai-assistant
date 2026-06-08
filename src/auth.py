from fastapi import Header, HTTPException, status
from src.config import MASTER_API_KEY
from src.tenants import get_tenant_by_api_key

def verify_master_key(x_api_key: str = Header(...)):
    if x_api_key != MASTER_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid master API key"
        )

def verify_widget_key(x_api_key: str = Header(...)):
    tenant = get_tenant_by_api_key(x_api_key)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid widget API key"
        )
    return tenant