# Arquitectura del frontend

Registro de decisiones de arquitectura de `front-end/`. Cada decisión indica su
estado: **Hecho** (ya está en el código) o **Pendiente** (acordado, aún sin
implementar).

## 1. Estructura del repositorio

**Hecho.** La aplicación Next.js vive directamente en `front-end/`.

- Antes: `front end/mediflow/` (espacio en el nombre y subcarpeta redundante).
- Ahora: `front-end/`. Es solo un renombre, sin cambios de contenido.
- `schemas.py` (contrato del backend) permanece en la raíz del repositorio.

## 2. Stack

**Hecho.**

| Pieza | Versión | Nota |
| --- | --- | --- |
| Next.js (App Router) | 16.3.6 | Esta versión tiene cambios incompatibles: leer `node_modules/next/dist/docs/` antes de usar APIs (ver `AGENTS.md`). |
| React | 19.2.8 | |
| Tailwind CSS | 4 | Configuración en CSS (`app/globals.css`), sin `tailwind.config`. |
| TypeScript | 5 (`strict`) | Alias `@/*` apunta a la raíz de `front-end/`. |
| pnpm | 12.6.0 | Fijado en `packageManager`. |

Requisito local: activar con `corepack pnpm ...` si el `pnpm` global no coincide
con la versión fijada.

## 3. Sistema de diseño

**Hecho.** Se usa el tema por defecto de shadcn/ui, sin personalización, según
lo acordado para no extender la decisión de diseño.

- Preset: `base-nova`, color base `neutral`, variables CSS activadas
  (`components.json`).
- Componentes en `components/ui/`; utilidad `cn` en `lib/utils.ts`.
- Iconos: `lucide-react`.
- Tokens de color y radio definidos en `app/globals.css` (`:root` y `.dark`).
- Fuente: Geist, enlazada a `--font-sans` desde `app/layout.tsx` (el tema lee
  esa variable). Geist Mono queda en `--font-geist-mono`.
- Modo oscuro: los tokens `.dark` existen, pero no hay selector de tema. Hoy
  la interfaz se muestra siempre en claro.
- Idioma del documento: `es`.

Regla: cualquier color o radio nuevo se agrega como token, no como valor fijo
dentro de un componente.

## 4. Rutas

**Pendiente.** Rutas acordadas:

| Ruta | Propósito |
| --- | --- |
| `/` | Página principal |
| `/triaje/[id]` | Detalle de un triaje |
| `/historial` | Historial de documentos procesados |
| `/auditoria` | Documentos en auditoría humana |
| `/faq` | Preguntas frecuentes |

## 5. Tipos y capa de API

**Pendiente.**

- Los tipos TypeScript se derivan de `TriageResponse` en `schemas.py`
  (incluye `unidad_edad` y `signos_vitales`). Los valores de los enums deben
  coincidir literalmente con los del backend.
- El acceso a datos pasa por una única capa (`api.ts`). Hoy devolverá datos
  mock; apuntar al backend real debe implicar cambiar solo esa capa, sin
  tocar páginas ni componentes.
