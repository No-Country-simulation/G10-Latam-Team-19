import type { DocumentoClinicoRequest } from "@/types/triage";
import { adaptarTriaje } from "./adaptador";
import type { DecisionAuditoria, RepositorioTriajes, Triaje } from "./tipos";

/** Fallo de red, timeout o respuesta no exitosa del backend. `status` es null si no hubo respuesta. */
export class ApiError extends Error {
  constructor(
    mensaje: string,
    readonly status: number | null,
  ) {
    super(mensaje);
    this.name = "ApiError";
  }
}

const TIMEOUT_LECTURA_MS = 10_000;
/** POST /triage invoca al agente (LLM), que tarda bastante más que una lectura. */
const TIMEOUT_PROCESAR_MS = 60_000;

const ACCION: Record<DecisionAuditoria, string> = { aprobado: "aprobar", rechazado: "rechazar" };

export function crearRepositorioHttp(
  baseUrl: string,
  fetchImpl: typeof fetch = fetch,
): RepositorioTriajes {
  const base = baseUrl.replace(/\/+$/, "");

  async function pedir(ruta: string, init: RequestInit, timeoutMs: number): Promise<Response> {
    const metodo = init.method ?? "GET";
    try {
      return await fetchImpl(`${base}${ruta}`, {
        ...init,
        cache: "no-store",
        signal: AbortSignal.timeout(timeoutMs),
      });
    } catch {
      throw new ApiError(`${metodo} ${ruta}: sin respuesta del backend`, null);
    }
  }

  // El cuerpo del error se omite a propósito: puede traer datos del paciente o trazas internas.
  function exigirOk(res: Response, metodo: string, ruta: string) {
    if (!res.ok) throw new ApiError(`${metodo} ${ruta} respondió ${res.status}`, res.status);
  }

  const json = (cuerpo: unknown): RequestInit => ({
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(cuerpo),
  });

  return {
    async listar() {
      const res = await pedir("/triage", {}, TIMEOUT_LECTURA_MS);
      exigirOk(res, "GET", "/triage");
      const datos: unknown = await res.json();
      if (!Array.isArray(datos)) throw new ApiError("GET /triage no devolvió una lista", res.status);
      return datos.map(adaptarTriaje);
    },

    async obtener(id) {
      const ruta = `/triage/${encodeURIComponent(id)}`;
      const res = await pedir(ruta, {}, TIMEOUT_LECTURA_MS);
      if (res.status === 404) return null;
      exigirOk(res, "GET", ruta);
      return adaptarTriaje(await res.json());
    },

    async resolver(id, decision): Promise<Triaje | null> {
      const ruta = `/triage/${encodeURIComponent(id)}/${ACCION[decision]}`;
      const res = await pedir(
        ruta,
        json({
          comentario: `Decisión tomada desde interfaz web: ${decision}`,
          revisor: "Auditor MediFlow",
        }),
        TIMEOUT_LECTURA_MS,
      );
      if (res.status === 404) return null;
      exigirOk(res, "POST", ruta);
      return adaptarTriaje(await res.json());
    },

    async procesar(req: DocumentoClinicoRequest) {
      const res = await pedir("/triage", json(req), TIMEOUT_PROCESAR_MS);
      exigirOk(res, "POST", "/triage");
      return adaptarTriaje(await res.json());
    },
  };
}
