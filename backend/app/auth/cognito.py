from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from app.settings import Settings


@dataclass(frozen=True)
class AuthenticatedUser:
    cognito_sub: str
    user_pool_id: str


bearer_scheme = HTTPBearer(auto_error=False)


@lru_cache
def get_jwks_client(issuer: str) -> PyJWKClient:
    return PyJWKClient(f"{issuer}/.well-known/jwks.json")


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
) -> AuthenticatedUser:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication is required.",
        )

    token = credentials.credentials
    settings = Settings()

    try:
        unverified_claims = jwt.decode(
            token,
            options={"verify_signature": False, "verify_aud": False},
        )
        issuer = unverified_claims["iss"]
        user_pool_id = get_user_pool_id(issuer, settings)
        signing_key = get_jwks_client(issuer).get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=issuer,
            options={"verify_aud": False},
        )
    except (KeyError, jwt.PyJWTError) as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token.",
        ) from error

    if claims.get("token_use") != "access" or not claims.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token.",
        )

    return AuthenticatedUser(
        cognito_sub=claims["sub"],
        user_pool_id=user_pool_id,
    )


def get_user_pool_id(issuer: str, settings: Settings) -> str:
    user_pool_ids = (
        settings.customer_user_pool_id,
        settings.staff_user_pool_id,
        settings.system_admin_user_pool_id,
    )

    for user_pool_id in user_pool_ids:
        expected_issuer = (
            f"https://cognito-idp.{settings.aws_region}.amazonaws.com/"
            f"{user_pool_id}"
        )
        if issuer == expected_issuer:
            return user_pool_id

    raise jwt.InvalidIssuerError("The token issuer is not allowed.")
