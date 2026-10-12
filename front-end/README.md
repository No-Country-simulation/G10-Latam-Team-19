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
| `npm test` | Pruebas unitarias con Vitest |

## Rutas

| Ruta | Descripción |
| --- | --- |
| `/` | Carga de documentos (archivo o texto pegado) y panel con pendientes, urgentes y últimos procesados |
| `/dashboard` | Métricas y distribución por prioridad, estado y destino |
| `/triaje/[id]` | Detalle de un triaje: clasificación, paciente, datos clínicos, signos vitales y enrutamiento |
| `/historial` | Todos los documentos procesados, con búsqueda (`?q=`) |
| `/auditoria` | Cola de auditoría humana con acciones Aprobar / Rechazar |
| `/faq` | Preguntas frecuentes |

## Estructura

```text
front-end/
├── app/               # Rutas (App Router), server actions, error.tsx y not-found.tsx
├── components/        # Componentes propios; ui/ contiene los de shadcn/ui
├── lib/
│   ├── api.ts         # Única puerta de acceso a datos: elige backend real o modo demo
│   ├── triajes/       # Repositorios (http, memoria), adaptador, consultas y sus pruebas
│   ├── validacion.ts  # Validación de entradas de formularios y server actions
│   ├── archivos.ts    # Reglas de los archivos que se pueden cargar
│   ├── formato.ts     # Fechas y etiquetas legibles
│   └── mocks/         # Datos de ejemplo del modo demo
├── types/triage.ts    # Tipos derivados del contrato del backend
└── docs/              # Decisiones de arquitectura
```

## Datos y contrato con el backend

- El contrato es `schemas.py` (raíz del repositorio). Los tipos de `types/triage.ts` se derivan de él: los `Optional` de Pydantic son `T | null` y los enums son arreglos `as const` con sus valores literales.
- Toda la lectura y escritura de datos pasa por `lib/api.ts`. Apuntar al backend real implica cambiar únicamente esa capa, sin tocar páginas ni componentes.
- **Con `API_URL`** se usa el backend real para todo (listar, detalle, procesar, aprobar y rechazar). Si el backend falla, se muestra una pantalla de error con "Reintentar": no se cae a datos de ejemplo, para no mostrar pacientes ficticios como reales.
- **Sin `API_URL`** la app entra en **modo demo**: datos de ejemplo en memoria (se reinician al reiniciar el servidor) y un aviso visible en la cabecera. Al procesar un documento se devuelve un resultado de ejemplo, no un análisis del texto.
- La carga acepta texto pegado, `.txt`, `.json` y PDF con texto (se extrae en el navegador). Imágenes y PDF escaneados requieren OCR, que el backend aún no ofrece.

Variable de entorno (archivo `.env.local`):

```env
API_URL=http://localhost:8000
```

`API_URL` solo se lee en el servidor. `NEXT_PUBLIC_API_URL` sigue funcionando por compatibilidad, pero se expone al navegador sin necesidad.

## Pruebas

```bash
npm test
```

Las pruebas (Vitest) cubren la lógica sin interfaz: adaptador del contrato, repositorios http y en memoria, consultas y métricas, validación de entradas y reglas de archivos.

## Estado

- [x] Tipos TypeScript derivados de `schemas.py`
- [x] Capa de API con datos mock
- [x] Rutas `/`, `/triaje/[id]`, `/historial`, `/auditoria`, `/faq`
- [x] Diseño aplicado (dirección A del Figma) en todas las rutas
- [x] Integración con el backend real
- [x] Pruebas unitarias de la capa de datos y validación
- [ ] Autenticación y roles (fuera del alcance actual)
- [ ] OCR para imágenes y PDF escaneados (depende del backend)

## Documentación adicional

- [Decisiones de arquitectura](docs/ARQUITECTURA.md)
