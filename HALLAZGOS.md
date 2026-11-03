# Hallazgos de ReqFlow

Matriz de seguimiento compartida. Cada componente mantiene su propia sección y numeración (H-AUTH-NN, H-API-NN, H-WEB-NN). Las evidencias se citan desde la raíz del repositorio. Estados: `Pendiente`, `No encontrado` (los demás estados los actualiza el paso de refactor con evidencia real).

## api

### Discovery — API FastAPI (solo lectura, sin cambios de código)

Alcance leído: `api/app/main.py`, `api/requirements.txt`, `api/requirements-dev.txt`, `api/pyproject.toml`, `api/Dockerfile`, `api/tests/test_api.py`, además de `README.md`, `RETO.md` y `docs/GOOD_PRACTICES.md`. `docs/ENDPOINTS.md` no existe, por lo que el contrato se deriva del código (contrato **observado**; aún no hay contrato acordado).

#### Contrato observado (derivado del código)

Todas las rutas exigen `Authorization: Bearer <token>` mediante `Depends(legacy_identity)` (api/app/main.py:17). Sin token válido responden 401.

| Método y ruta | Entrada | Respuesta | Evidencia |
|---|---|---|---|
| `GET /api/tasks` | query opcional `owner` | 200, lista de `{id,title,description,status,owner,priority,createdAt}` | api/app/main.py:67-75 |
| `POST /api/tasks` | JSON libre (`title`,`description`,`status`,`priority`,`owner`) | 201, tarea creada (mismo formato) | api/app/main.py:77-88 |
| `GET /api/summary` | query opcional `owner` | 200, `{owner,total,byStatus,highPriorityOpen}` | api/app/main.py:90-105 |
| `POST /api/requirements` | multipart `file` | 201, `{owner,fileName,storedAt,size}` | api/app/main.py:107-112 |
| `GET /api/backend-health` | — | 200, `{requestedBy,status,body}`; ante error `status` 0 y `body` con el texto de la excepción | api/app/main.py:114-121 |

#### Mapa de flujos

- **Token**: `legacy_identity` quita el prefijo `Bearer `, decodifica Base64, separa por `|` y espera `usuario|rol|exp|secreto`. Solo compara el cuarto campo con la constante `LEGACY_SECRET` y la expiración (api/app/main.py:14, 19-22); no hay firma, emisor ni audiencia. Devuelve `{"username","role"}` (api/app/main.py:24). Cualquier fallo responde 401 con `str(error)` (api/app/main.py:25-26).
- **SQLite**: una única conexión compartida (`check_same_thread=False`) creada en `create_app` (api/app/main.py:35-36), tabla `tasks` creada y sembrada al arrancar (api/app/main.py:37-43). Todas las consultas se arman por concatenación de strings (api/app/main.py:70, 84, 87, 93). Ruta por `WORKSHOP_DB_PATH` (api/app/main.py:30).
- **Carga de archivos**: `selected_uploads` viene de `WORKSHOP_UPLOAD_DIR` (api/app/main.py:31-33). `upload_requirement` usa `file.filename` sin normalizar, sin límite de extensión ni de tamaño, lee todo en memoria y escribe en disco (api/app/main.py:109-111); devuelve la ruta interna `storedAt` (api/app/main.py:112).
- **Integración con auth**: `backend_health` consulta `AUTH_HEALTH_URL` (por defecto `http://localhost:8080/q/health`) con `urllib3` (api/app/main.py:116-119).
- **CORS**: orígenes, métodos y cabeceras `*` con credenciales (api/app/main.py:48-54).

#### Riesgos pendientes de Discovery

- No se ejecutó la suite ni se midió cobertura base (no solicitado en este paso). Las 4 pruebas existentes (api/tests/test_api.py:19-58) solo cubren camino feliz y token inválido; no hay caracterización de `owner`, `summary` con prioridades/estados, `backend-health` ni cargas inválidas.
- Las advisories de SCA se contrastaron con fuentes públicas (urllib3: CVE-2025-66418 y CVE-2025-66471, corregidos en 2.6.0; CVE-2026-21441, corregido en 2.6.3). El CVE de `python-multipart 0.0.21` y las versiones objetivo finales quedan por confirmar con Dependency Review/`pip-audit` en el siguiente paso.
- Endurecer el token (H-API-01) cambia el contrato con auth, que es quien emite el token: cualquier cambio de formato exige coordinación con auth y web (fuera de AMBITO) y no se asume aprobado.

#### Matriz de seguimiento (ordenada de mayor a menor severidad)

| id | componente | hallazgo | tipo | explicacion | evidencia (archivo:linea) | severidad | estado |
|---|---|---|---|---|---|---|---|
| H-API-01 | api | Token Base64 con secreto embebido, sin firma, emisor, audiencia ni verificación real | Vulnerabilidad | El token es solo Base64 y el secreto `WORKSHOP_SECRET_2026` está en el código y en las pruebas; cualquiera que lo conozca puede fabricar un token con cualquier usuario y rol y suplantar identidades. No se valida emisor ni audiencia. | api/app/main.py:14, api/app/main.py:19-22, api/tests/test_api.py:10-12 (el secreto también está en las pruebas) | alta | Aprobado. Sin implementar: bloqueado hasta acordar con auth el contrato de token (claims, `iss`, `aud`, secreto, `JWT_*` en compose); ver PLAN.md. |
| H-API-02 | api | SQL construido por concatenación en filtros e inserts | Vulnerabilidad | `owner`, `title`, `description`, `status` y `priority` controlados por el cliente se concatenan en el SQL; permite inyección SQL (lectura/alteración de datos de cualquier usuario) y rompe con comillas. | api/app/main.py:70, api/app/main.py:84, api/app/main.py:87, api/app/main.py:93 | alta | Resuelto. Consultas con placeholders `?` en `TaskRepository` (api/app/repository.py:13-51); rutas tipadas con `TaskCreate`/`TaskResponse`/`TaskSummary` (api/app/schemas.py); el SQL ya no se arma en api/app/main.py. |
| H-API-03 | api | El cliente puede consultar y crear tareas de otro `owner` | Vulnerabilidad | `owner` llega por query o body y se usa en lugar de `identity["username"]`; un usuario autenticado lee el listado y resumen de otro y crea tareas a nombre de otro (IDOR). El rol del token no se usa. | api/app/main.py:69, api/app/main.py:83, api/app/main.py:92, api/app/main.py:94 | alta | Resuelto. `resolve_owner` (api/app/security.py:7-11) es la única fuente de `owner` en `list_tasks`, `create_task` y `summary`: usa la identidad y responde 403 genérico si el `owner` pedido es ajeno. Verificado en la revisión local; su eficacia depende de H-API-01 (con el token Base64 actual se puede fabricar la identidad de otro usuario: api/app/main.py:21,29). |
| H-API-04 | api | Subida de archivos con `upload.filename` sin normalizar, sin límite de extensión ni tamaño | Vulnerabilidad | El nombre del cliente se une a la carpeta de subida: permite path traversal/sobrescritura de archivos y nombres peligrosos; el contenido se lee completo en memoria sin tope (DoS) y se devuelve la ruta interna `storedAt`. | api/app/main.py:109-112 | alta | Pendiente (devuelto en la revisión local de IA; corrección parcial). Hecho: nombre normalizado, extensiones permitidas, tope `MAX_UPLOAD_BYTES` y ruta dentro del directorio (api/app/uploads.py:17-49). Falta: (1) `storedAt` sigue devolviendo la ruta del servidor (api/app/main.py:85); (2) cualquier usuario sobrescribe el archivo de otro con el mismo nombre (api/app/main.py:81-84, api/app/uploads.py:30-34); (3) el tope se aplica tras recibir el cuerpo completo, sin rechazo anticipado (api/app/uploads.py:37-49); (4) un nombre de 300 caracteres produce 500 (api/app/uploads.py:17-22). |
| H-API-05 | api | Dependencias con advisories: `urllib3 2.5.0` y `python-multipart 0.0.21` | Vulnerabilidad | `urllib3 2.5.0` está afectada por CVE-2025-66418/CVE-2025-66471 (DoS por descompresión; corregido en 2.6.0) y CVE-2026-21441 (corregido en 2.6.3); `python-multipart 0.0.21` procesa las cargas de archivos y su advisory debe confirmarse. Exposición de urllib3 acotada a `backend_health`. | api/requirements.txt:4, api/requirements.txt:5, api/app/main.py:118 | media | Resuelto. `urllib3` 2.5.0→2.8.0 y `python-multipart` 0.0.21→0.0.33 (api/requirements.txt:4-5); `pip-audit` ya no reporta avisos de ninguno de los dos (antes 6 de `python-multipart` y 5 de `urllib3`). Quedan avisos de `starlette` 0.50.0 (transitivo de fastapi), fuera del plan. |
| H-API-06 | api | Errores que exponen detalles internos al cliente | Vulnerabilidad | El 401 devuelve `str(error)` (p. ej. mensajes de `int()` o Base64) y `backend_health` devuelve `str(error)` y el cuerpo remoto; filtran información interna y ayudan a depurar ataques. Hallazgo adicional, no listado en RETO.md. | api/app/main.py:25-26, api/app/main.py:120-121 | media | Pendiente |
| H-API-07 | api | CORS abierto (`*`) con credenciales habilitadas | Vulnerabilidad | Cualquier origen puede invocar la API desde un navegador; con `allow_credentials=True` amplía la superficie de ataque. Hallazgo adicional, no listado en RETO.md. | api/app/main.py:48-54 | media | Pendiente |
| H-API-08 | api | Rutas, acceso a DB, reglas de negocio y serialización en un solo archivo | Refactor | Una sola función `create_app` mezcla conexión SQLite, esquema/seed, rutas, SQL, reglas del resumen y serialización; es difícil de probar, reutilizar y revisar. | api/app/main.py:29-127 | media | Pendiente |
| H-API-09 | api | Calidad: `dict[str, Any]`, `except Exception`, condicionales anidados y duplicación | Refactor | Request/response sin Pydantic ni tipos precisos; `except Exception` esconde fallos; el `if` anidado de 3 niveles y el patrón `owner or identity` + SQL con la misma forma se repiten; valores mágicos (URL, timeout, secreto, estados) sueltos. | api/app/main.py:25, api/app/main.py:56, api/app/main.py:68, api/app/main.py:69-70, api/app/main.py:78, api/app/main.py:92-93, api/app/main.py:101-104, api/app/main.py:116, api/app/main.py:118, api/app/main.py:120 | baja | Pendiente |
