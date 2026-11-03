# Plan de corrección de ReqFlow

Plan compartido. Cada componente mantiene su propia sección (`auth`, `api`, `web`). Los IDs y las evidencias provienen de [HALLAZGOS.md](./HALLAZGOS.md); las convenciones, de [docs/GOOD_PRACTICES.md](./docs/GOOD_PRACTICES.md) y de las reglas de Clean Code de `AGENTS.md`.

## api

## Aprobación humana registrada
- Aprobador indicado en el Plan: Marco Soto
- Fecha: 02/11/2026
- IDs aprobados: H-API-01, H-API-02, H-API-03, H-API-04, H-API-05

### Alcance, estado y reglas comunes

- **Hallazgos planificados** (estado `Aprobado` en HALLAZGOS.md; aprobación humana registrada arriba): H-API-01, H-API-02, H-API-03, H-API-04 y H-API-05.
- **Fuera de este plan** (siguen `Pendiente`, sin aprobar): H-API-06 (errores que exponen detalles; solo se toca lo inevitable en H-API-01, ver ese apartado), H-API-07 (CORS), H-API-08 (arquitectura) y H-API-09 (calidad).
- **Estado del plan**: aprobación humana registrada arriba (Marco Soto, 02/11/2026; H-API-01 a H-API-05). Implementados H-API-05, H-API-02, H-API-03 y H-API-04 (ver «Registro de ejecuciones»). H-API-01 fue desbloqueado el 03/11/2026 tras la aprobación explícita del contrato propuesto y la coordinación con auth; su implementación local queda pendiente de revisión humana.
- **Contrato**: `docs/ENDPOINTS.md` documenta los contratos HTTP observados. Se preservan rutas, métodos y claves JSON `id,title,description,status,owner,priority,createdAt`, `owner,total,byStatus,highPriorityOpen`, `owner,fileName,storedAt,size`, `requestedBy,status,body`; H-API-01 reemplaza únicamente el contrato de autenticación conforme al apartado aprobado.
- **Firma pública que no cambia**: `create_app(db_path, upload_dir)` y el objeto `app` en `api/app/main.py` (los usan `api/tests/test_api.py` y el `Dockerfile`: `app.main:app`). Cualquier parámetro nuevo será opcional.
- **Método por hallazgo**: (1) prueba de caracterización que pasa con el código actual y fija el contrato; (2) prueba de comportamiento deseado que falla antes del cambio (rojo) y pasa después (verde); (3) cambio mínimo; (4) regresión con `python tools/lab.py test api` (o `pytest` con cwd `api/`). Meta: 85 % del código modificado; el resultado real se registrará en `docs/TESTING.md`, no aquí.
- **Clean Code (AGENTS.md 8-12)**: una responsabilidad por función; sin duplicación (la resolución de `owner` y la conversión fila→tarea se escriben una vez); guard clauses en lugar de `if` anidados; constantes con nombre en `api/app/config.py` (`JWT_ALGORITHM`, `MAX_UPLOAD_BYTES`, `UPLOAD_CHUNK_BYTES`, `ALLOWED_UPLOAD_EXTENSIONS`, nombres de columnas/tabla, etc.); nombres que expliquen propósito.
- **Archivos nuevos acotados** (solo lo que exigen los hallazgos; la separación completa en capas es H-API-08): `api/app/config.py`, `api/app/security.py`, `api/app/schemas.py`, `api/app/repository.py`, `api/app/uploads.py`.
- **Orden propuesto**: H-API-05 → H-API-02 → H-API-03 → H-API-04 → H-API-01. H-API-01 quedó al final por requerir acuerdo de token con auth; el acuerdo fue confirmado antes de implementar. La dependencia conserva la forma `{"username","role"}`, así H-API-03 mantiene su uso de `resolve_owner`.

---

### H-API-01 — Token Base64 con secreto embebido (alta, Vulnerabilidad)

**Hallazgo**: [HALLAZGOS.md](./HALLAZGOS.md) fila H-API-01. Evidencia: `api/app/main.py:14`, `api/app/main.py:19-22`, `api/tests/test_api.py:10-12`.

**Problema**: el token es `Base64(usuario|rol|exp|secreto)`; el secreto está en el código y en las pruebas. Quien lo conozca fabrica un token con cualquier usuario y rol. No se verifican firma, emisor ni audiencia.

**Cambio propuesto (verificación real de JWT)**:
- `api/app/security.py`: `decode_access_token(token, settings) -> Identity` que verifica **firma, `iss`, `aud` y `exp`** (`require=["exp","iss","aud","sub"]`) con algoritmo fijo (`JWT_ALGORITHM = "HS256"`, nunca tomado del encabezado del token). `Identity` es un modelo Pydantic (`username` desde `sub`, `role`).
- `api/app/config.py`: `Settings` (Pydantic) leído de `JWT_SECRET`, `JWT_ISSUER`, `JWT_AUDIENCE`. **Sin valor por defecto para el secreto**: si falta, la app falla al arrancar con mensaje claro. Se elimina `LEGACY_SECRET`.
- `legacy_identity` pasa a `current_identity` con guard clauses: sin cabecera `Bearer` → 401; token inválido o expirado → 401 con `detail` genérico (`"Invalid or expired token"`) y `WWW-Authenticate: Bearer`. El motivo detallado va solo al log del servidor (nunca el token). Esto elimina el `str(error)` de `api/app/main.py:26` por necesidad del reemplazo; **el resto de H-API-06 (`backend_health`) no se toca**.
- **Dependencia nueva (justificada)**: `PyJWT==2.15.1`, aprobada para validar firma y claims sin implementar criptografía propia. `pip-audit` no reportó advisories para PyJWT; sí reportó 10 advisories preexistentes en `starlette==0.50.0`, fuera del alcance.
- **Coordinación con otro componente**: el usuario confirmó que auth está coordinado fuera de este cambio y aprobó el contrato propuesto: HS256; claims `sub`, `role`, `exp`, `iss`, `aud`; configuración `JWT_SECRET`, `JWT_ISSUER`, `JWT_AUDIENCE`. No se inspeccionó ni modificó código de auth/web.
- `compose.yaml` ahora requiere las tres variables de entorno para el servicio API, sin defaults ni secretos versionados. Para pruebas, `api/tests/conftest.py` fija valores aislados antes de importar `app.main`, porque `app = create_app()` se evalúa al importar.

**Archivos tocados**: `api/app/main.py`, `api/app/security.py`, `api/app/config.py`, `api/requirements.txt`, `api/tests/conftest.py`, `api/tests/helpers.py`, `api/tests/test_api.py`, `api/tests/test_authentication.py`, `compose.yaml`, `README.md`, `docs/ENDPOINTS.md`, `docs/TESTING.md`, `HALLAZGOS.md` y este plan.

**Caracterización antes del cambio**: `python tools/lab.py test api` pasó antes de tocar el código (65 pruebas, 100 % de cobertura global); caracterizaba rutas válidas, falta de autorización, token inválido y aislamiento de owner.
**Comportamiento deseado verificado**: firma incorrecta, issuer/audience incorrectos, claims requeridos ausentes, expiración, `alg: none` y formato Base64 legado → 401 genérico; la app no arranca sin variables de autenticación; identidad válida conserva las rutas y autorización por owner. Los helpers generan JWT de prueba con clave aislada.

---

### H-API-02 — SQL construido por concatenación (alta, Vulnerabilidad)

**Hallazgo**: fila H-API-02. Evidencia: `api/app/main.py:70`, `:84`, `:87`, `:93`.

**Problema**: `owner`, `title`, `description`, `status` y `priority` del cliente se concatenan en el SQL (inyección y fallo con comillas).

**Cambio propuesto (SQL parametrizado + modelos Pydantic)**:
- `api/app/repository.py`: `TaskRepository(connection)` con `list_by_owner(owner)`, `create(new_task)`, `get_by_id(task_id)` y `status_priority_by_owner(owner)`, todos con placeholders `?` y tupla de parámetros. El `CREATE TABLE` y el *seed* también usan constantes y parámetros. Ningún SQL dentro de las rutas (GOOD_PRACTICES: capas).
- `api/app/schemas.py`: `TaskCreate` (`title: str = ""`, `description: str = ""`, `status: str = "TODO"`, `priority: str = "MEDIUM"`, `owner: str | None = None`) y `TaskResponse` (`id,title,description,status,owner,priority,createdAt`, con alias `createdAt`). Las rutas dejan de usar `dict[str, Any]` y declaran `response_model`. Se conservan los valores por defecto observados.
- Una sola función `row_to_task` (reemplaza `as_task`) y un único método de lectura, eliminando la duplicación de columnas (líneas 70 y 87).
- **Decisión pendiente**: restringir `status`/`priority` a `Enum` (`TODO, IN_PROGRESS, DONE, ARCHIVED` / `HIGH, MEDIUM, LOW`) y límites de longitud devolvería 422 ante valores hoy aceptados; no se sabe qué envía `web` (fuera de AMBITO). Por defecto se mantienen como `str` y se registra el riesgo.

**Archivos a tocar**: `api/app/main.py`, `api/app/repository.py` (nuevo), `api/app/schemas.py` (nuevo), `api/tests/test_tasks_characterization.py` (nuevo).

**Prueba de caracterización antes de tocar** (verde ahora y después): `GET /api/tasks` devuelve las 2 tareas sembradas de `student` con las claves exactas; `POST /api/tasks` con valores por defecto → 201 con `owner == "student"`, `status == "TODO"`, `priority == "MEDIUM"`; `GET /api/summary` de `student` → `total 2`, `highPriorityOpen 1`, `byStatus {"TODO":1,"IN_PROGRESS":1}`.
**Comportamiento deseado (rojo→verde)**: un título con comilla simple (`O'Brien`) hoy falla y debe guardarse literal; un título `x'); DROP TABLE tasks;--` se guarda literal y la tabla sigue existiendo; `owner` con `' OR '1'='1` no devuelve tareas ajenas (el rechazo con 403 lo define H-API-03).

---

### H-API-03 — El cliente puede consultar y crear tareas de otro `owner` (alta, Vulnerabilidad)

**Hallazgo**: fila H-API-03. Evidencia: `api/app/main.py:69`, `:83`, `:92`, `:94`.

**Problema**: `owner` (query o body) prevalece sobre la identidad: se lee listado y resumen de otro usuario y se crean tareas a su nombre.

**Cambio propuesto (autorización ligada a la identidad)**:
- Función única `resolve_owner(identity, requested_owner) -> str` en `api/app/security.py`: devuelve el `username` de la identidad; si `requested_owner` viene informado y es distinto → `HTTPException(403, "Forbidden")`. Es la única fuente de `owner` para `list_tasks`, `create_task` y `summary` (elimina la duplicación de líneas 69, 83 y 92) y todas las consultas usan ese valor (GOOD_PRACTICES: `identity["username"]`, nunca el `owner` del cliente).
- El parámetro `owner` de query y el campo `owner` del body se siguen **aceptando** para no romper clientes que envían su propio usuario; solo se rechaza un valor ajeno. `summary` responde `owner` = identidad.
- **Decisión pendiente**: ¿403 explícito (propuesto) o ignorar silenciosamente el valor ajeno? ¿Algún rol (p. ej. trainer) puede ver otros `owner`? GOOD_PRACTICES no lo define y no se asume; por defecto no hay excepción por rol.

**Archivos a tocar**: `api/app/main.py`, `api/app/security.py`, `api/tests/test_authorization.py` (nuevo).

**Prueba de caracterización antes de tocar** (verde ahora): `student` sin `owner` ve 2 tareas; `trainer` sin `owner` ve 1; `summary` de `student` como arriba; con `owner=student` explícito sigue funcionando.
**Comportamiento deseado (rojo→verde)**: `student` con `?owner=trainer` en `/api/tasks` y `/api/summary` → 403; `POST /api/tasks` con `owner: "trainer"` → 403 y no inserta; sin `owner` la tarea se crea con la identidad.

---

### H-API-04 — Subida con `upload.filename` sin normalizar ni límites (alta, Vulnerabilidad)

**Hallazgo**: fila H-API-04. Evidencia: `api/app/main.py:109-112`.

**Problema**: el nombre del cliente se concatena al directorio (path traversal, sobrescritura), sin límite de extensión ni de tamaño, con lectura completa en memoria y ruta interna expuesta en `storedAt`.

**Cambio propuesto (carga segura de archivos)**:
- `api/app/uploads.py`, funciones pequeñas: `sanitize_filename(raw)` (solo `Path(raw).name`, caracteres `[A-Za-z0-9._-]`, resto → `_`; vacío o solo puntos → 400); `validate_extension(name)` contra `ALLOWED_UPLOAD_EXTENSIONS`; `save_limited(upload, target)` que escribe por bloques de `UPLOAD_CHUNK_BYTES` y corta al superar `MAX_UPLOAD_BYTES` (borra el parcial, 413); `ensure_inside(base, target)` (`resolve()` + `is_relative_to`) como defensa final. La ruta usa guard clauses.
- Códigos: nombre inválido 400; extensión no permitida 415; tamaño excedido 413. La respuesta de éxito mantiene `owner,fileName,storedAt,size`; `fileName` pasa a ser el nombre **normalizado** (idéntico al original cuando ya era seguro, como `requirements.txt`).
- **Decisiones pendientes**: (a) lista de extensiones (propuesta `.txt, .md, .pdf, .docx`; GOOD_PRACTICES no la fija); (b) tope (propuesta 5 MiB); (c) `storedAt` sigue devolviendo la ruta unida como hoy, para preservar el contrato; devolver solo el nombre es un cambio de contrato que requiere acuerdo con web. Queda como riesgo residual.
- Sin dependencia nueva; `python-multipart` se actualiza en H-API-05.

**Archivos a tocar**: `api/app/main.py`, `api/app/uploads.py` (nuevo), `api/app/config.py`, `api/tests/test_uploads.py` (nuevo).

**Prueba de caracterización antes de tocar** (verde ahora): subir `requirements.txt` → 201, claves `owner,fileName,storedAt,size`, `size == len(contenido)` y el archivo existe en el directorio de subida (se amplía `test_uploads_requirement`).
**Comportamiento deseado (rojo→verde)**: `../../evil.txt` queda dentro del directorio de subida; nombre vacío o inválido → 400; `.exe`/`.html` → 415; archivo de `MAX_UPLOAD_BYTES + 1` → 413 y no queda archivo; nada se escribe fuera del directorio (verificado con `tmp_path`).

---

### H-API-05 — Dependencias con advisories (media, Vulnerabilidad)

**Hallazgo**: fila H-API-05. Evidencia: `api/requirements.txt:4`, `:5`, `api/app/main.py:118`.

**Problema y análisis** (fuentes públicas; confirmar con Dependency Review/`pip-audit` al implementar):
- `urllib3 2.5.0`: CVE-2025-66418 y CVE-2025-66471 (corregidos en 2.6.0) y CVE-2026-21441 (corregido en 2.6.3). Exposición acotada a `backend_health`.
- `python-multipart 0.0.21`: GHSA-wp53-j4wj-2cfg (path traversal con opciones no predeterminadas `UPLOAD_DIR` + `UPLOAD_KEEP_FILENAME`; corregido en 0.0.22; esta API no usa esas opciones) y CVE-2026-42561 (DoS por cabeceras de parte sin límite; corregido en 0.0.27), que sí afecta a `/api/requirements`. La fila de HALLAZGOS.md dejaba este advisory por confirmar; aquí queda identificado.

**Cambio propuesto**: `urllib3 >= 2.6.3` y `python-multipart >= 0.0.27`, fijando en `api/requirements.txt` una versión exacta validada (el índice muestra 2.8.0 y 0.0.33 como últimas; elegir la más reciente compatible con `fastapi==0.128.2` que pase pruebas y `pip-audit`). Sin dependencias nuevas de producto; no se silencia ningún advisory.

**Archivos a tocar**: `api/requirements.txt`.

**Prueba de caracterización antes de tocar**: ejecutar la suite actual (4 pruebas) y `pip-audit -r api/requirements.txt` como línea base (resultados reales en `docs/TESTING.md`); añadir una prueba de humo de `GET /api/backend-health` con `urllib3.PoolManager` simulado (éxito → `status 200`, claves `requestedBy,status,body`) y una subida multipart. Tras actualizar: misma suite verde y `pip-audit` sin los advisories listados. `pip-audit` es una herramienta de verificación puntual, no una dependencia del producto.

---

### Riesgos y pendientes del plan api

1. Revisión del plan: aprobación registrada al inicio de la sección; el usuario aprobó explícitamente la propuesta H-API-01 y confirmó coordinación con auth el 03/11/2026.
2. Contrato de token: acordado para esta integración como HS256 con `sub`, `role`, `exp`, `iss` y `aud`, usando `JWT_SECRET`, `JWT_ISSUER` y `JWT_AUDIENCE`.
3. Variables de despliegue: incluidas como referencias obligatorias en `compose.yaml`; la sintaxis YAML pasó, pero no se pudo ejecutar `docker compose config` porque Docker CLI no está instalado.
4. Decisiones de otros hallazgos que siguen pendientes: roles con acceso a otros `owner`; Enum de `status`/`priority`; extensiones y tamaño máximo; `storedAt` con ruta.
5. `pip-audit` posterior: quedan 10 avisos de `starlette 0.50.0` (dependencia transitiva de `fastapi==0.128.2`, correcciones desde 1.0.1 hasta 1.3.1); no está en H-API-05 y no se tocó. Requiere evaluar una actualización de `fastapi`/`starlette`: **Pendiente** (hallazgo nuevo por registrar si se aprueba). Cobertura del diff por método de línea/rama de `coverage`: ver «Registro de ejecuciones»; el informe formal va a `docs/TESTING.md`.
6. H-API-06 sin aprobar: tras H-API-01 sigue pendiente el `str(error)` y el cuerpo remoto que devuelve `backend_health` (`api/app/main.py:80-81`); el 401 de autenticación ya es genérico por el cambio acotado de H-API-01.

---

### Registro de ejecuciones (componente api)

Comando de regresión: `python tools/lab.py test api` (equivale a `pytest --cov=app --cov-fail-under=85` con cwd `api/`; Python 3.13.15, `api/.venv`). Línea base antes de cualquier cambio: 4 pruebas pasan, cobertura de `app` 91 %. `pip-audit` se instaló en `api/.venv` solo para verificar (no está en `requirements.txt`).

| # | IDs | Ejecución | Antes del cambio | Después del cambio |
|---|---|---|---|---|
| 1 | H-API-05 | `pytest` (humo: `backend-health` simulado y subida multipart, `api/tests/test_dependencies_smoke.py`) | 6 pasan (4 existentes + 2 nuevas) | 6 pasan |
| 2 | H-API-05 | `pip-audit -r api/requirements.txt` | 11 avisos en `python-multipart 0.0.21` (6) y `urllib3 2.5.0` (5), más 10 de `starlette` | 0 en `python-multipart 0.0.33` y `urllib3 2.8.0`; quedan 10 de `starlette` |
| 3 | H-API-02 | `pytest api/tests/test_tasks_characterization.py` | 5 caracterización pasan; 4 de corrección fallan (apóstrofo, literal `DROP TABLE`, filtro `owner` inyectable en `/api/tasks` y `/api/summary`) | 9 pasan; suite completa 15 pasan |
| 4 | H-API-03 | `pytest api/tests/test_authorization.py` | 2 caracterización pasan; 4 de corrección fallan (`owner` ajeno → 403 en lecturas y creación, detalle genérico) | 6 pasan; suite completa 21 pasan |
| 5 | H-API-04 | `pytest api/tests/test_uploads.py` | 7 pasan; 13 de corrección fallan (traversal, caracteres, nombres vacíos, extensiones, tamaño). La ejecución roja escribió `C:\tmp\evil.txt` fuera de `tmp_path` (demostración del hallazgo); se eliminó | 21 pasan; suite completa 42 pasan |
| 6 | H-API-02, 03, 04, 05 | `python tools/lab.py test api` final | — | 42 pasan; cobertura total 97,94 % (`main.py` 95 %; `config`, `repository`, `schemas`, `security` y `uploads` 100 %); gate 85 % cumplido |
| 7 | H-API-01 | `python tools/lab.py test api` | 65 pasan; cobertura total 100 % | 85 pasan; cobertura total 100 %; gate 85 % cumplido |
| 8 | H-API-01 | `api\.venv\Scripts\pip-audit.exe -r api\requirements.txt` | — | Código 1: 10 advisories de `starlette==0.50.0`; ningún advisory reportado para `PyJWT==2.15.1` |
| 9 | H-API-01 | `api\.venv\Scripts\python.exe -c "import yaml; yaml.safe_load(open('compose.yaml', encoding='utf-8'))"` | — | YAML válido; validación Compose no disponible porque Docker CLI no está instalado |

La última ejecución cubrió 211/211 statements y 18/18 branches del código `app`. No se redujo el gate. Se conservaron warnings existentes de deprecación de FastAPI/Starlette.

### Desviaciones del plan

- **H-API-01**: implementado localmente después de recibir aprobación explícita del contrato y confirmación de coordinación con auth. No se modificó código de auth/web. El formato Base64 legado se rechaza; la revisión humana de los cambios sigue pendiente.
- **H-API-05**: se fijaron `urllib3==2.8.0` y `python-multipart==0.0.33` (el plan indicaba mínimos 2.6.3 y 0.0.27); `pip-audit` mostró correcciones de `python-multipart` hasta 0.0.31, por lo que 0.0.27 no bastaba.
- **H-API-02**: no se creó `status_priority_by_owner`; el resumen usa `list_by_owner` y `summarize_tasks` (función a nivel de módulo en `api/app/main.py`) para evitar una consulta duplicada. Se tipó también la respuesta de `/api/summary` (`TaskSummary`).
- **H-API-04**: se añadió el modelo `UploadResponse` (api/app/schemas.py) para no dejar `dict[str, Any]` en la ruta; el contrato JSON no cambia. Limitación residual: Starlette recibe y almacena temporalmente el cuerpo multipart completo antes de que el tope de `MAX_UPLOAD_BYTES` se aplique en el handler.
- `api/tests/helpers.py` centraliza tokens JWT de prueba; `api/tests/conftest.py` configura valores aislados antes de importar `app.main`.
- `api/tests/test_api.py` migró de tokens Base64 a JWT de prueba; `api/tests/test_authentication.py` cubre la validación y el rechazo de tokens inválidos.

### Revisión local del diff (IA, 02/11/2026; no es aprobación humana)

Evidencia: `git diff main -- api/` más archivos nuevos de `git status --short`. Las ramas locales muestran solo `main` (no existe `day1/prompting`) y los cambios están sin commit, por lo que el diff equivale al árbol de trabajo. Resultado: H-API-02 y H-API-05 verificados como `Resuelto`; H-API-03 `Resuelto` con la salvedad de depender de H-API-01 (identidad fabricable); **H-API-04 devuelto a `Pendiente`** por residuales detallados en su fila de HALLAZGOS.md. Aprobación humana de la revisión: **Pendiente**.

### Implementación local H-API-01 (03/11/2026)

La rama actual es `day1/prompting`. `python tools/lab.py test api` pasó con 85 pruebas y cobertura global del 100 %. `pip-audit` informó 10 advisories existentes de Starlette; no se ocultaron ni corrigieron fuera de alcance. No se creó PR remoto ni se hizo push conforme al cierre local del Día 1. La revisión humana de los cambios aún está pendiente.
