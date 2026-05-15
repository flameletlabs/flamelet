"""Flamelet Web API FastAPI application."""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

from core.web.api import operations, runs, services, stream, tenants
from core.web.db import init_db

# Initialize database on module load
init_db()

app = FastAPI(title="Flamelet Web API", version="0.1.0")


@app.middleware("http")
async def no_cache_html(request: Request, call_next):
    """Prevent browsers from caching index.html so new builds are picked up."""
    response = await call_next(request)
    if response.headers.get("content-type", "").startswith("text/html"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


# Enable CORS for remote access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    """Initialize database on startup."""
    init_db()


# Include API routers
app.include_router(tenants.router, prefix="/api")
app.include_router(operations.router, prefix="/api")
app.include_router(runs.router, prefix="/api")
app.include_router(stream.router, prefix="/api")
app.include_router(services.router, prefix="/api")


# Serve Svelte SPA (if built)
@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve index.html if SPA is built, otherwise return a simple message."""
    dist = Path(__file__).parent.parent.parent / "web" / "dist"
    index_html = dist / "index.html"

    if index_html.exists():
        return Response(
            content=index_html.read_text(),
            media_type="text/html",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )

    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Flamelet Web UI</title>
        <style>
            body { font-family: system-ui; background: #0d1117; color: #e6edf3;
                   display: flex; align-items: center; justify-content: center;
                   height: 100vh; margin: 0; }
            .container { text-align: center; }
            h1 { color: #00d4aa; }
            p { color: #7d8590; }
            code { background: #1c2128; padding: 4px 8px;
                   border-radius: 4px; font-family: monospace; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔥 Flamelet Web UI</h1>
            <p>Frontend not yet built.</p>
            <p>To build the frontend, run:</p>
            <code>cd web && npm install && npm run build</code>
            <p>API is available at <code>/api/tenants</code></p>
        </div>
    </body>
    </html>
    """


# Mount SPA static files if dist exists
dist = Path(__file__).parent.parent.parent / "web" / "dist"
if dist.exists():
    app.mount("/", StaticFiles(directory=dist, html=True), name="spa")
