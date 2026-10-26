# Pruebas de API — FastAPI

## Alcance y medicion

Las pruebas cubren los cinco endpoints documentados en `docs/ENDPOINTS.md`.
Los casos usan `TestClient`, SQLite y directorios temporales; la respuesta de
`/api/backend-health` se simula localmente. No se requiere llamar a servicios
externos.

La medicion usa `pytest-cov` con `--cov=app --cov-report=term-missing`, que
mide las sentencias y ramas de toda la aplicacion Python bajo `api/app/`.
Reporte actual: **109 sentencias, 0 no cubiertas, 22 ramas, 2 parciales, 98%**.
Numerador/denominador del reporte global: **109/109 sentencias cubiertas**;
pytest-cov muestra 98% al combinar sentencias y ramas parciales. El codigo de
`api/app/main.py` tocado tiene 109 sentencias instrumentadas, 0 omitidas y 98%
de cobertura reportada, por encima de la meta de 85%. El reporte es global de
`app` y no una medicion diferencial aislada por linea cambiada.

## Matriz de casos

| endpoint | caso | tipo | resultado esperado |
|---|---|---|---|
| `GET /api/tasks` | Listado de tareas semilla (`test_lists_seeded_tasks`) | Camino feliz | HTTP 200 y dos tareas de `student`. |
| `GET /api/tasks` | Owner conocido (`test_characterizes_owner_filter_with_regular_owner`) | Camino feliz / caracterizacion | HTTP 200, dos tareas propias de `student`; el query coincide con la identidad. |
| `GET /api/tasks` | Owner desconocido (`test_lists_empty_result_for_unknown_owner`) | Borde | HTTP 200 y `[]`. |
| `GET /api/tasks` | Owner con expresion SQL (`test_filters_owner_sql_expression_as_literal_value`) | Seguridad H-API-03 | HTTP 200 y `[]`; el resumen parametrizado devuelve total 0 para ese owner. |
| `GET /api/tasks` | STUDENT intenta leer tareas de TRAINER (`test_rejects_student_reading_trainer_tasks`) | Error de autorizacion H-API-02 | **Falla actualmente:** HTTP 200 contiene una tarea de TRAINER. |
| `GET /api/tasks` | Token ausente/invalido (`test_all_endpoints_require_valid_authentication`) | Error H-API-01 | HTTP 401 con `detail` que empieza con `Invalid token:`. |
| `GET /api/tasks` | Tabla SQLite ausente (`test_returns_internal_error_when_task_table_is_missing`) | Error | HTTP 500 y texto `Internal Server Error`. |
| `POST /api/tasks` | Crear con campos completos (`test_creates_task_and_summary`) | Camino feliz | HTTP 201 y tarea persistida con los campos enviados. |
| `POST /api/tasks` | Campos de texto con comillas (`test_creates_task_with_quoted_fields`) | Borde H-API-03 | HTTP 201 y textos recuperados literalmente. |
| `POST /api/tasks` | Objeto vacio (`test_creates_task_with_empty_object_defaults`) | Borde | HTTP 201; valores por defecto observados (`""`, `TODO`, `MEDIUM`, username). |
| `POST /api/tasks` | Body que no es objeto (`test_rejects_non_object_task_body`) | Error | HTTP 422, `loc` igual a `["body"]`. |
| `POST /api/tasks` | Token ausente/invalido (`test_all_endpoints_require_valid_authentication`) | Error H-API-01 | HTTP 401. |
| `POST /api/tasks` | Tabla SQLite ausente (`test_returns_internal_error_when_task_creation_fails`) | Error | HTTP 500 y texto `Internal Server Error`. |
| `GET /api/summary` | Resumen del owner con datos (`test_returns_summary_for_seeded_owner`) | Camino feliz | HTTP 200 y conteos exactos por estado/prioridad. |
| `GET /api/summary` | Owner desconocido (`test_returns_empty_summary_for_unknown_owner`) | Borde | HTTP 200, total 0, `byStatus` vacio y `highPriorityOpen` 0. |
| `GET /api/summary` | Filtro SQL-like como literal (`test_filters_owner_sql_expression_as_literal_value`) | Error H-API-03 | HTTP 200 y total 0. |
| `GET /api/summary` | Token ausente/invalido (`test_all_endpoints_require_valid_authentication`) | Error H-API-01 | HTTP 401. |
| `GET /api/summary` | Tabla SQLite ausente (`test_returns_internal_error_when_summary_query_fails`) | Error | HTTP 500 y texto `Internal Server Error`. |
| `POST /api/requirements` | Archivo `requirements.txt` pequeno (`test_uploads_requirement`) | Camino feliz | HTTP 201, respuesta completa y bytes guardados iguales al body enviado. |
| `POST /api/requirements` | Archivo exactamente de 4 MiB (`test_accepts_upload_at_maximum_size`) | Borde H-API-04 | HTTP 201 y 4 MiB guardados. |
| `POST /api/requirements` | Nombre con separadores (`test_rejects_upload_filename_with_path_separators`) | Error H-API-04 | HTTP 400; no se crea archivo fuera ni dentro del destino esperado. |
| `POST /api/requirements` | Archivo sin extension (`test_rejects_upload_without_extension`) | Error H-API-04 | HTTP 400 y `{"detail":"Invalid upload"}`. |
| `POST /api/requirements` | Extension no permitida (`test_rejects_unapproved_upload_extension`) | Error H-API-04 | HTTP 400; no se crea el archivo. |
| `POST /api/requirements` | Contenido mayor de 4 MiB (`test_rejects_upload_above_maximum_size`) | Error H-API-04 | HTTP 400; no se escribe el archivo. |
| `POST /api/requirements` | Parte `file` ausente o nombre vacio (`test_rejects_upload_when_file_part_is_missing`, `test_rejects_upload_without_filename`) | Error | HTTP 422 y detalle de validacion. |
| `POST /api/requirements` | Token ausente/invalido (`test_all_endpoints_require_valid_authentication`) | Error H-API-01 | HTTP 401. |
| `POST /api/requirements` | Fallo de escritura simulado (`test_returns_internal_error_when_upload_write_fails`) | Error | HTTP 500 y texto `Internal Server Error`. |
| `GET /api/backend-health` | Respuesta upstream 200 simulada (`test_returns_backend_health_response`) | Camino feliz | HTTP 200 con `requestedBy`, status 200 y cuerpo upstream. |
| `GET /api/backend-health` | Timeout upstream simulado (`test_backend_health_returns_zero_status_when_upstream_fails`) | Borde/error documentado H-API-07 | HTTP 200 con status 0 y texto de la excepcion en `body`. |
| `GET /api/backend-health` | Token ausente/invalido (`test_all_endpoints_require_valid_authentication`) | Error H-API-01 | HTTP 401. |
| `GET /api/backend-health` | Fallo de configuracion antes de la llamada upstream (`test_returns_internal_error_when_backend_health_configuration_fails`) | Error | HTTP 500 y texto `Internal Server Error`. |

## Codigo de los tests

El codigo ejecutable completo reside en `api/tests/test_api.py`. Los tests de
cada fila de la matriz se identifican por el nombre de funcion indicado. En
particular, la comprobacion de IDOR es deliberadamente una asercion de
seguridad, no una caracterizacion que acepte el acceso indebido:

```python
def test_rejects_student_reading_trainer_tasks(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get(
            "/api/tasks",
            params={"owner": "trainer"},
            headers=headers(username="student"),
        )

    assert response.status_code == 200
    assert all(task["owner"] == "student" for task in response.json())
```

La autenticacion se verifica en las cinco rutas usando la misma prueba
parametrizada (`test_all_endpoints_require_valid_authentication`); los fallos
del servicio upstream y de operaciones locales usan mocks/recursos temporales,
sin servicios externos.

## Comandos y resultados ejecutados

Todos se ejecutaron desde `api/` con Python 3.13.15.

| comando | codigo de salida | resultado |
|---|---:|---|
| `python -m pytest tests/test_api.py --cov=app --cov-report=term-missing` (despues del rollback) | 1 | 35 passed, 1 failed: `test_rejects_student_reading_trainer_tasks`; 109/109 sentencias cubiertas, 22 ramas, 2 parciales; cobertura reportada 98%. |

Pytest emitio 71 avisos de deprecacion de `on_event` en FastAPI/Starlette; no
se silenciaron.

## Fallos, pendientes y pruebas propuestas

### Fallo reproducido; mitigacion provisional revertida

- **H-API-02:** `test_rejects_student_reading_trainer_tasks` falla porque
  `GET /api/tasks?owner=trainer` devuelve una tarea con `owner=trainer` al token
  de `student`. Se revirtio la mitigacion provisional que ignoraba `owner`;
  el filtro actual vuelve a aceptar el query del cliente. H-API-02 sigue
  pendiente y no se presenta la prueba fallida como una correccion.
- Resultado actual: **35 passed, 1 failed**; cobertura global reportada de
  `app`: **98%**.

### Pendientes

- Los errores 401 actuales revelan el motivo de validacion del token. El token
  sigue siendo Base64 sin firma (H-API-01).
- El test de lectura entre owners solo comprueba la mitigacion de query y no
  demuestra autorizacion segura hasta que H-API-01 valide un token firmado.
- H-API-06 necesita evidencia de advisories; esta matriz no certifica estado
  de CVEs.
- La cobertura global informada es de `app` y no de cada test ni de un diff de
  produccion. La mitigacion provisional modifica `api/app/main.py`; se reporta
  cobertura global porque el runner no genera una medida diferencial.

### Pruebas propuestas al corregir H-API-01/H-API-02

- Sustituir los fixtures Base64 por tokens firmados del contrato confirmado
  por el emisor, y probar firma, expiracion, issuer y audience invalidos.
- Comprobar que STUDENT no obtiene tareas TRAINER ni puede asignar tareas con
  owner ajeno; mantener una prueba positiva para tareas propias.
- No se atribuye resultado a estas pruebas hasta implementarlas y ejecutarlas.
