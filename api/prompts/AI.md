# AGENTS.md (ejemplo): revision de login en auth

## AMBITO
Workspace ai-labs abierto en su raiz. Lee codigo solo en auth/.
Todas las rutas parten de la raiz. Lee README.md, RETO.md y docs/ generales.
Esta tarea es de solo lectura; no escribas archivos.
Git se ejecuta desde la raiz; las pruebas propuestas usan cwd auth/.
No leas ni modifiques codigo de api/ ni web/. Usa IDs H-AUTH-NN y componente auth.

## SOLUCION Y TECNOLOGIA
ai-labs es un monorepo de practica (un solo repo Git) con deuda tecnica y
vulnerabilidades sembradas a proposito. Los alumnos las identifican, priorizan
y remedian. Hay tres componentes que se levantan juntos con compose.yaml:

| Componente | Funcion | Tecnologia | Puerto local |
|---|---|---|---|
| auth/ | Login: POST /auth/login valida credenciales en SQLite y emite un token | Java 21, Quarkus 3.27.4 (REST/Jackson, Arc, SmallRye Health), sqlite-jdbc 3.50.3.0, Commons Text 1.9, Maven, JUnit5 + RestAssured, JaCoCo | 8080 |
| api/ | Tareas y requisitos: /api/tasks, /api/summary, /api/requirements, /api/backend-health, subida de archivos | Python 3.11-3.13, FastAPI 0.128.2, Uvicorn, Pydantic 2.13.4, sqlite3, pytest (cobertura >= 85%) | 8000 |
| web/ | Interfaz: login y dashboard que consumen /auth/login y /api/tasks | Angular 21, TypeScript 5.9.3, Vitest, nginx | 4200 |

Flujo: web -> auth (login, devuelve token) -> web -> api (con el token).
api consulta la salud de auth en /q/health. Docker Compose publica todo solo
en 127.0.0.1. Las pruebas se ejecutan con python tools/lab.py test auth|api|web
desde la raiz (auth usa mvn verify; api, pytest; web, npm test y build).

Hallazgos sembrados en auth segun RETO.md (a verificar, no dar por ciertos):
SCA (Quarkus y Commons Text), contrasenas en texto plano, SQL concatenado,
token Base64 con secreto embebido, secreto y CORS hardcodeados, Resource con
varias responsabilidades y errores que exponen detalles internos.

## CONTEXTO
ai-labs autentica mediante POST /auth/login. Lee README.md, RETO.md y
docs/ENDPOINTS.md si existe. Localiza la ruta desde el recurso HTTP
(auth/src/main/java/com/bcp/workshop/auth/AuthResource.java) hasta la
consulta a SQLite (LegacyDatabase.java). No des por cierta la lista de RETO.md.

## OBJETIVO
Determinar si las entradas del login (username, password) llegan
concatenadas a una consulta SQL.

## RESTRICCIONES
- No edites codigo ni ejecutes ataques contra servicios remotos.
- Usa solo codigo y datos ficticios locales.
- Si falta un archivo o no puedes ejecutar una comprobacion, dilo.
- No cambies contratos ni leas otros componentes.
- No agregues secretos reales; usa valores de prueba aislados.

## CRITERIOS DE ACEPTACION
- Identifica el recorrido de la entrada hasta la consulta con archivo y linea.
- Distingue concatenacion, parametrizacion y cualquier caso no comprobado.
- Propone una prueba local con credenciales validas, invalidas y entrada con
  comilla, con resultado esperado segun el contrato observado.
- No afirmes que la prueba paso si solo la propusiste.

## FORMATO DE RESPUESTA
Tabla: afirmacion | evidencia archivo:linea | comprobado o hipotesis |
prueba propuesta. Termina con preguntas abiertas y comandos no ejecutados.