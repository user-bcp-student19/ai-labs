# ReqFlow — Contratos HTTP

## API (`api/`)

### Estado del contrato

- **Contrato observado**: este documento describe las rutas, modelos y respuestas de la implementación actual de `api/app/main.py`, `api/app/schemas.py`, `api/app/security.py` y `api/app/uploads.py`. Los ejemplos de respuesta y error se comprobaron con `TestClient`; las llamadas a `backend-health` usaron una respuesta upstream simulada.
- **Contrato acordado**: API espera un JWT firmado con HS256 y claims `sub`, `role`, `exp`, `iss` y `aud`, coordinado con el emisor auth. `JWT_SECRET`, `JWT_ISSUER` y `JWT_AUDIENCE` son obligatorios; no se aceptan tokens del formato Base64 legado.
- **Riesgos pendientes**: H-API-04 está Pendiente: `storedAt` expone una ruta del servidor, archivos con el mismo nombre pueden sobrescribirse entre usuarios, el límite se aplica después de que Starlette recibe el multipart y nombres muy largos pueden causar 500. Consultar [HALLAZGOS.md](../HALLAZGOS.md) y [PLAN.md](../PLAN.md).

Base local: `http://localhost:8000` (README.md). Todas las rutas de esta API requieren `Authorization: Bearer <access-token>`. La API valida la firma HS256 y los claims `exp`, `iss`, `aud`, `sub` y `role`; `sub` se mapea a `username`. Auth debe emitir tokens compatibles con este contrato.

```http
Authorization: Bearer <access-token-returned-by-auth>
```

En los ejemplos HTTP siguientes, reemplaza `<access-token-returned-by-auth>` por el valor devuelto por el login. En cada endpoint, los cuerpos de error son los de FastAPI/Pydantic que se observaron. Un 500 no gestionado usa por defecto el cuerpo `text/plain` `Internal Server Error` de Starlette; un servidor/configuración puede sustituirlo. FastAPI responde 405 si se usa un método no definido para la ruta; `/api/tasks` admite tanto `GET` como `POST`.

---

## `GET /api/tasks`

### 1. Qué hace

Lista las tareas del usuario autenticado.

### 2. Autenticación

Requerida. Enviar `Authorization: Bearer <token>` como se explica arriba.

### 3. Request

No tiene cuerpo. `owner` es un parámetro de query opcional; si se omite o está vacío se usa el usuario del token. Si tiene un valor distinto del usuario autenticado, la solicitud se rechaza.

| campo/parámetro | tipo | obligatorio | descripción |
|---|---|---:|---|
| `owner` (query) | string | No | Usuario cuyos datos se piden. Debe ser igual a `username` del token; omitido o vacío usa esa identidad. |

Ejemplo completo:

```http
GET /api/tasks?owner=student HTTP/1.1
Host: localhost:8000
Authorization: Bearer <access-token-returned-by-auth>
```

### 4. Response exitosa

**200 OK**, arreglo de tareas (puede ser vacío).

| campo | tipo | descripción |
|---|---|---|
| `id` | integer | Identificador de la tarea. |
| `title` | string | Título. |
| `description` | string | Descripción. |
| `status` | string | Estado almacenado. |
| `owner` | string | Usuario propietario. |
| `priority` | string | Prioridad almacenada. |
| `createdAt` | string | Fecha y hora SQLite en formato `YYYY-MM-DD HH:MM:SS`. |

Ejemplo completo:

```json
[
  {
    "id": 1,
    "title": "Refactor login",
    "description": "Separar responsabilidades en frontend",
    "status": "TODO",
    "owner": "student",
    "priority": "HIGH",
    "createdAt": "2026-11-02 22:15:23"
  },
  {
    "id": 2,
    "title": "Review API",
    "description": "Revisar seguridad de endpoints",
    "status": "IN_PROGRESS",
    "owner": "student",
    "priority": "MEDIUM",
    "createdAt": "2026-11-02 22:15:23"
  }
]
```

### 5. Respuestas de error

| código | cuándo ocurre |
|---|---|
| 401 Unauthorized | Falta la cabecera o el token no es válido, expiró o no cumple la configuración de emisor y audiencia. Respuesta genérica y desafío `WWW-Authenticate: Bearer`. |
| 403 Forbidden | `owner` no vacío no coincide con la identidad del token. |
| 405 Method Not Allowed | Se usa un método distinto de `GET` y `POST` para la ruta `/api/tasks`. |
| 500 Internal Server Error | Error interno no gestionado (por ejemplo, fallo de SQLite); el detalle depende del servidor. |

Ejemplos de cuerpo:

```json
{"detail":"Invalid or expired token"}
```

```json
{"detail":"Forbidden"}
```

```json
{"detail":"Method Not Allowed"}
```

```text
Internal Server Error
```

### 6. Notas de seguridad

- La consulta filtra por el usuario devuelto por `resolve_owner`; el cliente no puede seleccionar otro `owner` con este endpoint.
- La identidad se obtiene de un JWT cuya firma, expiración, emisor y audiencia se validan antes de autorizar la consulta.
- El SQL de lectura usa parámetros SQLite, no concatena el valor de `owner`.

---

## `POST /api/tasks`

### 1. Qué hace

Crea una tarea asociada al usuario autenticado y devuelve la tarea creada.

### 2. Autenticación

Requerida. Enviar `Authorization: Bearer <token>` como se explica arriba.

### 3. Request

El cuerpo JSON es obligatorio, pero todas sus propiedades tienen valores por defecto y pueden omitirse. `owner` puede omitirse o ser `null`; si se envía un nombre distinto de la identidad, se rechaza.

| campo/parámetro | tipo | obligatorio | descripción |
|---|---|---:|---|
| cuerpo | objeto JSON | Sí | Objeto `TaskCreate`; `{}` también es válido. |
| `title` | string | No | Título; por defecto `""`. |
| `description` | string | No | Descripción; por defecto `""`. |
| `status` | string | No | Estado; por defecto `"TODO"`. |
| `priority` | string | No | Prioridad; por defecto `"MEDIUM"`. |
| `owner` | string o null | No | Si coincide con la identidad, se acepta; si se omite o es null se usa la identidad. Un valor distinto responde 403. |

Ejemplo completo:

```http
POST /api/tasks HTTP/1.1
Host: localhost:8000
Authorization: Bearer <access-token-returned-by-auth>
Content-Type: application/json

{
  "title": "Review API",
  "description": "Check required changes",
  "status": "TODO",
  "priority": "HIGH",
  "owner": "student"
}
```

### 4. Response exitosa

**201 Created**. Devuelve un objeto tarea con los mismos campos que `GET /api/tasks`.

| campo | tipo | descripción |
|---|---|---|
| `id` | integer | Identificador asignado. |
| `title` | string | Título guardado. |
| `description` | string | Descripción guardada. |
| `status` | string | Estado guardado. |
| `owner` | string | Identidad autenticada. |
| `priority` | string | Prioridad guardada. |
| `createdAt` | string | Fecha y hora SQLite en formato `YYYY-MM-DD HH:MM:SS`. |

Ejemplo completo:

```json
{
  "id": 4,
  "title": "Review API",
  "description": "Check required changes",
  "status": "TODO",
  "owner": "student",
  "priority": "HIGH",
  "createdAt": "2026-11-02 22:15:23"
}
```

### 5. Respuestas de error

| código | cuándo ocurre |
|---|---|
| 401 Unauthorized | Falta la cabecera o el token no es válido, expiró o no cumple la configuración de emisor y audiencia. Respuesta genérica y desafío `WWW-Authenticate: Bearer`. |
| 403 Forbidden | `owner` enviado no coincide con la identidad del token. |
| 422 Unprocessable Entity | Falta el cuerpo JSON o un campo tiene un tipo incompatible con el modelo (por ejemplo, `title` numérico). |
| 405 Method Not Allowed | Se usa un método distinto de `GET` y `POST` para la ruta `/api/tasks`. |
| 500 Internal Server Error | Error interno no gestionado, por ejemplo fallo de SQLite; el detalle depende del servidor. |

Ejemplos de cuerpo:

```json
{"detail":"Invalid or expired token"}
```

```json
{"detail":"Forbidden"}
```

```json
{"detail":"Method Not Allowed"}
```

```json
{
  "detail": [
    {
      "type": "string_type",
      "loc": ["body", "title"],
      "msg": "Input should be a valid string",
      "input": 5
    }
  ]
}
```

```text
Internal Server Error
```

### 6. Notas de seguridad

- El `owner` persistido se obtiene de la identidad; el cliente no puede crear tareas para otro usuario.
- Los valores del `INSERT` y de la lectura posterior se pasan como parámetros SQLite.
- `TaskCreate` comprueba tipos, pero no restringe longitudes ni los valores permitidos de `status`/`priority`.
- La identidad de la tarea procede del token validado; el cliente no puede sustituirla enviando otro propietario.

---

## `GET /api/summary`

### 1. Qué hace

Resume el número de tareas y las agrupa por estado para el usuario autenticado.

### 2. Autenticación

Requerida. Enviar `Authorization: Bearer <token>` como se explica arriba.

### 3. Request

No tiene cuerpo. El parámetro `owner` opcional debe coincidir con la identidad autenticada; si se omite o está vacío se usa esa identidad.

| campo/parámetro | tipo | obligatorio | descripción |
|---|---|---:|---|
| `owner` (query) | string | No | Usuario a resumir; solo se permite el `username` del token. |

Ejemplo completo:

```http
GET /api/summary?owner=student HTTP/1.1
Host: localhost:8000
Authorization: Bearer <access-token-returned-by-auth>
```

### 4. Response exitosa

**200 OK**.

| campo | tipo | descripción |
|---|---|---|
| `owner` | string | Identidad autenticada que se resumió. |
| `total` | integer | Total de tareas del usuario. |
| `byStatus` | objeto de string a integer | Conteo de tareas por cada estado presente. |
| `highPriorityOpen` | integer | Tareas `HIGH` cuyo estado no es `DONE` ni `ARCHIVED`. |

Ejemplo completo:

```json
{
  "owner": "student",
  "total": 3,
  "byStatus": {
    "TODO": 2,
    "IN_PROGRESS": 1
  },
  "highPriorityOpen": 2
}
```

### 5. Respuestas de error

| código | cuándo ocurre |
|---|---|
| 401 Unauthorized | Falta la cabecera o el token no es válido, expiró o no cumple la configuración de emisor y audiencia. Respuesta genérica y desafío `WWW-Authenticate: Bearer`. |
| 403 Forbidden | `owner` no vacío no coincide con la identidad del token. |
| 405 Method Not Allowed | Se usa un método HTTP distinto de `GET` para esta ruta. |
| 500 Internal Server Error | Error interno no gestionado; el detalle depende del servidor. |

Ejemplos de cuerpo:

```json
{"detail":"Invalid or expired token"}
```

```json
{"detail":"Forbidden"}
```

```json
{"detail":"Method Not Allowed"}
```

```text
Internal Server Error
```

### 6. Notas de seguridad

- El `owner` del resultado y el filtro de tareas proceden de `resolve_owner`, no de un valor ajeno enviado por el cliente.
- El conteo se calcula sobre las tareas recuperadas del repositorio y la identidad derivada del token validado.

---

## `POST /api/requirements`

### 1. Qué hace

Guarda un archivo de requisitos asociado a la identidad autenticada y devuelve sus metadatos.

### 2. Autenticación

Requerida. Enviar `Authorization: Bearer <token>` como se explica arriba.

### 3. Request

El cuerpo es `multipart/form-data` y debe incluir un archivo en el campo `file`.

| campo/parámetro | tipo | obligatorio | descripción |
|---|---|---:|---|
| `file` | archivo binario (`UploadFile`, multipart) | Sí | Nombre de archivo y contenido. Extensiones admitidas, sin distinguir mayúsculas: `.txt`, `.md`, `.pdf`, `.docx`. Máximo de contenido aceptado por el handler: 5 MiB. |

Ejemplo completo:

```http
POST /api/requirements HTTP/1.1
Host: localhost:8000
Authorization: Bearer <access-token-returned-by-auth>
Content-Type: multipart/form-data; boundary=----ReqFlowBoundary

------ReqFlowBoundary
Content-Disposition: form-data; name="file"; filename="requirements.txt"
Content-Type: text/plain

Login requirement
------ReqFlowBoundary--
```

### 4. Response exitosa

**201 Created**.

| campo | tipo | descripción |
|---|---|---|
| `owner` | string | Usuario autenticado. |
| `fileName` | string | Nombre normalizado usado en el almacenamiento. |
| `storedAt` | string | Ruta del servidor donde se guardó el archivo. |
| `size` | integer | Bytes escritos. |

Ejemplo completo con el directorio por defecto `./uploads` (la ruta real depende del directorio de trabajo y de `WORKSHOP_UPLOAD_DIR`):

```json
{
  "owner": "student",
  "fileName": "requirements.txt",
  "storedAt": "./uploads/requirements.txt",
  "size": 17
}
```

### 5. Respuestas de error

| código | cuándo ocurre |
|---|---|
| 400 Bad Request | El nombre está vacío o consiste solo en puntos. |
| 401 Unauthorized | Falta la cabecera o el token no es válido, expiró o no cumple la configuración de emisor y audiencia. Respuesta genérica y desafío `WWW-Authenticate: Bearer`. |
| 413 Payload Too Large | El contenido leído por el handler supera 5 MiB. |
| 415 Unsupported Media Type | La extensión no está en la lista permitida o falta una extensión reconocida. |
| 400 Bad Request | El cuerpo multipart está mal formado, por ejemplo, falta el boundary. |
| 422 Unprocessable Entity | Falta el campo `file` o el multipart no satisface la forma esperada. |
| 405 Method Not Allowed | Se usa un método HTTP distinto de `POST` para esta ruta. |
| 500 Internal Server Error | Error de filesystem u otro error interno no gestionado; por ejemplo, un nombre de archivo excesivamente largo puede exceder el límite del sistema. El detalle depende del servidor. |

Ejemplos de cuerpo:

```json
{"detail":"Invalid file name"}
```

```json
{"detail":"Missing boundary in multipart."}
```

```json
{"detail":"Invalid or expired token"}
```

```json
{"detail":"File too large"}
```

```json
{"detail":"Unsupported file type"}
```

```json
{"detail":"Method Not Allowed"}
```

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "file"],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

```text
Internal Server Error
```

### 6. Notas de seguridad

- Se normaliza el nombre, se filtran extensiones y se comprueba que la ruta queda bajo el directorio de subidas.
- El archivo se escribe por bloques y el handler elimina el parcial cuando detecta más de 5 MiB. Starlette ya recibió el multipart antes de aplicar ese límite; no equivale a un límite temprano de tamaño de request.
- El mismo nombre apunta al mismo archivo, independientemente del usuario: una subida posterior puede sobrescribirlo.
- `storedAt` expone una ruta interna del servidor. Estos riesgos están pendientes en H-API-04.
- El `owner` de la respuesta es la identidad obtenida del token validado.

---

## `GET /api/backend-health`

### 1. Qué hace

Consulta el endpoint de salud del servicio de autenticación y devuelve el resultado upstream junto con el usuario solicitante.

### 2. Autenticación

Requerida. Enviar `Authorization: Bearer <token>` como se explica arriba.

### 3. Request

No tiene cuerpo ni parámetros. El destino se configura con `AUTH_HEALTH_URL`; si no se define, usa `http://localhost:8080/q/health`.

| campo/parámetro | tipo | obligatorio | descripción |
|---|---|---:|---|
| `AUTH_HEALTH_URL` (variable de entorno del servidor) | URL string | No | URL consultada por la API; no es un parámetro enviado por el cliente. |

Ejemplo completo:

```http
GET /api/backend-health HTTP/1.1
Host: localhost:8000
Authorization: Bearer <access-token-returned-by-auth>
```

### 4. Response exitosa

**200 OK** tanto si la consulta upstream responde como si lanza una excepción capturada.

| campo | tipo | descripción |
|---|---|---|
| `requestedBy` | string | Usuario autenticado. |
| `status` | integer | Código HTTP upstream; vale `0` si la consulta lanza una excepción. No es el código HTTP de esta respuesta. |
| `body` | string | Cuerpo upstream decodificado como UTF-8; ante excepción, texto de la excepción. |

Ejemplo completo de respuesta upstream exitosa:

```json
{
  "requestedBy": "student",
  "status": 200,
  "body": "{\"status\":\"UP\"}"
}
```

Ejemplo completo cuando la llamada simulada lanza `RuntimeError("upstream unavailable")`:

```json
{
  "requestedBy": "student",
  "status": 0,
  "body": "upstream unavailable"
}
```

### 5. Respuestas de error

| código | cuándo ocurre |
|---|---|
| 401 Unauthorized | Falta la cabecera o el token no es válido, expiró o no cumple la configuración de emisor y audiencia. Respuesta genérica y desafío `WWW-Authenticate: Bearer`. |
| 405 Method Not Allowed | Se usa un método HTTP distinto de `GET` para esta ruta. |

Los errores de conexión upstream no cambian el código de respuesta de la API a error: se representan con HTTP 200 y `status: 0`.

Ejemplo de cuerpo:

```json
{"detail":"Invalid or expired token"}
```

```json
{"detail":"Method Not Allowed"}
```

### 6. Notas de seguridad

- El endpoint permite que la configuración del servidor determine la URL consultada; debe considerarse confiable y controlada por el operador. La petición no toma una URL del cliente.
- Devuelve al cliente el cuerpo upstream y el texto crudo de excepciones. El contenido puede filtrar detalles internos; H-API-06 sigue pendiente.
- No confundir `status` (código del upstream) con el estado HTTP 200 de la propia ruta.
- La llamada tiene timeout de 3 segundos.

---

## Referencias de implementación

- Rutas, dependencia de autenticación, configuración del upstream y timeout: `api/app/main.py`.
- Request/response y alias JSON `createdAt`: `api/app/schemas.py`.
- Resolución de propietario: `api/app/security.py`.
- Normalización, extensión, ruta y límite de archivos: `api/app/uploads.py`, `api/app/config.py`.
- Consultas parametrizadas: `api/app/repository.py`.
- Pruebas de contrato y casos de borde: `api/tests/test_api.py`, `api/tests/test_tasks_characterization.py`, `api/tests/test_authorization.py`, `api/tests/test_uploads.py`, `api/tests/test_dependencies_smoke.py`.
