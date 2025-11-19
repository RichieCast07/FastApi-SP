import os
import json
from typing import Optional, Tuple, Dict, Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI(
    title="Load Balancer",
    description="Funcionamiento del balanceo de carga.",
    version="1.0.0"
)

SERVER_ID = os.getenv("SERVER_ID", "Backend-Default")


def _client_host_from_request(request: Request) -> Optional[str]:
    client = getattr(request, "client", None)
    if not client:
        return None
    try:
        if isinstance(client, tuple):
            return client[0]
        host = getattr(client, "host", None)
        if host:
            return host
    except Exception:
        return None
    return None


def parse_xff(header_value: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    if not header_value:
        return None, None
    parts = [p.strip() for p in header_value.split(",") if p.strip()]
    first = parts[0] if len(parts) >= 1 else None
    second = parts[1] if len(parts) >= 2 else None
    return first, second


@app.get("/")
async def root(request: Request) -> JSONResponse:
    headers = request.headers

    xff = headers.get("x-forwarded-for")
    x_real_ip = headers.get("x-real-ip")

    xff_first, xff_second = parse_xff(xff)

    client_ip = xff_first or _client_host_from_request(request) or "unknown"

    load_balancer_ip = x_real_ip or xff_second or _client_host_from_request(request) or "unknown"

    response_data = {
        "status": "success",
        "server_id": SERVER_ID,
        "client_ip": client_ip,
        "load_balancer_ip": load_balancer_ip,
    }
    
    return JSONResponse(content=response_data)


@app.get("/health")
async def health() -> Dict[str, str]:
    """Endpoint de salud simple para health checks."""
    return {"status": "UP", "service": "Backend API", "id": SERVER_ID}


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", "8000"))
    
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)