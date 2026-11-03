---
name: jira-incident-root-cause-analyzer
description: Analiza incidentes provenientes de Jira para identificar patrones recurrentes, agrupar incidentes similares, detectar causas raíz comunes y generar recomendaciones de remediación y prevención basadas en evidencia.
---
# Skill: Jira Incident -&gt; Root Cause Analyzer

## 1) Metadata

- **Skill ID:** jira-incident-root-cause-analyzer
- **Version:** 0.1.0
- **Purpose:** Analizar tickets de incidentes registrados en Jira para descubrir agrupaciones naturales, causas raíz recurrentes, tendencias operativas y oportunidades de mejora continua.
- **Audience (roles):** Incident Manager, SRE, DevOps, Tech Lead, Backend, QA, Support, Problem Manager
- **When to use:** Durante actividades de Problem Management, revisiones post-incidente, análisis de tendencias operativas y detección de problemas sistémicos.
- **When NOT to use:** Análisis de un incidente individual sin histórico suficiente, incidentes activos en contención o investigaciones forenses de seguridad.
- **Sensitive inputs:** No incluir credenciales, datos personales, tokens, secretos, dumps de bases de datos ni información confidencial de clientes.
- **Expected output:** Documento Markdown estructurado según la sección Output definida más adelante.

---

## 2) Inputs

Proporciona la información en este formato:

- **Jira Project(s):**
- **Analysis period:** (ej. últimos 3 meses)
- **Incident dataset:** (tickets Jira, export CSV, consulta JQL o listado)
- **Fields available:**
  - Summary
  - Description
  - Resolution notes
  - Service/Application
  - Component
  - Priority
  - Severity
  - Environment
  - Root Cause (si existe)
  - Resolution Category
  - Labels
  - Creation Date
  - Resolution Date
- **Known business context:**
- **Systems involved:**
- **Known recurring issues:** (si existen)
- **Categorization standard:** (ITIL, interno, otro)
- **Expected outcome of analysis:**

---

## 3) Output

Devuelve **solo** un documento Markdown con estas secciones:

### 1. Executive Summary

- Total de incidentes analizados
- Periodo analizado
- Hallazgos principales
- Principales dominios afectados

### 2. Incident Distribution

- Por aplicación
- Por servicio
- Por severidad
- Por prioridad
- Por entorno

### 3. Cluster Analysis

Para cada grupo identificado:

- Cluster ID
- Descripción del patrón común
- Cantidad de incidentes
- Sistemas involucrados
- Síntomas recurrentes
- Impacto observado

### 4. Root Cause Categories

Agrupar incidentes en categorías como:

- Defectos de software
- Configuración incorrecta
- Integración externa
- Infraestructura
- Base de datos
- Despliegues/cambios
- Capacidad o rendimiento
- Monitoreo insuficiente
- Error humano
- Dependencias externas
- Seguridad
- Otros

### 5. Top Root Causes

Para cada causa raíz identificada:

- Descripción
- Cantidad de incidentes asociados
- Impacto estimado
- Evidencia encontrada
- Nivel de confianza (Alto/Medio/Bajo)

### 6. Recurring Patterns

- Patrones funcionales
- Patrones técnicos
- Patrones operativos
- Patrones temporales
- Patrones por equipo o componente

### 7. Incident Correlation Matrix

- Componentes relacionados
- Dependencias recurrentes
- Servicios afectados conjuntamente
- Posibles problemas sistémicos

### 8. Recommendations

#### Corrective Actions

- Acciones inmediatas
- Acciones de mediano plazo

#### Preventive Actions

- Automatización
- Monitoreo
- Observabilidad
- Testing
- Arquitectura

### 9. Problem Candidates

Lista priorizada de problemas candidatos para Problem Management:

- Problema
- Evidencia
- Cantidad de incidentes relacionados
- Prioridad sugerida

### 10. Open Questions

- Información faltante
- Datos inconsistentes
- Áreas que requieren validación adicional

---

## 4) Analysis Guidelines

Al analizar los incidentes:

### Agrupación semántica

Identifica similitudes utilizando:

- Títulos similares
- Palabras clave recurrentes
- Componentes afectados
- Servicios involucrados
- Tipos de error
- Códigos de error
- Síntomas comunes

### Detección de patrones

Busca:

- Reincidencia temporal
- Concentración por entorno
- Dependencias involucradas
- Cambios previos al incidente
- Equipos asociados
- Aplicaciones afectadas

### Inferencia de causa raíz

Cuando la causa raíz no exista explícitamente:

- Utiliza evidencias observables
- Agrupa síntomas equivalentes
- Identifica correlaciones frecuentes
- Declara el nivel de confianza

### Priorización

Utiliza:

- Frecuencia
- Impacto
- Tiempo de resolución
- Severidad
- Alcance del servicio afectado

---

## 5) Constraints

- No inventar causas raíz sin evidencia observada.
- Si la evidencia es insuficiente, marcar como "Hipótesis".
- Diferenciar claramente hechos de inferencias.
- No incluir datos sensibles.
- Mantener trazabilidad entre incidentes y conclusiones.
- Toda recomendación debe estar vinculada a uno o más incidentes.
- Evitar conclusiones basadas en un único incidente aislado.

---

## 6) Validation Rules

La salida es válida si:

- Incluye todas las secciones definidas en Output.
- Identifica al menos 3 categorías de causa raíz cuando los datos lo permitan.
- Incluye evidencia para cada causa raíz propuesta.
- Contiene al menos 5 recomendaciones accionables.
- Diferencia claramente evidencia, hipótesis y conclusiones.
- Identifica candidatos para Problem Management.
- No contiene datos sensibles.
- Incluye nivel de confianza para cada causa raíz inferida.

---

## 7) Evidence

Adjuntar o referenciar:

- `SKILL.md`
- `examples/input.sample.md`
- `examples/output.sample.md`
- Export Jira utilizado para el análisis (`csv`, `json` o consulta `JQL`)
- Evidencia de agrupamiento o categorización realizada
- Tag de versión como:

`skill-jira-root-cause-analyzer-v0.1.0`

---

## 8) Advanced Analysis Rules (Optional)

Si existen más de 50 incidentes:

### Generar Top 10 Hallazgos

- Causa raíz más frecuente
- Sistema más afectado
- Componente más inestable
- Equipo con mayor carga operativa
- Tipo de error más recurrente
- Dependencia externa más incidente
- Cambio más correlacionado
- Entorno más afectado
- Servicio crítico más impactado
- Oportunidad principal de automatización

### Generar Heatmap Conceptual

| Categoría | Incidentes | Impacto | Prioridad |
| --- | --- | --- | --- |
| Software Defects | Alto | Alto | Crítica |
| Infrastructure | Medio | Alto | Alta |
| Configuration | Alto | Medio | Alta |

### Generar Pareto 80/20

Identificar qué causas raíz explican aproximadamente el 80% de los incidentes observados y proponer un backlog priorizado de remediación.