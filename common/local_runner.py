#!/usr/bin/env python
import uvicorn

def run_local(app, host: str = "0.0.0.0", port: int = 8080, debug: bool = False):
    """
    Runs the FastAPI app locally using uvicorn.
    If debug is True, enables auto-reloading and debugging features.
    
    Args:
        app: Either a FastAPI app instance or import string like "main:app"
        host: Host to bind the server to
        port: Port to bind the server to
        debug: Whether to enable debug features like auto-reload
    """
    if debug:
        # In debug mode, we need the import string and must verify it's a string
        if not isinstance(app, str):
            raise TypeError("For debug mode with auto-reload, app must be an import string (e.g., 'main:app')")
        
        uvicorn.run(
            app,
            host=host,
            port=port,
            reload=True,
            log_level="debug"
        )
    else:
        # In normal mode, we can use either the app instance or import string
        uvicorn.run(
            app,
            host=host,
            port=port,
            reload=False,
            log_level="info"
        )
