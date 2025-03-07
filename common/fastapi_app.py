#!/usr/bin/env python
import os
from fastapi import FastAPI
from common.openapi_utils import transform_to_swagger_2
from common.vellox_handler import create_vellox_handler
from common.logging_utils import info, error, audit, warning, debug, exception

def create_fastapi_app(title: str = "My Project", root_path: str = None, include_handler: bool = True):
    """
    Creates and configures a FastAPI application instance with optional Vellox handler.
    """

    # Detect if running in GCP Cloud Functions
    is_gcp = "FUNCTION_NAME" in os.environ
    is_local = os.getenv("ENVIRONMENT", "local") == "local"

    if is_local:
        root_path = "/"
    elif is_gcp:
        root_path = f"/{os.getenv('FUNCTION_NAME')}"
    else:
        root_path = "" #TODO: probably should raise an ERROR here, but not sure what else to do when not sure

    app = FastAPI(
        title=title,
        version=os.getenv("DEPLOYED_VERSION") if os.environ.get('DEPLOYED_VERSION') is not None else "x.x.x",
        root_path=root_path
    )

    # Add the /openapi_v2.json endpoint
    @app.get("/openapi_v2.json", include_in_schema=False)
    def get_openapi_v2():
        """
        Returns the OpenAPI specification in Swagger 2.X format.
        """
        openapi_spec = app.openapi()
        swagger_2_spec = transform_to_swagger_2(openapi_spec)
        return swagger_2_spec

    if include_handler:
        handler = create_vellox_handler(app)
        return app, handler

    return app