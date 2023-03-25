import json 
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from server.main import sub_app

def generate_openapi():
    # assert app.openapi_schema
    openapi_schema = get_openapi(
        title=sub_app.title,
        version=sub_app.version,
        description=sub_app.description,
        routes=sub_app.routes,
        servers=sub_app.servers
    )
    sub_app.openapi_schema = openapi_schema
    with open('.well-known/openapi.json', 'w') as file:
        file.write(json.dumps(openapi_schema, indent = 4))
    print('OpenAPI schema updated.')

