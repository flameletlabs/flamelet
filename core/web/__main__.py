"""Flamelet Web UI entry point."""

import uvicorn

from core.web.app import app


def main():
    """Start the web server."""
    uvicorn.run(app, host="0.0.0.0", port=7070, reload=False)


if __name__ == "__main__":
    main()
