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
| H-API-01 | api | Token Base64 con secreto embebido, sin firma, emisor, audiencia ni verificación real | Vulnerabilidad | El token es solo Base64 y el secreto `WORKSHOP_SECRET_2026` está en el código y en las pruebas; cualquiera que lo conozca puede fabricar un token con cualquier usuario y rol y suplantar identidades. No se valida emisor ni audiencia. | api/app/main.py:14, api/app/main.py:19-22, api/tests/test_api.py:10-12 (evidencia original, antes del cambio) | alta | Implementado localmente en `day1/prompting`; 85 pruebas pasan con 100 % de cobertura. Revisión humana e integración aún pendientes; ver PLAN.md y docs/TESTING.md. |
| H-API-02 | api | SQL construido por concatenación en filtros e inserts | Vulnerabilidad | `owner`, `title`, `description`, `status` y `priority` controlados por el cliente se concatenan en el SQL; permite inyección SQL (lectura/alteración de datos de cualquier usuario) y rompe con comillas. | api/app/main.py:70, api/app/main.py:84, api/app/main.py:87, api/app/main.py:93 | alta | Resuelto. Consultas con placeholders `?` en `TaskRepository` (api/app/repository.py:13-51); rutas tipadas con `TaskCreate`/`TaskResponse`/`TaskSummary` (api/app/schemas.py); el SQL ya no se arma en api/app/main.py. |
| H-API-03 | api | El cliente puede consultar y crear tareas de otro `owner` | Vulnerabilidad | `owner` llega por query o body y se usa en lugar de `identity["username"]`; un usuario autenticado lee el listado y resumen de otro y crea tareas a nombre de otro (IDOR). El rol del token no se usa. | api/app/main.py:69, api/app/main.py:83, api/app/main.py:92, api/app/main.py:94 | alta | Resuelto. `resolve_owner` es la única fuente de `owner` en las rutas y responde 403 genérico si el `owner` pedido es ajeno. H-API-01 ya valida la identidad en esta rama local; revisión e integración pendientes. |
| H-API-04 | api | Subida de archivos con `upload.filename` sin normalizar, sin límite de extensión ni tamaño | Vulnerabilidad | El nombre del cliente se une a la carpeta de subida: permite path traversal/sobrescritura de archivos y nombres peligrosos; el contenido se lee completo en memoria sin tope (DoS) y se devuelve la ruta interna `storedAt`. | api/app/main.py:109-112 | alta | Pendiente (devuelto en la revisión local de IA; corrección parcial). Hecho: nombre normalizado, extensiones permitidas, tope `MAX_UPLOAD_BYTES` y ruta dentro del directorio (api/app/uploads.py:17-49). Falta: (1) `storedAt` sigue devolviendo la ruta del servidor (api/app/main.py:85); (2) cualquier usuario sobrescribe el archivo de otro con el mismo nombre (api/app/main.py:81-84, api/app/uploads.py:30-34); (3) el tope se aplica tras recibir el cuerpo completo, sin rechazo anticipado (api/app/uploads.py:37-49); (4) un nombre de 300 caracteres produce 500 (api/app/uploads.py:17-22). |
| H-API-05 | api | Dependencias con advisories: `urllib3 2.5.0` y `python-multipart 0.0.21` | Vulnerabilidad | `urllib3 2.5.0` está afectada por CVE-2025-66418/CVE-2025-66471 (DoS por descompresión; corregido en 2.6.0) y CVE-2026-21441 (corregido en 2.6.3); `python-multipart 0.0.21` procesa las cargas de archivos y su advisory debe confirmarse. Exposición de urllib3 acotada a `backend_health`. | api/requirements.txt:4, api/requirements.txt:5, api/app/main.py:118 | media | Resuelto. `urllib3` 2.5.0→2.8.0 y `python-multipart` 0.0.21→0.0.33 (api/requirements.txt:4-5); `pip-audit` ya no reporta avisos de ninguno de los dos (antes 6 de `python-multipart` y 5 de `urllib3`). Quedan avisos de `starlette` 0.50.0 (transitivo de fastapi), fuera del plan. |
| H-API-06 | api | Errores que exponen detalles internos al cliente | Vulnerabilidad | El 401 de autenticación ahora usa un detalle genérico como parte de H-API-01. `backend_health` aún devuelve `str(error)` y el cuerpo remoto, lo que puede revelar información interna. Hallazgo adicional, no listado en RETO.md. | api/app/security.py:50, api/app/main.py:80-81 | media | Pendiente por la respuesta de `backend_health`; H-API-01 cubre el error de autenticación. |
| H-API-07 | api | CORS abierto (`*`) con credenciales habilitadas | Vulnerabilidad | Cualquier origen puede invocar la API desde un navegador; con `allow_credentials=True` amplía la superficie de ataque. Hallazgo adicional, no listado en RETO.md. | api/app/main.py:48-54 | media | Pendiente |
| H-API-08 | api | Rutas, acceso a DB, reglas de negocio y serialización en un solo archivo | Refactor | Una sola función `create_app` mezcla conexión SQLite, esquema/seed, rutas, SQL, reglas del resumen y serialización; es difícil de probar, reutilizar y revisar. | api/app/main.py:29-127 | media | Pendiente |
| H-API-09 | api | Calidad: `dict[str, Any]`, `except Exception`, condicionales anidados y duplicación | Refactor | Request/response sin Pydantic ni tipos precisos; `except Exception` esconde fallos; el `if` anidado de 3 niveles y el patrón `owner or identity` + SQL con la misma forma se repiten; valores mágicos (URL, timeout, secreto, estados) sueltos. | api/app/main.py:25, api/app/main.py:56, api/app/main.py:68, api/app/main.py:69-70, api/app/main.py:78, api/app/main.py:92-93, api/app/main.py:101-104, api/app/main.py:116, api/app/main.py:118, api/app/main.py:120 | baja | Pendiente |

#### Candidatos nuevos de discovery (requieren revisión humana)

### H-API-10 — Validación de contenido de tareas sin límites ni catálogo
- Estado: CANDIDATO
- Evidencia: `TaskCreate` define `title`, `description`, `status` y `priority` como `str` sin restricciones (`api/app/schemas.py:6-11`); `POST /api/tasks` persiste esos valores (`api/app/repository.py:43-46`). La documentación confirma que no se restringen longitudes ni valores (`docs/ENDPOINTS.md:234`).
- Impacto: si el consumidor espera estados o prioridades conocidos, una tarea con valores arbitrarios o texto excesivamente largo podría quedar guardada y producir datos incompatibles con filtros o vistas. El impacto depende de que exista un catálogo de negocio aprobado.
- Prioridad propuesta: baja, hasta confirmar las reglas de dominio.
- Contrato potencialmente afectado: entrada de `POST /api/tasks` y agregados `byStatus`/`highPriorityOpen` de `GET /api/summary`.
- Cómo validarlo: acordar primero longitudes y valores permitidos; después probar entradas vacías, sobre el límite y valores desconocidos, verificando el código de respuesta y que el resumen conserve el contrato aprobado.

### H-API-11 — El resumen materializa todas las tareas del propietario
- Estado: CANDIDATO
- Evidencia: `summary` obtiene `tasks.list_by_owner(...)` antes de resumir (`api/app/main.py:75-77`); `list_by_owner` ejecuta `fetchall()` y convierte todas las filas a modelos (`api/app/repository.py:37-41`).
- Impacto: una consulta que devuelve pocos contadores consume tiempo y memoria proporcional al total de tareas del propietario; el coste puede crecer con el historial almacenado.
- Prioridad propuesta: media si se espera crecimiento sostenido; baja para volúmenes pequeños.
- Contrato potencialmente afectado: latencia y disponibilidad de `GET /api/summary`; la forma de su respuesta no necesita cambiar.
- Cómo validarlo: medir latencia y memoria de `/api/summary` con conjuntos de datos crecientes y comparar los contadores con un cálculo de referencia, incluyendo estados cerrados y prioridades distintas.

### H-API-12 — Un fallo de escritura puede dejar una carga parcial en disco
- Estado: CANDIDATO
- Evidencia: `save_limited` elimina el destino solo al capturar `HTTPException` (`api/app/uploads.py:37-48`); errores de lectura/escritura distintos, como `OSError` en `destination.write`, salen sin limpieza (`api/app/uploads.py:40-45`). La prueba actual comprueba un 500 al fallar la función, pero no verifica el estado del archivo (`api/tests/test_endpoint_contracts.py:186-200`).
- Impacto: un archivo incompleto puede permanecer en el directorio de cargas después de que `POST /api/requirements` falle, y confundirse con una carga válida o impedir una recuperación fiable.
- Prioridad propuesta: media.
- Contrato potencialmente afectado: semántica de éxito/error de `POST /api/requirements` y consistencia del almacenamiento local.
- Cómo validarlo: provocar un error de lectura o escritura después de guardar al menos un fragmento; comprobar que la respuesta sigue siendo de error y que no queda un archivo parcial.

### H-API-13 — Conexión SQLite compartida sin serialización explícita
- Estado: CANDIDATO
- Evidencia: `create_app` crea una conexión con `check_same_thread=False` y la entrega al repositorio compartido (`api/app/main.py:50-52`); los endpoints síncronos de lectura y escritura la usan directamente (`api/app/main.py:67-77`), sin bloqueo visible en `TaskRepository` (`api/app/repository.py:25-51`).
- Impacto: solicitudes concurrentes pueden usar la misma conexión desde distintos hilos sin coordinación explícita; podría producir errores intermitentes o interacción inesperada entre operaciones/commits.
- Prioridad propuesta: media, sujeta a reproducir el comportamiento con la configuración de SQLite usada en despliegue.
- Contrato potencialmente afectado: fiabilidad y consistencia de `GET /api/tasks`, `POST /api/tasks` y `GET /api/summary` bajo concurrencia.
- Cómo validarlo: ejecutar solicitudes concurrentes de lectura y creación sobre una misma instancia de app y una base temporal; registrar errores, comprobar todas las inserciones y verificar que cada respuesta corresponde a la operación solicitada.
