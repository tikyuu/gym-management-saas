from functools import lru_cache

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import HTTPException

from app.settings import Settings


class CognitoAdmin:
    def __init__(self, client):
        self.client = client

    def verified_email(self, user_pool_id: str, subject: str) -> str:
        try:
            user = self.client.admin_get_user(UserPoolId=user_pool_id, Username=subject)
        except (BotoCoreError, ClientError) as error:
            raise HTTPException(status_code=503, detail="Identity provider is unavailable.") from error
        attributes = {item["Name"]: item["Value"] for item in user["UserAttributes"]}
        if attributes.get("sub") != subject or attributes.get("email_verified") != "true" or not attributes.get("email"):
            raise HTTPException(status_code=403, detail="Verified email is required.")
        return attributes["email"]

    def invite(self, user_pool_id: str, email: str) -> str:
        try:
            user = self.client.admin_create_user(
                UserPoolId=user_pool_id,
                Username=email.lower(),
                UserAttributes=[{"Name": "email", "Value": email.lower()}],
                DesiredDeliveryMediums=["EMAIL"],
            )["User"]
        except (BotoCoreError, ClientError) as error:
            if isinstance(error, ClientError) and error.response["Error"]["Code"] in ("UsernameExistsException", "AliasExistsException"):
                raise HTTPException(status_code=409, detail="User already exists.") from error
            raise HTTPException(status_code=503, detail="Identity provider is unavailable.") from error
        subject = next((item["Value"] for item in user["Attributes"] if item["Name"] == "sub"), None)
        if subject is None:
            raise HTTPException(status_code=503, detail="Identity provider did not return a subject.")
        return subject

    def subjects_for_email(self, user_pool_id: str, email: str) -> list[str]:
        subjects = []
        pagination_token = None
        try:
            while True:
                options = {"UserPoolId": user_pool_id, "Filter": f'email = "{email}"'}
                if pagination_token is not None:
                    options["PaginationToken"] = pagination_token
                result = self.client.list_users(**options)
                for user in result["Users"]:
                    subject = next((item["Value"] for item in user["Attributes"] if item["Name"] == "sub"), None)
                    if subject is not None:
                        subjects.append(subject)
                pagination_token = result.get("PaginationToken")
                if pagination_token is None:
                    break
        except (BotoCoreError, ClientError) as error:
            raise HTTPException(status_code=503, detail="Identity provider is unavailable.") from error
        return subjects

    def set_enabled(self, user_pool_id: str, subject: str, enabled: bool) -> None:
        method = self.client.admin_enable_user if enabled else self.client.admin_disable_user
        try:
            method(UserPoolId=user_pool_id, Username=subject)
        except (BotoCoreError, ClientError) as error:
            raise HTTPException(status_code=503, detail="Identity provider is unavailable.") from error

    def delete(self, user_pool_id: str, subject: str) -> None:
        try:
            self.client.admin_delete_user(UserPoolId=user_pool_id, Username=subject)
        except (BotoCoreError, ClientError) as error:
            raise HTTPException(status_code=503, detail="Identity provider is unavailable.") from error


@lru_cache
def get_cognito_admin() -> CognitoAdmin:
    return CognitoAdmin(boto3.client("cognito-idp", region_name=Settings().aws_region))
