# Contrato HTTP — API FastAPI

## Alcance y estado del contrato

Esta seccion describe el comportamiento observado en la implementacion actual
de `api/app/main.py`; no constituye un contrato aprobado para cambiar
comportamientos. La base local indicada en `README.md` es
`http://localhost:8000`. Los ejemplos de autenticación usan el placeholder
`<jwt-firmado>`; sustitúyelo por un token de prueba válido en el entorno local.

### Autenticacion observada

Las cinco operaciones de ruta requieren un Bearer JWT firmado con RS256:

```http
Authorization: Bearer <jwt-firmado>
```

La API verifica la firma RS256 con la clave pública configurada en
`AUTH_JWT_PUBLIC_KEY_PATH`, exige el issuer `workshop-auth` y la audience
`workshop-api`, y valida la expiración. También exige los claims `iat`, `sub`
y `role`. Credenciales ausentes o inválidas producen HTTP 401. El placeholder
no es un token utilizable ni contiene credenciales.

### Contrato acordado y preguntas abiertas

- No hay un contrato de endpoints acordado por revision humana en
  `docs/ENDPOINTS.md`; las tablas siguientes son observaciones del codigo.
- La politica aprobada para H-API-02 indica que cada usuario solo deberia leer
  y crear bajo su propia identidad, pero actualmente `GET /api/tasks`, `GET
  /api/summary` y `POST /api/tasks` permiten seleccionar `owner`. El cierre
  seguro depende de tener una identidad verificada (H-API-01).
- La API sigue implementada en `api/app/main.py`; la separacion completa de
  rutas, servicios y repositorio (H-API-05) no se refleja aun en el codigo
  observado.

## `GET /api/tasks`

### 1. Que hace

Devuelve las tareas asociadas al `owner` solicitado; si se omite o esta vacio,
usa el username extraido del token.

### 2. Autenticacion

Requiere `Authorization: Bearer <token>` como se describe arriba. Token ausente
o invalido produce HTTP 401.

### 3. Request

| Campo/parametro | Tipo | Obligatorio | Descripcion |
|---|---|---:|---|
| `owner` (query) | string | No | Owner usado como filtro. Si se omite o esta vacio, se usa el username decodificado del token. La implementacion no lo restringe a la identidad autenticada. |
| `Authorization` (header) | string | Si | Debe usar `Bearer ` seguido de un JWT firmado válido según la sección Autenticación observada. |

Ejemplo completo:

```http
GET /api/tasks?owner=student HTTP/1.1
Host: localhost:8000
Authorization: Bearer <jwt-firmado>
```

### 4. Response exitosa

HTTP **200 OK**. El cuerpo es una lista ordenada por `id`.

| Campo | Tipo | Descripcion |
|---|---|---|
| `id` | integer | Identificador de la tarea. |
| `title` | string | Titulo. |
| `description` | string | Descripcion. |
| `status` | string | Estado almacenado, por ejemplo `TODO` o `IN_PROGRESS`. |
| `owner` | string | Owner almacenado en la tarea. |
| `priority` | string | Prioridad almacenada. |
| `createdAt` | string | Fecha/hora SQLite en texto `YYYY-MM-DD HH:MM:SS` (UTC, sin sufijo de zona). |

Ejemplo observado con la base semilla:

```json
[
  {
    "id": 1,
    "title": "Refactor login",
    "description": "Separar responsabilidades en frontend",
    "status": "TODO",
    "owner": "student",
    "priority": "HIGH",
    "createdAt": "2026-10-26 21:40:32"
  },
  {
    "id": 2,
    "title": "Review API",
    "description": "Revisar seguridad de endpoints",
    "status": "IN_PROGRESS",
    "owner": "student",
    "priority": "MEDIUM",
    "createdAt": "2026-10-26 21:40:32"
  }
]
```

La fecha del ejemplo depende del instante en que se inicializa la base.

### 5. Respuestas de error

| Codigo | Cuando ocurre | Ejemplo de cuerpo |
|---:|---|---|
| 401 | Falta el header o el token no puede validarse. El detalle puede variar según el error detectado. | `{"detail":"Invalid token: invalid token"}` |
| 500 | Una excepcion interna no manejada, por ejemplo un fallo SQLite. FastAPI/Starlette responde texto plano en la configuracion actual. | `Internal Server Error` |

### 6. Notas de seguridad

- El query `owner` permite seleccionar tareas de otra identidad; H-API-02
  sigue pendiente.
- La identidad se obtiene de un JWT firmado y validado como se describe arriba
  (H-API-01). El detalle del 401 puede incluir texto de excepción (H-API-07
  pendiente).

## `POST /api/tasks`

### 1. Que hace

Crea una tarea con los valores recibidos y devuelve la fila persistida.

### 2. Autenticacion

Requiere `Authorization: Bearer <token>` como se describe arriba. Token ausente
o invalido produce HTTP 401.

### 3. Request

El body debe ser un objeto JSON. Los campos se convierten a texto mediante
`str()`; no hay validacion de enumeraciones ni de longitud en la ruta actual.

| Campo/parametro | Tipo | Obligatorio | Descripcion |
|---|---|---:|---|
| `title` (body) | valor JSON convertido a string | No | Titulo. Default: `""`. |
| `description` (body) | valor JSON convertido a string | No | Descripcion. Default: `""`. |
| `status` (body) | valor JSON convertido a string | No | Estado. Default: `"TODO"`. |
| `priority` (body) | valor JSON convertido a string | No | Prioridad. Default: `"MEDIUM"`. |
| `owner` (body) | valor JSON convertido a string | No | Owner. Default: username del token. Actualmente un valor suministrado por el cliente puede asignar otra identidad. |
| `Authorization` (header) | string | Si | Debe usar `Bearer ` seguido de un JWT firmado válido según la sección Autenticación observada. |

Ejemplo completo:

```http
POST /api/tasks HTTP/1.1
Host: localhost:8000
Authorization: Bearer <jwt-firmado>
Content-Type: application/json

{
  "title": "Document API",
  "description": "Integrate task endpoints",
  "status": "TODO",
  "priority": "HIGH",
  "owner": "student"
}
```

### 4. Response exitosa

HTTP **201 Created**.

| Campo | Tipo | Descripcion |
|---|---|---|
| `id` | integer | Identificador SQLite asignado. |
| `title` | string | Titulo persistido. |
| `description` | string | Descripcion persistida. |
| `status` | string | Estado persistido. |
| `owner` | string | Owner persistido. |
| `priority` | string | Prioridad persistida. |
| `createdAt` | string | Fecha/hora SQLite en texto `YYYY-MM-DD HH:MM:SS` (UTC, sin sufijo de zona). |

Ejemplo observado:

```json
{
  "id": 4,
  "title": "Document API",
  "description": "Integrate task endpoints",
  "status": "TODO",
  "owner": "student",
  "priority": "HIGH",
  "createdAt": "2026-10-26 21:40:32"
}
```

El ID y la fecha dependen del estado y del instante de la base.

### 5. Respuestas de error

| Codigo | Cuando ocurre | Ejemplo de cuerpo |
|---:|---|---|
| 401 | Falta el header o el token no puede validarse. | `{"detail":"Invalid token: invalid token"}` |
| 422 | Falta el body o el JSON no es un objeto. FastAPI valida el body antes de llamar a la ruta. | `{"detail":[{"type":"missing","loc":["body"],"msg":"Field required","input":null}]}` |
| 500 | Una excepcion interna no manejada, por ejemplo un error SQLite. | `Internal Server Error` |

### 6. Notas de seguridad

- Los valores del `INSERT` y la consulta de recuperación por ID usan
  parámetros enlazados (H-API-03 resuelto).
- `owner` sigue viniendo del body si se proporciona; la ruta no fuerza la
  identidad del token (H-API-02 pendiente).
- La autenticación exige un JWT firmado RS256 con issuer, audience y
  expiración válidos; no admite el token Base64 legado (H-API-01).

## `GET /api/summary`

### 1. Que hace

Calcula el total de tareas, la cantidad por estado y las tareas de prioridad
alta que no están completadas ni archivadas para un owner.

### 2. Autenticacion

Requiere `Authorization: Bearer <token>` como se describe arriba. Token ausente
o invalido produce HTTP 401.

### 3. Request

| Campo/parametro | Tipo | Obligatorio | Descripcion |
|---|---|---:|---|
| `owner` (query) | string | No | Owner del resumen. Si se omite o es vacio, se usa `username` del token. Actualmente no se restringe a la identidad autenticada. |
| `Authorization` (header) | string | Si | Debe usar `Bearer ` seguido de un JWT firmado válido según la sección Autenticación observada. |

Ejemplo completo:

```http
GET /api/summary?owner=student HTTP/1.1
Host: localhost:8000
Authorization: Bearer <jwt-firmado>
```

### 4. Response exitosa

HTTP **200 OK**.

| Campo | Tipo | Descripcion |
|---|---|---|
| `owner` | string | Owner utilizado para el filtro. |
| `total` | integer | Cantidad de tareas encontradas. |
| `byStatus` | object de string a integer | Conteo por cada valor de `status` presente. Puede ser `{}` si no hay tareas. |
| `highPriorityOpen` | integer | Tareas con `priority == "HIGH"` cuyo status no es `DONE` ni `ARCHIVED`. |

Ejemplo observado con las tareas semilla:

```json
{
  "owner": "student",
  "total": 2,
  "byStatus": {
    "TODO": 1,
    "IN_PROGRESS": 1
  },
  "highPriorityOpen": 1
}
```

### 5. Respuestas de error

| Codigo | Cuando ocurre | Ejemplo de cuerpo |
|---:|---|---|
| 401 | Falta el header o el token no puede validarse. | `{"detail":"Invalid token: invalid token"}` |
| 500 | Una excepcion interna no manejada, por ejemplo un fallo SQLite. | `Internal Server Error` |

### 6. Notas de seguridad

- El filtro de owner está parametrizado, pero el cliente puede seleccionar
  cualquier owner (H-API-02 pendiente).
- La identidad requiere un JWT firmado RS256 con issuer, audience y
  expiración válidos (H-API-01).

## `POST /api/requirements`

### 1. Que hace

Recibe y guarda un archivo de requisitos de texto en el directorio de cargas.

### 2. Autenticacion

Requiere `Authorization: Bearer <token>` como se describe arriba. Token ausente
o invalido produce HTTP 401.

### 3. Request

Usa `multipart/form-data`. El límite de contenido es 4 MiB (4 × 1024 × 1024
bytes). La extensión `.txt` se compara sin distinguir mayúsculas/minúsculas.

| Campo/parametro | Tipo | Obligatorio | Descripcion |
|---|---|---:|---|
| `file` (form-data) | archivo binario con nombre | Si | Solo admite nombre sin `/`, `\` ni `:`, sin terminación en espacio/punto, y extensión `.txt`. Tamaño máximo: 4 MiB. |
| `Authorization` (header) | string | Si | Debe usar `Bearer ` seguido de un JWT firmado válido según la sección Autenticación observada. |

Ejemplo completo con un archivo local `requirements.txt`:

```bash
curl -X POST "http://localhost:8000/api/requirements" ^
  -H "Authorization: Bearer <jwt-firmado>" ^
  -F "file=@requirements.txt;type=text/plain"
```

`curl` añade automáticamente el boundary de `multipart/form-data`.

### 4. Response exitosa

HTTP **201 Created**.

| Campo | Tipo | Descripcion |
|---|---|---|
| `owner` | string | Username extraído del token. |
| `fileName` | string | Nombre aceptado del archivo. |
| `storedAt` | string | Ruta construida con el directorio configurado y `fileName`; el formato depende del sistema operativo y la configuración. |
| `size` | integer | Cantidad de bytes guardados. |

Ejemplo observado (la ruta real depende del entorno):

```json
{
  "owner": "student",
  "fileName": "requirements.txt",
  "storedAt": "uploads\\requirements.txt",
  "size": 19
}
```

### 5. Respuestas de error

| Codigo | Cuando ocurre | Ejemplo de cuerpo |
|---:|---|---|
| 400 | Nombre inválido, extensión distinta de `.txt` o contenido mayor de 4 MiB. | `{"detail":"Invalid upload"}` |
| 401 | Falta el header o el token no puede validarse. | `{"detail":"Invalid token: invalid token"}` |
| 422 | No se envía la parte `file` o el multipart no puede validarse. | `{"detail":[{"type":"missing","loc":["body","file"],"msg":"Field required","input":null}]}` |
| 500 | Excepción no manejada al leer/escribir, por ejemplo un fallo de filesystem. | `Internal Server Error` |

### 6. Notas de seguridad

- Se rechazan separadores de ruta, nombres inválidos, extensiones no
  permitidas y cargas que exceden el límite antes de escribir (H-API-04
  resuelto).
- El código lee como máximo 4 MiB + 1 byte para detectar un exceso; el
  middleware/parser multipart procesa la petición antes de llegar al endpoint,
  y no se observa un límite global de tamaño de request configurado aquí.
- El nombre se limita mediante comprobaciones de `Path.name` y extensión; no
  se promete una normalización Unicode ni protección contra sobrescritura de
  otro `.txt` con el mismo nombre.
- La autenticación exige el JWT RS256 descrito arriba; no admite el token
  Base64 legado (H-API-01).

## `GET /api/backend-health`

### 1. Que hace

Consulta el endpoint de health del servicio de autenticación y devuelve quién
hizo la consulta, el status HTTP recibido del servicio y su cuerpo textual.

### 2. Autenticacion

Requiere `Authorization: Bearer <token>` como se describe arriba. Token ausente
o invalido produce HTTP 401.

### 3. Request

No tiene query ni body. El servicio consultado se configura mediante
`AUTH_HEALTH_URL`; si no se define, se usa
`http://localhost:8080/q/health`. La petición upstream usa timeout de 3
segundos.

| Campo/parametro | Tipo | Obligatorio | Descripcion |
|---|---|---:|---|
| `Authorization` (header) | string | Si | Debe usar `Bearer ` seguido de un JWT firmado válido según la sección Autenticación observada. |
| `AUTH_HEALTH_URL` (configuración del servidor) | URL string | No | URL consultada por el backend. Default: `http://localhost:8080/q/health`. No es un parámetro enviado por este cliente HTTP. |

Ejemplo completo:

```http
GET /api/backend-health HTTP/1.1
Host: localhost:8000
Authorization: Bearer <jwt-firmado>
```

### 4. Response exitosa

HTTP **200 OK** si la llamada upstream responde o si la ruta captura una
excepción. El `status` del cuerpo es el código HTTP upstream, no el código
HTTP de esta API.

| Campo | Tipo | Descripcion |
|---|---|---|
| `requestedBy` | string | Username extraído del token. |
| `status` | integer | Código HTTP upstream; vale `0` cuando la llamada falla o el cuerpo upstream no puede decodificarse como UTF-8. |
| `body` | string | Cuerpo upstream decodificado como UTF-8, o texto de excepción cuando falla la llamada. |

Ejemplo de respuesta con upstream simulado localmente:

```json
{
  "requestedBy": "student",
  "status": 200,
  "body": "{\"status\":\"UP\"}"
}
```

### 5. Respuestas de error

| Codigo | Cuando ocurre | Ejemplo de cuerpo |
|---:|---|---|
| 401 | Falta el header o el token no puede validarse. | `{"detail":"Invalid token: invalid token"}` |

Los errores de conexión, timeout y decodificación del upstream **no** producen
un status HTTP de error: la ruta los captura y devuelve HTTP 200 con `status`
igual a `0`, por ejemplo:

```json
{
  "requestedBy": "student",
  "status": 0,
  "body": "timed out"
}
```

El texto exacto de `body` depende de la excepción recibida. Una excepción
interna no cubierta fuera de ese bloque podría responder HTTP 500 genérico
`Internal Server Error`; no hay un formato de error propio definido para ese
caso.

### 6. Notas de seguridad

- `AUTH_HEALTH_URL` es configuración del servidor, no entrada de este endpoint.
- La ruta devuelve `str(exception)` en `body` en caso de fallo; el detalle
  puede revelar información interna (H-API-07 pendiente).
- La ruta requiere el JWT RS256 descrito en la sección Autenticación observada
  (H-API-01).

## Preguntas abiertas

- ¿Se confirmaron con el emisor y el consumidor los valores `workshop-auth` y
  `workshop-api` que valida la API?
- ¿Se eliminará `owner` de entrada o se conservará pero se ignorará? En
  `GET /api/tasks` se ignora provisionalmente; hay que verificar primero la
  identidad con el contrato JWT confirmado. `GET /api/summary` y `POST
  /api/tasks` todavía permiten seleccionar owner (H-API-02 pendiente).
- ¿Debe imponerse un límite total al request multipart además del máximo de
  4 MiB que aplica el endpoint al contenido del archivo?
- ¿Se desea un esquema estable para errores 500 y para fallos de
  `/api/backend-health`? El comportamiento observado expone detalle de
  excepción en el cuerpo de backend-health.
