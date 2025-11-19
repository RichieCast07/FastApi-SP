import os
from typing import Optional, Tuple

from fastapi import FastAPI, Request

app = FastAPI()

SERVER_ID = os.getenv("SERVER_ID", "Backend-Default")


def _client_host_from_request(request: Request) -> Optional[str]:
    """Obtener la IP remota (host) desde request.client de forma segura."""
    client = getattr(request, "client", None)
    if not client:
        return None
    # En Starlette/FastAPI normalmente es una tupla (host, port) o un objeto con atributos
    try:
        # caso tuple (host, port)
        if isinstance(client, tuple):
            return client[0]
        # caso objeto con .host
        host = getattr(client, "host", None)
        if host:
            return host
    except Exception:
        return None
    return None


def parse_xff(header_value: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """Parsea X-Forwarded-For y devuelve (first, second) si existen.

    - first: primer valor (client original)
    - second: segundo valor (posible proxy/load balancer)
    """
    if not header_value:
        return None, None
    # X-Forwarded-For suele ser una lista separada por comas: client, proxy1, proxy2
    parts = [p.strip() for p in header_value.split(",") if p.strip()]
    first = parts[0] if len(parts) >= 1 else None
    second = parts[1] if len(parts) >= 2 else None
    return first, second


@app.get("/")
async def root(request: Request):
    """Endpoint principal que devuelve información para verificar el balanceo de carga."""
    headers = request.headers

    xff = headers.get("x-forwarded-for")
    x_real_ip = headers.get("x-real-ip")

    xff_first, xff_second = parse_xff(xff)

    # client_ip: preferir XFF primero
    client_ip = xff_first or _client_host_from_request(request) or "unknown"

    # load_balancer_ip: preferir X-Real-IP; si no, usar segundo valor de XFF; si no, la ip directa
    load_balancer_ip = x_real_ip or xff_second or _client_host_from_request(request) or "unknown"

    return {
        "status": "success",
        "server_id": SERVER_ID,
        "client_ip": client_ip,
        "load_balancer_ip": load_balancer_ip,
    }


@app.get("/health")
async def health():
    """Endpoint de salud simple para los health checks de Nginx u otro proxy."""
    return {"status": "UP", "service": "Backend API", "id": SERVER_ID}


if __name__ == "__main__":
    # Permite ejecutar directamente `python main.py` para desarrollo rápido.
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=False)
