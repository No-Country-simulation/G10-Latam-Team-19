# Arquitectura del frontend

Registro de decisiones de arquitectura de `front-end/`. Cada decisión indica su
estado: **Hecho** (ya está en el código) o **Pendiente** (acordado, aún sin
implementar).

## 0. Objetivo semanal (PM)

Ponerse al día: elegir diseño e implementar de verdad las rutas acordadas, con
datos mock.

- Definir la dirección de diseño esta semana, sin extenderlo más. Si no hay
  consenso para el miércoles, usar el tema por defecto de shadcn/ui y avanzar
  igual.
- Implementar las rutas acordadas con contenido real, aunque sean datos de
  prueba hardcodeados.
- Armar los tipos TypeScript derivados del `TriageResponse` actualizado (con
  `unidad_edad`, signos vitales, etc.).
- Dejar una capa de API (`api.ts` o similar) que hoy apunte a datos mock y
  luego sea trivial apuntar al backend real.

**"Done" cuando** se puede navegar por las 5 rutas con datos de prueba
visibles en pantalla (no placeholders vacíos) y el diseño elegido ya está
aplicado al menos en `/` y `/triaje/[id]`.

| Criterio | Estado |
| --- | --- |
| Dirección de diseño definida (tema por defecto de shadcn/ui) | Hecho |
| 5 rutas navegables con datos de prueba visibles | Hecho |
| Tipos derivados de `TriageResponse` (con `unidad_edad` y signos vitales) | Hecho |
| Capa de API sobre datos mock, apuntable al backend real | Hecho |
| Diseño aplicado en `/` y `/triaje/[id]` | Hecho |

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

Aplicación del diseño (tema por defecto, sin personalizar): `components/ui/`
suma `badge` y `card` siguiendo la convención de shadcn. La prioridad se
comunica con variantes de badge (Urgente = `destructive`, Prioritario =
`default`, Rutina = `outline`) y la confianza con una barra que pasa a
`destructive` cuando el caso requiere auditoría humana. No se agregaron
colores ni radios nuevos.

## 4. Rutas

**Hecho.** Las cinco rutas están implementadas con datos mock visibles
(App Router, Server Components).

| Ruta | Propósito |
| --- | --- |
| `/` | Resumen (procesados, urgentes, pendientes de auditoría) y últimos documentos |
| `/triaje/[id]` | Detalle de un triaje; `notFound()` si el id no existe |
| `/historial` | Historial de documentos procesados |
| `/auditoria` | Cola de auditoría humana con Aprobar / Rechazar |
| `/faq` | Preguntas frecuentes |

- `params` es asíncrono en Next 16 (`PageProps<"/triaje/[id]">`).
- Las páginas que leen estado mutable usan `dynamic = "force-dynamic"`.
- Navegación común (`components/site-nav.tsx`) en el layout raíz y tabla
  reutilizable (`components/triajes-tabla.tsx`).
- Las mutaciones de `/auditoria` son Server Actions
  (`app/auditoria/actions.ts`) con `revalidatePath`; no hay API routes ni
  componentes cliente para esto.

## 5. Tipos y capa de API

**Hecho.**

- `types/triage.ts` deriva de `TriageResponse` en `schemas.py` (incluye
  `unidad_edad` y `signos_vitales`). Los `Optional` de Pydantic son
  `T | null`; los enums son arreglos `as const` con su tipo unión, y sus
  valores coinciden literalmente con los del backend (verificado).
- El acceso a datos pasa por una única capa, `lib/api.ts`, que hoy devuelve
  datos de `lib/mocks/triajes.ts` (5 triajes: urgencia, rutina, ambiguo,
  pediátrico y un segundo caso de auditoría). Apuntar al backend real implica
  cambiar solo esa capa.
- `Triaje` extiende `TriageResponse` con `estado` (`recibidos`, `procesados`,
  `auditoria_humana`, `validados`) y `decision_auditoria`. Son campos solo del
  frontend que simulan las carpetas de OCI Object Storage.
- El estado mock vive en memoria, en `globalThis`, para que páginas y Server
  Actions compartan instancia. Se reinicia con el servidor; no es persistencia.
- Con `NEXT_PUBLIC_API_URL`, `procesarDocumento` llama al `POST /triage`
  real. Historial, detalle y auditoría siguen en mock.

## 6. Dependencias del backend

**Pendiente.** Observado en la rama `feature/backend` (sin fusionar):

- Su `schemas.py` está desactualizado respecto al de la raíz: no tiene
  `UnidadEdad`, `SignosVitales` ni `MedicamentoPrescrito`, `medicamentos` es
  `list[str]` con un `dosis` aparte, y `TriageResponse` no incluye
  `canal_origen`.
- Solo expone `GET /health` y `POST /triage`. Faltan endpoints para listar el
  historial, obtener un triaje por id y resolver la auditoría; hasta entonces
  esas funciones de `lib/api.ts` siguen en mock.

## 7. Otras decisiones

**Hecho.**

- `<body>` lleva `suppressHydrationWarning`: extensiones del navegador
  (p. ej. ColorZilla) inyectan atributos antes de la hidratación.
- Las dependencias se instalan con pnpm (`pnpm-lock.yaml`); el README
  documenta `pnpm install` y `npm run dev`.
