# Contrato Backend ⇄ Frontend — Auditoría humana

**Estado: PROPUESTA para acordar con Frontend** (ya implementada en el backend).
Base URL: `http://localhost:8000`. Todas las respuestas devuelven `TriageResponse`.

## Cambios en `TriageResponse` / schemas (revisar tipos en `types/triage.ts`)

| Cambio | Detalle |
| --- | --- |
| `status` | Siempre un valor de `EstadoDocumento`: `procesados` \| `auditoria_humana` \| `validados`. Equivale al `estado` que hoy el front calcula en `lib/api.ts`. (Antes el backend devolvía `procesado`, `validado`, `rechazado`.) |
| **Nuevo** `decision_auditoria` | `"aprobado"` \| `"rechazado"` \| `null`. `null` = aún sin revisar. Mismo nombre/valores que `DecisionAuditoria` del front. |
| `datos_extraidos.paciente.nombre` | Ahora `string \| null` (el agente devuelve `null` si el documento no trae nombre). |
| `datos_extraidos.medico_solicitante.nombre` | Ahora `string \| null`. |
| **Nuevo** `medicamentos[].via` | `ViaAdministracion \| null` (enum: `Oral`, `Sublingual`, `Intravenosa (IV)`, `Intramuscular (IM)`, `Subcutanea (SC)`, `Inhalatoria`, `Topica`, `Oftalmica`, `Otica`, `Rectal`, `Vaginal`, `Sonda Enteral`, `Otra_No_Especificada`). |

## Endpoints

### `GET /triage?estado=auditoria_humana`
Cola de auditoría (más recientes primero). Sin `estado` devuelve todo el historial.

### `POST /triage/{documento_id}/aprobar`
Mueve `/auditoria_humana/{id}.json` → `/validados/{id}.json`.
Body (opcional): `{ "comentario": "string|null", "revisor": "string|null" }`
Respuesta 200: `status="validados"`, `decision_auditoria="aprobado"`, `decision_enrutamiento.requiere_auditoria_humana=false`, `almacenamiento_oci.ruta_objeto="validados/{id}.json"`.

### `POST /triage/{documento_id}/rechazar`
El documento **permanece** en `/auditoria_humana/` (no hay carpeta `/rechazados/`).
Mismo body. Respuesta 200: `status="auditoria_humana"`, `decision_auditoria="rechazado"`. Un rechazado puede aprobarse luego.

### Errores (cuerpo `{ "detail": "..." }`)
| Código | Cuándo |
| --- | --- |
| 404 | El documento no existe (ni en memoria ni en OCI/R2). |
| 409 | El documento no está en `auditoria_humana` (p. ej. ya fue validado). *(antes 400)* |
| 429 | Límite de uso del proveedor de IA (LLM) alcanzado (Rate Limit / tokens por minuto). Devuelve cabecera `Retry-After: 60` y mensaje `"Servicio ocupado por límite de uso del proveedor de IA. Por favor, intentá en un minuto."`. |
| 502 | Falló el almacenamiento (OCI/R2) o el agente falló por un error interno no recuperable. |
| 503 | Agente mal configurado (p. ej. falta API key o directorio del agente no encontrado). |

`POST /triage` guarda el documento crudo en `/recibidos/` antes de procesar, garantizando que no se pierdan datos aunque el agente falle (502, 503 o 429). En caso de 429, el cliente o frontend puede informar al usuario que intente en un minuto sin necesidad de reescribir su consulta.

## Mapeo sugerido en `lib/api.ts`
`estado = status` · `decision_auditoria = decision_auditoria` · `listarAuditoria() = GET /triage?estado=auditoria_humana` · `resolverAuditoria(id, "aprobado"|"rechazado")` → `POST /triage/{id}/aprobar|rechazar`.
