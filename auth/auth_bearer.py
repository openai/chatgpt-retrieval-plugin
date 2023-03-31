from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from models.api import User

from .auth_handler import decodeJWT


class GetCurrentUser(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super(GetCurrentUser, self).__init__(auto_error=auto_error)

    async def __call__(self, request: Request):
        credentials: HTTPAuthorizationCredentials = await super(GetCurrentUser, self).__call__(request)
        if credentials:
            if not credentials.scheme == "Bearer":
                raise HTTPException(status_code=403, detail="Invalid authentication scheme.")
            token = self.verify_jwt(credentials.credentials)
            if not token:
                raise HTTPException(status_code=403, detail="Invalid token or expired token.")
            return User(
                token=credentials.credentials, account_id=token["accountId"], organization_id=token["organizationId"], app_role=token["appRole"]
            )
        else:
            raise HTTPException(status_code=403, detail="Invalid authorization code.")

    def verify_jwt(self, jwtoken: str) -> bool:
        isTokenValid: bool = False

        try:
            payload = decodeJWT(jwtoken)
        except:
            payload = None
        return payload