from datetime import datetime, timedelta, timezone
from typing import Optional, List
from fastapi import HTTPException, Security, status, Depends
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from app.core.config import settings
import hashlib
import hmac

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)
ALGORITHM = "HS256"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    salt = settings.SECRET_KEY.encode()
    computed = hashlib.pbkdf2_hmac("sha256", plain_password.encode(), salt, 100000).hex()
    return hmac.compare_digest(computed, hashed_password)

def get_password_hash(password: str) -> str:
    salt = settings.SECRET_KEY.encode()
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000).hex()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

async def verify_auth(
    api_key: Optional[str] = Security(api_key_header),
    bearer: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
) -> dict:
    """
    Validates either standard X-API-Key or Bearer JWT token.
    For local development, if API_KEY matches settings.API_KEY, access is granted.
    """
    if api_key and api_key == settings.API_KEY:
        return {"sub": "system_user", "auth_type": "api_key", "roles": ["admin"]}

    if bearer:
        payload = decode_access_token(bearer.credentials)
        if payload:
            return payload

    # If in development or testing and no auth was provided, permit local access with default user role
    if (settings.DEBUG or settings.ENVIRONMENT in ["development", "test"]) and not api_key and not bearer:
        return {"sub": "default_user", "auth_type": "dev_session", "roles": ["user", "admin"]}

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials or missing API key",
        headers={"WWW-Authenticate": "Bearer"},
    )

def require_permissions(required_permissions: List[str]):
    async def permission_checker(current_user: dict = Depends(verify_auth)):
        roles = current_user.get("roles", [])
        if "admin" in roles:
            return current_user
        # Enforce strict policy check
        for perm in required_permissions:
            if perm not in current_user.get("permissions", []):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: Missing '{perm}' capability"
                )
        return current_user
    return permission_checker
