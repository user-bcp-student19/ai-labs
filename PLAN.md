# Plan de correccion — API

## Alcance y seleccion

Se planifican los siete hallazgos `api` que aparecen como `Pendiente` en
`HALLAZGOS.md`:

- **H-API-01**: autenticacion por token Base64 sin firma; riesgo alto.
- **H-API-02**: el cliente elige el owner de lectura y creacion; riesgo alto.
- **H-API-03**: entradas concatenadas en SQL; riesgo alto.
- **H-API-04**: nombre y contenido de archivo sin controles visibles; riesgo
  alto.
- **H-API-05**: persistencia, rutas, reglas y serializacion acopladas; riesgo
  medio, seleccionado por ser la base para cambios revisables.
- **H-API-06**: versiones objetivo de SCA requieren verificar advisories; riesgo
  medio, seleccionado para que no se actualicen dependencias sin evidencia.
- **H-API-07**: modelos genericos, excepciones amplias y condicionales anidados;
  riesgo bajo, seleccionado para converger a las practicas de tipos y funciones
  pequenas.

## Contrato observado y decisiones pendientes

`docs/ENDPOINTS.md` no existe. Estos son contratos observados en
`api/app/main.py`; no son un contrato acordado por revision humana:

- `GET /api/tasks` acepta `owner` opcional y devuelve una lista con campos de
  tarea en camelCase para `createdAt`.
- `POST /api/tasks` acepta un objeto, responde 201 y usa valores por defecto
  para `status`, `priority` y `owner`.
- `GET /api/summary` acepta `owner` opcional y devuelve `owner`, `total`,
  `byStatus` y `highPriorityOpen`.
- `POST /api/requirements` recibe `file` y responde 201 con `owner`, `fileName`,
  `storedAt` y `size`.
- `GET /api/backend-health` responde con `requestedBy`, `status` y `body`.
- Las rutas protegidas consumen `Authorization: Bearer ...`; la prueba actual
  construye un token Base64 de cuatro partes.

La propuesta conserva rutas y formas de respuesta. Aplicar identidad en vez
del `owner` enviado por el cliente cambia el resultado de solicitudes
cruzadas; limitar extensiones/tamano tambien restringe cargas que hoy se
aceptan. Esos cambios de seguridad se deben hacer visibles en las pruebas y
revisar antes de implementar, no presentarse como comportamiento ya aprobado.

La API solo consume el token; el contrato del componente que lo emite no se
inspecciono por el alcance acordado. Antes de elegir algoritmo, clave, emisor,
audiencia y claims definitivos, coordinar esos valores con el responsable del
emisor. No codificar secretos reales ni inventar valores de produccion.

## H-API-01 — Token Base64 sin firma (Aprobado)

- **Aprobacion humana:** Juan Mendieta, 26/10/26 (confirmada en esta
  interaccion).
- **Bloqueo para implementar:** falta coordinar con el emisor el algoritmo,
  `issuer`, `audience`, la configuracion de clave y los claims requeridos.
  No editar codigo ni seleccionar una biblioteca/parametros JWT hasta contar
  con ese contrato.

- **Problema:** `legacy_identity` confia en contenido decodificado de Base64,
  compara un secreto constante y comprueba expiracion, pero no verifica una
  firma JWT ni emisor/audiencia.
- **Cambio propuesto:** validar firma, algoritmo permitido, `exp`, `iss` y
  `aud` mediante una biblioteca JWT mantenida solo despues de revisar el
  contrato del emisor y justificar la dependencia. Leer clave y valores
  esperados de configuracion externa; devolver un error generico sin texto de
  excepcion. Mantener el header Bearer y la identidad `username`/`role` que
  necesitan las rutas, sujeto a coordinacion del contrato.
- **Archivos previstos:** `api/app/main.py`; `api/requirements.txt` si la
  biblioteca elegida no esta ya disponible; `api/tests/test_api.py`.
- **Caracterizacion antes de editar:** agregar pruebas locales que documenten
  el header Bearer, la identidad reconocida por el token ficticio vigente y el
  401 para token invalido/expirado. Registrar que el token de prueba actual es
  Base64, no un JWT firmado. Tras la caracterizacion, reemplazar el fixture por
  JWT firmado con clave aislada de pruebas y probar firma, emisor, audiencia y
  expiracion invalidos; no conservar como expectativa de seguridad la
  aceptacion del token Base64 legado.
- **Registro de ejecucion (H-API-01):**
  - cwd `api/`, `python -m pytest tests/test_api.py` (antes de agregar la
    caracterizacion): **4 passed**.
  - cwd `api/`, `python -m pytest tests/test_api.py` (con caracterizacion de
    identidad Bearer y token expirado): **6 passed**.
  - Reejecucion en esta interaccion, cwd `api/`, `python -m pytest
    tests/test_api.py`: **6 passed**.
  - No se modifico codigo de produccion ni se ejecuto cobertura. El cambio de
    autenticacion queda bloqueado hasta coordinar el contrato JWT del emisor.
    Se informo `HS256`, pero `issuer`, `audience`, variable de entorno de la
    clave y claims requeridos siguen pendientes.
  - En esta interaccion se eligio proponer al emisor `HS256`, `iss=workshop-auth`,
    `aud=workshop-api`, variable `WORKSHOP_JWT_SECRET` y claims `sub`, `role`,
    `exp`, `iss` y `aud`. Es una propuesta sin confirmacion del emisor; no se
    compartio ni se invento el valor de una clave.
  - En la continuacion del 26/10/26 se selecciono de nuevo esa propuesta, pero
    la confirmacion del emisor se dejo vacia/pendiente. No se modifico codigo
    ni pruebas y no se ejecuto una prueba de caracterizacion nueva; H-API-01
    sigue bloqueado hasta recibir la confirmacion real del emisor sobre
    algoritmo, issuer, audience, configuracion de clave y claims.

## H-API-02 — Owner controlado por cliente (Aprobado)

- **Aprobacion humana:** Juan Mendieta, 26/10/26 (confirmada en esta
  interaccion). Politica acordada: STUDENT y TRAINER solo pueden leer y crear
  tareas bajo su propia identidad; el `owner` enviado por el cliente no cambia
  esa identidad.
- **Bloqueo para corregir:** la implementacion depende de una identidad
  verificada, pero `legacy_identity` aun confia en un token Base64 sin firma.
  H-API-01 sigue bloqueado por el contrato pendiente con el emisor.
- **Mitigacion provisional autorizada:** Juan Mendieta, 26/10/26, autorizo
  ignorar el query `owner` de `GET /api/tasks` y filtrar por el username
  decodificado del token legado para que el test de lectura cruzada pase. Esto
  reduce la seleccion accidental/cruzada por query, pero no es autorizacion
  segura: un cliente puede fabricar el token Base64 y elegir ese username.
  H-API-02 permanece **Pendiente** hasta verificar firma/claims y limitar
  tambien `GET /api/summary` y `POST /api/tasks`.
- **Problema:** `owner` de query selecciona filas para tareas/resumen y `owner`
  del cuerpo puede asignarse al crear, en vez de limitarse a la identidad
  autenticada.
- **Cambio propuesto:** derivar el owner de las operaciones de identidad
  verificada. Mantener las rutas, campos de respuesta y, si el contrato
  acordado exige conservarlos, aceptar los campos `owner` de entrada sin
  permitir que seleccionen otra identidad. La regla para usuarios con rol
  trainer debe acordarse; el codigo actual no define una politica de roles.
- **Archivos previstos:** `api/app/main.py`; `api/tests/test_api.py`; si se
  aprueba separar capas, los nuevos modulos de servicio/repositorio bajo
  `api/app/`.
- **Caracterizacion antes de editar:** con tokens ficticios `student` y
  `trainer`, documentar el resultado actual al consultar `owner=trainer` como
  student y al crear una tarea con `owner=trainer`. Despues de registrar esa
  linea base, las pruebas de correccion deben verificar que un usuario no
  puede leer ni asignar datos de otra identidad; conservar el acceso existente
  de cada identidad a sus propias tareas. La politica acordada para TRAINER es
  la misma que para STUDENT: operar solo sobre tareas propias.
- **Registro de ejecucion (H-API-02):**
  - Linea base previa a agregar caracterizaciones, cwd `api/`,
    `python -m pytest tests/test_api.py`: **6 passed**.
  - Caracterizacion antes de corregir, cwd `api/`,
    `python -m pytest tests/test_api.py -k 'characterizes_student'`:
    **2 passed**. Se observo que STUDENT puede leer tareas de TRAINER y crear
    una tarea con `owner=trainer`.
  - Regresion de caracterizacion, cwd `api/`,
    `python -m pytest tests/test_api.py`: **8 passed**.
  - No se modifico codigo de produccion ni se ejecuto una prueba de correccion
    posterior: el cambio queda bloqueado hasta resolver H-API-01 y verificar
    que las operaciones usan una identidad autenticada.
  - Continuacion 26/10/26, aprobacion de Juan Mendieta para mitigacion
    provisional de lectura en `GET /api/tasks`; caracterizacion antes del
    cambio, cwd `api/`,
    `python -m pytest tests/test_api.py -k 'rejects_student_reading_trainer_tasks or characterizes_student_reading_trainer_tasks'`:
    codigo de salida **1**, **1 failed, 1 passed**. El test de rechazo fallo
    porque se devolvio una tarea de TRAINER al token STUDENT.
  - Se implemento solo el filtro propio para `GET /api/tasks`, ignorando el
    query `owner`; se mantiene H-API-02 pendiente porque el token no esta
    firmado y el resumen/creacion siguen aceptando owner ajeno.
  - Prueba focal posterior, cwd `api/`,
    `python -m pytest tests/test_api.py -k 'rejects_student_reading_trainer_tasks or trainer_cannot_read_student_tasks'`:
    codigo de salida **0**, **2 passed, 34 deselected**.
  - La primera suite completa posterior obtuvo **2 failed, 34 passed** porque
    dos pruebas todavía esperaban que `GET /api/tasks` filtrara por un query
    `owner` diferente a la identidad. Se actualizaron esas expectativas para
    comprobar el contrato provisional: owner desconocido y texto tipo SQL se
    ignoran en la lista y solo se devuelven tareas propias; `GET /api/summary`
    mantiene su comprobación de valor literal parametrizado.
  - Suite final, cwd `api/`,
    `python -m pytest tests/test_api.py --cov=app --cov-report=term-missing`:
    codigo de salida **0**, **36 passed**; 109 sentencias, 0 omitidas,
    22 ramas, 2 parciales y cobertura reportada **98%** para `app`. Esto mide
    cobertura global de la aplicación, no un subconjunto diferencial de líneas.
    Pytest reportó 71 avisos de deprecación de `on_event`; no se ocultaron.
  - Rollback solicitado el 26/10/2026: se revirtió la mitigación provisional
    en `GET /api/tasks`, por lo que `owner` vuelve a seleccionar el filtro
    (o se usa la identidad del token si se omite). Se restauraron las
    expectativas de owner desconocido y expresión SQL como valor literal; la
    prueba de autorización cruzada vuelve a evidenciar el hallazgo. La prueba
    de trainer se dejó verificando su listado por defecto, sin solicitar
    explícitamente tareas de STUDENT.
  - Validación tras rollback, cwd `api/`,
    `python -m pytest tests/test_api.py --cov=app --cov-report=term-missing`:
    codigo de salida **1**, **35 passed, 1 failed**. El unico fallo es
    `test_rejects_student_reading_trainer_tasks`: HTTP 200 incluye una tarea
    TRAINER en respuesta al token STUDENT. Cobertura global de `app`: **98%**
    (109 sentencias, 0 omitidas; 22 ramas, 2 parciales). H-API-02 sigue
    pendiente; no se afirma que la vulnerabilidad esté corregida.

## H-API-03 — SQL construido con entradas concatenadas (Resuelto)

- **Aprobacion humana:** Juan Mendieta, 26/10/2026 (confirmada en esta
  interaccion).
- **Problema:** el filtro de owner y los campos del insert se interpolan en
  SQL; la consulta de lectura de la nueva fila tambien concatena un id.
- **Cambio propuesto:** usar parametros enlazados de SQLite para todo valor
  dinamico en filtros e inserts. Para el id insertado, preferir recuperar la
  fila por el identificador con parametro enlazado. No cambiar nombres de
  endpoints ni forma de respuesta.
- **Archivos previstos:** `api/app/main.py` o el repositorio nuevo bajo
  `api/app/` si se implementa H-API-05; `api/tests/test_api.py`.
- **Caracterizacion antes de editar:** verificar con una base temporal que
  crear tarea normal devuelve 201 y los campos actuales, y que consultar owner
  propio filtra como se observa hoy. Agregar valores ficticios con comilla
  literal en campos de texto y verificar que se guardan y recuperan literalmente
  sin error; despues de la correccion, comprobar tambien que no alteran el
  conjunto de filas devuelto. No usar bases ni servicios remotos.
- **Registro de ejecucion (H-API-03):**
  - Linea base previa a la caracterizacion, cwd `api/`,
    `python -m pytest tests/test_api.py`: **13 passed**.
  - Caracterizacion antes del cambio, cwd `api/`,
    `python -m pytest tests/test_api.py -k 'characterizes_owner_filter or characterizes_quoted_task_fields'`:
    **3 passed**. El filtro SQL-like devolvia las 3 tareas (y el resumen
    incluia las 3); crear una tarea con comillas en texto devolvia HTTP 500.
    El filtro normal `owner=student` devolvia las 2 tareas de student.
  - Correccion: se parametrizaron los filtros de tareas/resumen, el INSERT y
    la lectura por `lastrowid`.
  - Pruebas posteriores de correccion, cwd `api/`,
    `python -m pytest tests/test_api.py -k 'owner_filter or owner_sql_expression or quoted_fields'`:
    **3 passed**. El filtro SQL-like devuelve lista vacia y resumen total 0;
    los textos con comillas se crean y recuperan literalmente con HTTP 201.
  - Regresion y cobertura posteriores, cwd `api/`,
    `python -m pytest tests/test_api.py --cov=app.main --cov-report=term-missing`:
    **16 passed**, cobertura de `app.main` **94%** (109 statements, 6 missed;
    22 branches, 2 partial).

## Aprobaciones registradas para trabajo posterior

- **H-API-05:** Juan Mendieta, 26/10/26. Aprobacion confirmada; no se
  implemento en este cambio.
- **H-API-07:** Juan Mendieta, 26/10/26. Aprobacion confirmada; no se
  implemento en este cambio.

## H-API-04 — Carga de archivos sin controles visibles (Resuelto)

- En esta interaccion (26/10/26), Juan Mendieta confirmo que H-API-04 habia
  recibido aprobacion humana. Se acordo aceptar solo `.txt` hasta 4 MiB,
  preservando el caso observado `requirements.txt`; la politica propuesta de
  aceptar solo `.pdf` se descarto para no rechazar ese caso.
- **Problema:** el nombre proporcionado se usa para formar la ruta y se lee el
  archivo completo sin limite de tamano.
- **Cambio propuesto:** normalizar y reducir el nombre a un nombre de archivo
  seguro, definir extensiones permitidas y tamano maximo como constantes con
  nombre, y leer con limite antes de escribir. Rechazar cargas fuera de la
  politica con error HTTP generico. La politica acordada es `.txt` hasta 4
  MiB. Se mantiene la ruta, respuesta y archivo guardado para cargas permitidas.
- **Archivos previstos:** `api/app/main.py` o modulo de servicio de archivos
  bajo `api/app/` si se separa; `api/tests/test_api.py`.
- **Caracterizacion antes de editar:** en directorio temporal, subir un archivo
  ficticio pequeno `requirements.txt` y verificar 201, campos de respuesta y
  bytes guardados. Registrar el comportamiento actual para nombre con
  separadores, extension no prevista y contenido mayor que el limite propuesto;
  despues de aprobar la politica, exigir rechazo y confirmar que no se crea ni
  sobrescribe un archivo fuera del directorio de cargas.
- **Registro de ejecucion (H-API-04):**
  - Caracterizacion antes de corregir, cwd `api/`,
    `python -m pytest tests/test_api.py -k 'characterizes_upload or uploads_requirement'`:
    **4 passed**. Se observo que `../outside.txt` se guardo fuera de `uploads`,
    y que `.pdf` y un archivo mayor de 4 MiB se aceptaron; `requirements.txt`
    devolvio 201 y guardo los bytes.
  - Pruebas de correccion antes del cambio, cwd `api/`,
    `python -m pytest tests/test_api.py -k 'upload'`: **3 failed, 1 passed**;
    las tres cargas que debian rechazarse devolvieron 201.
  - Regresion despues del cambio, cwd `api/`,
    `python -m pytest tests/test_api.py --cov=app.main --cov-report=term-missing`:
    **13 passed**, cobertura total de `app.main`: **94%** (111 statements,
    6 missed; 22 branches, 2 partial).
  - Se limitaron las extensiones a `.txt`, el archivo a 4 MiB y se rechazan
    nombres con separadores, extensiones no permitidas y cargas mayores al
    limite con HTTP 400 generico. Se conserva la respuesta y el contenido
    almacenado de `requirements.txt`.

## H-API-05 — Responsabilidades mezcladas (Aprobado)

- **Problema:** inicializacion de SQLite, SQL, logica de endpoints,
  serializacion y gestion de archivos comparten `main.py`.
- **Cambio propuesto:** separar rutas HTTP, reglas de servicio y persistencia
  en modulos pequenos de `api/app/`; mantener las firmas externas, estados y
  serializacion observados. Reutilizar helpers para evitar SQL, validacion o
  conversiones duplicadas. No iniciar esta separacion hasta que las pruebas de
  caracterizacion de las rutas cubiertas esten escritas.
- **Archivos previstos:** `api/app/main.py`, nuevos modulos de router/servicio/
  repositorio bajo `api/app/`, y `api/tests/test_api.py`.
- **Caracterizacion antes de editar:** extender pruebas con `TestClient` y
  SQLite/directorio temporales para listar, crear y resumir tareas, cargar un
  archivo y consultar backend-health mediante una respuesta local simulada.
  Fijar rutas, estados, valores por defecto y campos de respuesta observados;
  no llamar a servicios externos. Ejecutar esas pruebas tras cada extraccion.

## H-API-06 — Versiones para revision SCA (Aprobado)

- **Problema:** `urllib3==2.5.0` y `python-multipart==0.0.21` coinciden con las
  versiones senaladas por el reto, pero no hay evidencia de analisis de
  advisories aplicables.
- **Cambio propuesto:** revisar advisories para las versiones directas y el
  arbol resuelto, registrar fuente/fecha/resultado y actualizar o retirar solo
  si la evidencia lo requiere. No silenciar findings ni anadir un scanner o
  dependencia de aplicacion sin justificacion. Coordinar actualizacion con
  quien mantenga integraciones externas si cambia compatibilidad.
- **Archivos previstos:** `api/requirements.txt` solo si la evidencia justifica
  cambios; `api/requirements-dev.txt` solo si una herramienta de auditoria se
  aprueba y necesita declaracion; `api/tests/test_api.py` solo si una
  actualizacion requiere pruebas de compatibilidad.
- **Caracterizacion antes de editar:** guardar el inventario de versiones
  instaladas y ejecutar el analisis de advisories disponible antes de cambiar
  el manifiesto; correr `python -m pip check` y las pruebas actuales de API
  como linea base. No se propone un test unitario que congele las versiones
  cuestionadas. Si no hay scanner disponible, dejar el resultado como
  pendiente y no afirmar que el riesgo quedo verificado.

## H-API-07 — Tipos, errores y complejidad (Aprobado)

- **Problema:** el body de creacion es `dict[str, Any]`, hay capturas de
  excepcion amplias y `summary` contiene condiciones anidadas.
- **Cambio propuesto:** definir modelos Pydantic de entrada/salida con tipos y
  valores por defecto que reflejen el contrato acordado; extraer conversiones
  reutilizables, reemplazar condicionales anidados por condiciones combinadas
  o retornos tempranos y devolver errores genericos con manejo explicito. Cada
  funcion debe tener una responsabilidad y no introducir strings o numeros
  magicos.
- **Archivos previstos:** `api/app/main.py`, nuevos modulos de esquemas/
  servicio bajo `api/app/` solo si se necesitan para mantener responsabilidades,
  y `api/tests/test_api.py`.
- **Caracterizacion antes de editar:** cubrir creacion con campos minimos y
  valores por defecto, campos completos, resumen vacio/no vacio, errores de
  autenticacion y fallo local simulado de backend-health. Registrar estados y
  formas actuales; acordar por separado cualquier cambio de coercion, campos
  requeridos o detalle de error antes de actualizar las expectativas.

## Secuencia y controles

1. Escribir y ejecutar las caracterizaciones de cada hallazgo con SQLite y
   archivos temporales; guardar resultados reales antes de cambiar codigo.
2. Acordar el contrato JWT con su emisor y las politicas pendientes de owner,
   roles, extensiones y tamano. No inventar aprobaciones ni valores de
   configuracion.
3. Implementar primero parametros SQL, validacion de identidad/autorizacion y
   controles de carga en cambios revisables; despues extraer capas y modelos.
   Resolver SCA solo con evidencia de advisories.
4. Ejecutar regresion API y revisar cobertura del codigo cambiado. Registrar
   comandos y resultados reales en `docs/TESTING.md` cuando se realice esa
   etapa; no hay ejecuciones registradas por este plan.

## Documentacion del contrato observado — API

- **Registro (H-API-01 a H-API-07):** 26/10/26 se creo
  `docs/ENDPOINTS.md` a partir del codigo actual de `api/app/main.py`, sin
  modificar codigo ni pruebas. Se documentan contratos observados, ejemplos,
  respuestas de autenticacion/validacion/error, y riesgos/decisiones abiertas.
- Se hicieron sondeos locales con `TestClient` y recursos temporales para
  verificar ejemplos de respuesta, errores 401/422/500 y el caso exitoso de
  backend-health usando una respuesta upstream simulada. No se llamo al
  servicio externo real y no se ejecuto la suite de pruebas.

## Pruebas de endpoints — API (H-API-01 a H-API-07)

- **Registro:** 26/10/26 se amplio `api/tests/test_api.py` para cubrir camino
  feliz, bordes y respuestas de error documentadas en `docs/ENDPOINTS.md`.
  Incluye listado/creacion/resumen de tareas, filtros SQL, carga de archivo,
  backend-health simulado, errores 401/400/422/500 y la comprobacion de acceso
  entre owners.
- **H-API-02 — fallo de seguridad observado:** `test_rejects_student_reading_trainer_tasks`
  (cwd `api/`, `python -m pytest tests/test_api.py`) esperaba que un token de
  STUDENT no recibiera tareas de TRAINER, pero la respuesta actual fue HTTP
  200 con una tarea ajena. El test se conserva como regresion fallida; no se
  cambio la autorizacion ni se adapto la expectativa.
- **Ejecucion completa:** cwd `api/`, `python -m pytest tests/test_api.py`,
  codigo de salida **1**: **35 passed, 1 failed** (el test H-API-02 indicado).
- **Cobertura excluyendo ese test fallido:** cwd `api/`,
  `python -m pytest tests/test_api.py -k 'not rejects_student_reading_trainer_tasks' --cov=app --cov-report=term-missing`,
  codigo de salida **0**: **35 passed, 1 deselected**. Cobertura global de
  `app`: **98%**, 109 statements, 0 missed, 22 branches y 2 parciales. Metodo:
  `pytest-cov` sobre el paquete de aplicacion completo; no es una medicion
  separada del diff de pruebas. No se modifico codigo de produccion.
- **Prueba focal adicional:** cwd `api/`,
  `python -m pytest tests/test_api.py -k 'backend_health_configuration'`,
  codigo de salida **0**: **1 passed, 35 deselected**; se verifica HTTP 500
  para fallo simulado de configuracion antes de la llamada upstream.
- **Pendiente:** resolver H-API-02 de acuerdo con la identidad autenticada
  verificada por H-API-01 y volver a ejecutar la suite completa. Las pruebas
  no certifican advisories de dependencias H-API-06.
