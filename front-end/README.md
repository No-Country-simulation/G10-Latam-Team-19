# MediFlow — Frontend

Interfaz web de **MediFlow**, el agente autónomo para triaje, extracción y enrutamiento de documentos clínicos (Hackathon ONE G10 · Oracle Next Education & Alura).

Permite consultar los documentos procesados por el agente, revisar su clasificación y prioridad, y resolver desde una cola de **auditoría humana** (Human-in-the-Loop) los casos de baja confianza o con datos faltantes.

## Stack

| Pieza | Versión |
| --- | --- |
| Next.js (App Router, Turbopack) | 16.3.6 |
| React | 19.2.8 |
| TypeScript (`strict`) | 5 |
| Tailwind CSS | 4 |
| shadcn/ui (preset `base-nova`) + lucide-react | — |
| Gestor de paquetes | pnpm 12.6.0 |

## Requisitos

- Node.js **20.9 o superior**
- pnpm, solo para instalar dependencias (el repositorio incluye `pnpm-lock.yaml`)

## Puesta en marcha

Instala las dependencias una sola vez y levanta el servidor:

```bash
pnpm install
npm run dev
```

La aplicación queda disponible en <http://localhost:3000>.

> Si `npm run dev` responde `next: not found`, las dependencias aún no están instaladas: ejecuta `pnpm install` y espera a que termine antes de arrancar.

| Script | Descripción |
| --- | --- |
| `npm run dev` | Servidor de desarrollo |
| `npm run build` | Compilación de producción |
| `npm run start` | Sirve la compilación de producción |
| `npm run lint` | Análisis estático con ESLint |

## Rutas

| Ruta | Descripción |
| --- | --- |
| `/` | Resumen (procesados, urgentes, pendientes de auditoría) y últimos documentos |
| `/triaje/[id]` | Detalle de un triaje: clasificación, paciente, datos clínicos, signos vitales y enrutamiento |
| `/historial` | Todos los documentos procesados |
| `/auditoria` | Cola de auditoría humana con acciones Aprobar / Rechazar |
| `/faq` | Preguntas frecuentes |

## Estructura

```text
front-end/
├── app/             # Rutas (App Router) y server actions
├── components/      # Componentes propios; ui/ contiene los de shadcn/ui
├── lib/
│   ├── api.ts       # Única capa de acceso a datos
│   └── mocks/       # Datos de prueba (urgencia, rutina y caso ambiguo)
├── types/triage.ts  # Tipos derivados del contrato del backend
└── docs/            # Decisiones de arquitectura
```

## Datos y contrato con el backend

- El contrato es `schemas.py` (raíz del repositorio). Los tipos de `types/triage.ts` se derivan de él: los `Optional` de Pydantic son `T | null` y los enums son arreglos `as const` con sus valores literales.
- Toda la lectura y escritura de datos pasa por `lib/api.ts`. Apuntar al backend real implica cambiar únicamente esa capa, sin tocar páginas ni componentes.
- Por ahora las páginas usan **datos mock** en memoria (se reinician al reiniciar el servidor). Si se define `NEXT_PUBLIC_API_URL`, `procesarDocumento` llama al `POST /triage` real; el resto de funciones seguirá en mock hasta que el backend exponga endpoints de lectura.

Variable de entorno opcional (archivo `.env.local`):

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Estado

- [x] Tipos TypeScript derivados de `schemas.py`
- [x] Capa de API con datos mock
- [x] Rutas `/`, `/triaje/[id]`, `/historial`, `/auditoria`, `/faq`
- [ ] Diseño aplicado en `/` y `/triaje/[id]`
- [ ] Integración con el backend real

## Documentación adicional

- [Decisiones de arquitectura](docs/ARQUITECTURA.md)
