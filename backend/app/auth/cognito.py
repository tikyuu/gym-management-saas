from dataclasses import dataclass


@dataclass(frozen=True)
class AuthenticatedUser:
    cognito_sub: str
    user_pool_id: str
