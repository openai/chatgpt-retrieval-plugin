import json
from urllib.request import urlopen
from jose import jwt

from fastapi import FastAPI, File, HTTPException, Depends, Body, UploadFile
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

bearer_scheme = HTTPBearer()


def validate_token(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    token = credentials.credentials

    # load the details from the fast api config
    auth0_domain = "fluid-ai-gpt-converse.us.auth0.com"
    api_audience = "https://fluidai-gpt-audience-api-identifier"

    # generate url for the jwks and load it
    jsonurl = urlopen("https://" + auth0_domain + "/.well-known/jwks.json")
    jwks = json.loads(jsonurl.read())

    # get the unverified headers
    unverified_header = jwt.get_unverified_header(token)
    token_algorithms = [unverified_header['alg']]

    # loop through the jwks keys and see if the token matches any of the tokens
    rsa_key = {}
    for key in jwks["keys"]:
        if key["kid"] == unverified_header["kid"]:
            rsa_key = {
                "kty": key["kty"],
                "kid": key["kid"],
                "use": key["use"],
                "n": key["n"],
                "e": key["e"]
            }
    if rsa_key:
        try:
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=token_algorithms,
                audience=api_audience,
                issuer="https://" + auth0_domain + "/"
            )

            tenant = payload['fluidai_app_metadata']['tenant']
            print('tenant: ', tenant)
        except jwt.ExpiredSignatureError:
            error = "token is expired"
            raise HTTPException(status_code=401, detail=error)
        except jwt.JWTClaimsError:
            error = "incorrect claims, please check the audience and issuer"
            raise HTTPException(status_code=401, detail=error)
        except Exception as err:
            error = "Unable to parse authentication token: " + str(err)
            raise HTTPException(status_code=401, detail=error)

        return True, None, tenant
    raise HTTPException(status_code=401, detail="RSA Token is invalid")
