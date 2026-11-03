# ReqFlow — Evidencia de pruebas

## API (`api/`)

Pruebas basadas en el contrato observado en [ENDPOINTS.md](./ENDPOINTS.md). La cobertura de casos de error genéricos 500 usa fallos simulados de SQLite/filesystem; no altera el código del producto. Los tests existentes ejercitan aspectos de H-API-01 (rechazo de token inválido; no demuestra JWT seguro), H-API-02 (consultas y contrato), H-API-03 (aislamiento de owner), H-API-04 (validación de archivo, con riesgos pendientes), H-API-05 (smoke de rutas que usan las dependencias, no auditoría de advisories), H-API-06 (respuesta de errores observada, no remediación) y H-API-09 (validación tipada). La asociación con un ID no significa que el hallazgo esté resuelto.

### Matriz endpoint | caso | tipo | resultado esperado

| endpoint | caso | tipo | resultado esperado |
|---|---|---|---|
| `GET /api/tasks` | Listar tareas sembradas del usuario | Feliz | 200; arreglo con campos del contrato y solo tareas de la identidad |
| `GET /api/tasks` | Omitir `owner` o enviarlo vacío | Borde | 200; usar la identidad del token |
| `GET /api/tasks` | Sin autorización | Error (401) | 401 con cuerpo `detail` |
| `GET /api/tasks` | `owner` de otra identidad | Error (403) | 403, `{"detail":"Forbidden"}` |
| `GET /api/tasks` | Método no admitido en la ruta compartida `/api/tasks` | Error (405) | 405, `{"detail":"Method Not Allowed"}`; la ruta admite tanto GET como POST |
| `GET /api/tasks` | Fallo simulado de SQLite | Error (500) | 500, cuerpo `text/plain` `Internal Server Error` |
| `POST /api/tasks` | Crear tarea completa o con campos omitidos | Feliz | 201; respuesta con la tarea persistida y `createdAt` |
| `POST /api/tasks` | Objeto JSON vacío | Borde | 201; aplicar defaults `title=""`, `description=""`, `status="TODO"`, `priority="MEDIUM"` y owner autenticado |
| `POST /api/tasks` | Campo `title` con tipo incompatible | Error (422) | 422; detalle de validación apunta a `body.title` |
| `POST /api/tasks` | Sin autorización | Error (401) | 401 con cuerpo `detail` |
| `POST /api/tasks` | Owner ajeno en body | Error (403) | 403, `{"detail":"Forbidden"}`; no crear con owner ajeno |
| `POST /api/tasks` | Método no admitido en la ruta compartida `/api/tasks` | Error (405) | 405, `{"detail":"Method Not Allowed"}` |
| `POST /api/tasks` | Fallo simulado de SQLite | Error (500) | 500, cuerpo `text/plain` `Internal Server Error` |
| `GET /api/summary` | Resumen de tareas del usuario | Feliz | 200; owner, total, conteos por estado y prioridades abiertas |
| `GET /api/summary` | `owner` vacío | Borde | 200; resumir la identidad del token |
| `GET /api/summary` | Sin autorización | Error (401) | 401 con cuerpo `detail` |
| `GET /api/summary` | Consultar owner ajeno | Error (403) | 403, `{"detail":"Forbidden"}` |
| `GET /api/summary` | Método no admitido | Error (405) | 405, `{"detail":"Method Not Allowed"}` |
| `GET /api/summary` | Fallo simulado de SQLite | Error (500) | 500, cuerpo `text/plain` `Internal Server Error` |
| `POST /api/requirements` | Subir archivo permitido | Feliz | 201; owner, nombre normalizado, ruta y tamaño |
| `POST /api/requirements` | Archivo del tamaño máximo (5 MiB) y rutas/nombres normalizados | Borde | 201 dentro del límite; nombre inseguro no escapa del directorio |
| `POST /api/requirements` | Archivo de más de 5 MiB | Error (413) | 413, `{"detail":"File too large"}` |
| `POST /api/requirements` | Extensión no permitida o ausente | Error (415) | 415, `{"detail":"Unsupported file type"}` |
| `POST /api/requirements` | Nombre compuesto solo por puntos | Error (400) | 400, `{"detail":"Invalid file name"}` |
| `POST /api/requirements` | Multipart sin boundary | Error (400) | 400, `{"detail":"Missing boundary in multipart."}` |
| `POST /api/requirements` | Sin campo `file` | Error (422) | 422; detalle identifica `body.file` |
| `POST /api/requirements` | Sin autorización | Error (401) | 401 con cuerpo `detail` |
| `POST /api/requirements` | Método no admitido | Error (405) | 405, `{"detail":"Method Not Allowed"}` |
| `POST /api/requirements` | Fallo simulado al escribir el archivo | Error (500) | 500, cuerpo `text/plain` `Internal Server Error` |
| `GET /api/backend-health` | Upstream devuelve 200 | Feliz | HTTP 200; requestedBy, estado upstream y body |
| `GET /api/backend-health` | Upstream devuelve 503 o lanza excepción | Borde | HTTP 200; conservar estado upstream o `status: 0` y texto de la excepción |
| `GET /api/backend-health` | Sin autorización | Error (401) | 401 con cuerpo `detail` |
| `GET /api/backend-health` | Método no admitido | Error (405) | 405, `{"detail":"Method Not Allowed"}` |

Pruebas que ya cubrían los caminos felices y bordes:

- [test_api.py](../api/tests/test_api.py): tareas sembradas, creación/resumen, subida válida y token inválido.
- [test_tasks_characterization.py](../api/tests/test_tasks_characterization.py): formas de respuesta, defaults, conteos, SQL y filtros.
- [test_authorization.py](../api/tests/test_authorization.py): owner propio/ajeno en lecturas y creación.
- [test_uploads.py](../api/tests/test_uploads.py): extensiones, nombres, traversal, límite exacto y exceso.
- [test_dependencies_smoke.py](../api/tests/test_dependencies_smoke.py): smoke de urllib3 y multipart.

Casos de errores de ruta, validación y fallos simulados añadidos en [test_endpoint_contracts.py](../api/tests/test_endpoint_contracts.py).

### Código de los tests añadidos

Archivo: `api/tests/test_endpoint_contracts.py`.

```python
"""Contract error and edge cases for the documented API endpoints."""
import sqlite3
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.helpers import auth_headers

TASK_PAYLOAD = {
    "title": "Review API",
    "description": "Check required changes",
    "status": "TODO",
    "priority": "HIGH",
}
UPLOAD_FILE = {"file": ("requirements.txt", b"Login requirement", "text/plain")}
ERROR_BODY = "Internal Server Error"


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.mark.parametrize(
    ("method", "path", "request_options"),
    [
        ("GET", "/api/tasks", {}),
        ("POST", "/api/tasks", {"json": TASK_PAYLOAD}),
        ("GET", "/api/summary", {}),
        ("POST", "/api/requirements", {"files": UPLOAD_FILE}),
        ("GET", "/api/backend-health", {}),
    ],
)
def test_each_endpoint_rejects_missing_authentication(
    client: TestClient,
    method: str,
    path: str,
    request_options: dict[str, object],
) -> None:
    response = client.request(method, path, **request_options)
    assert response.status_code == 401
    assert "detail" in response.json()


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("DELETE", "/api/tasks"),
        ("PUT", "/api/summary"),
        ("PUT", "/api/requirements"),
        ("PUT", "/api/backend-health"),
    ],
)
def test_each_endpoint_rejects_unsupported_method(
    client: TestClient,
    method: str,
    path: str,
) -> None:
    response = client.request(method, path, headers=auth_headers())
    assert response.status_code == 405
    assert response.json() == {"detail": "Method Not Allowed"}


@pytest.mark.parametrize("path", ["/api/tasks", "/api/summary"])
def test_read_endpoints_reject_a_different_owner(
    client: TestClient,
    path: str,
) -> None:
    response = client.get(path, headers=auth_headers(), params={"owner": "trainer"})
    assert response.status_code == 403
    assert response.json() == {"detail": "Forbidden"}


def test_create_task_rejects_a_different_owner(client: TestClient) -> None:
    response = client.post(
        "/api/tasks",
        headers=auth_headers(),
        json={**TASK_PAYLOAD, "owner": "trainer"},
    )
    assert response.status_code == 403
    assert response.json() == {"detail": "Forbidden"}


def test_create_task_accepts_an_empty_object_and_applies_defaults(client: TestClient) -> None:
    response = client.post("/api/tasks", headers=auth_headers(), json={})
    body = response.json()
    assert response.status_code == 201
    assert body == {
        "id": 4,
        "title": "",
        "description": "",
        "status": "TODO",
        "owner": "student",
        "priority": "MEDIUM",
        "createdAt": body["createdAt"],
    }
    datetime.strptime(body["createdAt"], "%Y-%m-%d %H:%M:%S")


def test_create_task_rejects_a_non_string_title(client: TestClient) -> None:
    response = client.post(
        "/api/tasks",
        headers=auth_headers(),
        json={**TASK_PAYLOAD, "title": 5},
    )
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "title"]


def test_summary_uses_identity_for_empty_owner_filter(client: TestClient) -> None:
    response = client.get(
        "/api/summary",
        headers=auth_headers(),
        params={"owner": ""},
    )
    assert response.status_code == 200
    assert response.json()["owner"] == "student"
    assert response.json()["total"] == 2


def test_upload_rejects_missing_file(client: TestClient) -> None:
    response = client.post("/api/requirements", headers=auth_headers())
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "file"]


def test_upload_rejects_multipart_without_boundary(client: TestClient) -> None:
    response = client.post(
        "/api/requirements",
        headers={
            **auth_headers(),
            "Content-Type": "multipart/form-data",
        },
        content="not a multipart body",
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "Missing boundary in multipart."}


@pytest.mark.parametrize(
    ("path", "method", "kwargs"),
    [
        ("/api/tasks", "GET", {}),
        ("/api/summary", "GET", {}),
    ],
)
def test_task_read_endpoints_return_generic_500_on_database_error(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    path: str,
    method: str,
    kwargs: dict[str, object],
) -> None:
    def fail_read(*args: object, **kwargs: object) -> None:
        raise sqlite3.OperationalError("database unavailable")

    monkeypatch.setattr("app.main.TaskRepository.list_by_owner", fail_read)
    response = client.request(method, path, headers=auth_headers(), **kwargs)
    assert response.status_code == 500
    assert response.text == ERROR_BODY


def test_create_task_returns_generic_500_on_database_error(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_create(*args: object, **kwargs: object) -> None:
        raise sqlite3.OperationalError("database unavailable")

    monkeypatch.setattr("app.main.TaskRepository.create", fail_create)
    response = client.post(
        "/api/tasks",
        headers=auth_headers(),
        json=TASK_PAYLOAD,
    )
    assert response.status_code == 500
    assert response.text == ERROR_BODY


def test_upload_returns_generic_500_on_filesystem_error(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fail_save(*args: object, **kwargs: object) -> int:
        raise OSError("filesystem unavailable")

    monkeypatch.setattr("app.main.save_limited", fail_save)
    response = client.post(
        "/api/requirements",
        headers=auth_headers(),
        files=UPLOAD_FILE,
    )
    assert response.status_code == 500
    assert response.text == ERROR_BODY


@pytest.mark.parametrize(
    ("upstream_status", "upstream_body"),
    [
        (503, b'{"status":"DOWN"}'),
        (0, b"upstream unavailable"),
    ],
)
def test_backend_health_keeps_api_200_for_upstream_failure(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    upstream_status: int,
    upstream_body: bytes,
) -> None:
    class FakeResponse:
        status = upstream_status
        data = upstream_body

    class FakePoolManager:
        def request(self, method: str, url: str, timeout: float) -> FakeResponse:
            if upstream_status == 0:
                raise RuntimeError(upstream_body.decode("utf-8"))
            return FakeResponse()

    monkeypatch.setattr("app.main.urllib3.PoolManager", FakePoolManager)
    response = client.get("/api/backend-health", headers=auth_headers())
    assert response.status_code == 200
    assert response.json() == {
        "requestedBy": "student",
        "status": upstream_status,
        "body": upstream_body.decode("utf-8"),
    }
```

### Ejecuciones y cobertura

Python **3.13.15**, entorno `api/.venv`, Windows.

| comando | directorio de trabajo | código de salida | resultado |
|---|---|---:|---|
| `.\.venv\Scripts\python.exe -m pytest --cov=app --cov-report=term-missing --cov-report=html --cov-fail-under=85` | `api/` | 0 | 65 pasaron, 131 warnings; gate de 85 % satisfecho; HTML en `api/htmlcov/`. |

**Cobertura global de la aplicación** (medida con `pytest-cov`/Coverage.py, configuración `api/pyproject.toml`, `source=["app"]`, branch coverage activada): **178/178 statements y 16/16 branches = 100 %** en este run. Informe HTML: `api/htmlcov/index.html`. El umbral del comando sigue en 85 %; no fue reducido.

**Cobertura del diff**: no se modificó código de producción. Las pruebas nuevas están fuera del `source=["app"]`, por lo que la cobertura específica del código de pruebas no aplica; la cifra anterior es global para la aplicación.

### Fallos, pendientes y pruebas propuestas

- **Fallo de prueba durante el desarrollo (corregido)**: la primera ejecución de `test_endpoint_contracts.py` esperaba 405 para `GET /api/tasks`, que es una operación válida. El código de salida fue 1. El resumen de esa ejecución no conservó la línea exacta del comando. Se corrigió el caso para usar `DELETE`; además, docs/ENDPOINTS.md ahora especifica que `/api/tasks` admite ambos métodos. La suite final documentada pasó después.
- **Pendiente H-API-01**: las pruebas ejercitan el formato de token heredado, no demuestran firma JWT, emisor ni audiencia; el token actual es falsificable. No se afirma que la autenticación sea segura.
- **Pendiente H-API-04**: las pruebas no fijan como comportamiento deseado la sobrescritura, el límite de request antes de que Starlette parse el multipart, ni nombres excesivamente largos. La documentación registra esos riesgos; H-API-04 continúa Pendiente.
- **Pendiente H-API-06**: no se asertan como comportamiento aceptable los detalles verbosos de token/upstream; la implementación actual los devuelve. Requiere remediación aprobada.
- **Pruebas propuestas cuando se acuerde el contrato/remediación**: JWT firmado real (H-API-01); aislamiento de nombres entre owners y rechazo temprano de cargas grandes (H-API-04); mensajes genéricos en 401 y backend-health (H-API-06). No se implementaron ni se reportan como ejecutadas.
- Se generaron warnings de deprecación de `FastAPI.on_event`; no causaron fallos y no se cambió el umbral ni se silenció ningún warning.

### Fuentes consultadas

- [ENDPOINTS.md](./ENDPOINTS.md): contrato observado, respuestas y riesgos pendientes.
- [HALLAZGOS.md](../HALLAZGOS.md): IDs y estados de los hallazgos API.
- `api/pyproject.toml`: configuración de pytest y Coverage.py.
- Tests existentes enlazados arriba y `api/tests/test_endpoint_contracts.py`: evidencia de casos y código de pruebas.
