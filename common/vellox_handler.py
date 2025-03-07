#!/usr/bin/env python
from common.logging_utils import info, error, audit, warning, debug, exception
from vellox import Vellox


 

def create_vellox_handler(app):
    """
    Creates a Vellox instance and a handler function for the given FastAPI app.
    """
    # Initialize Vellox with the FastAPI app
    vellox = Vellox(app=app, lifespan="off")

    def handler(request=None):
        """
        Handler function for cloud functions.
        """
        return vellox(request)

    return handler