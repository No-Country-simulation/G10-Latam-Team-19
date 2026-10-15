import type { TriageResponse } from "@/types/triage";
import { adaptarTriaje } from "./adaptador";
import type { RepositorioTriajes, Triaje } from "./tipos";

export function sembrarTriajes(semilla: TriageResponse[]): Triaje[] {
  return semilla.map(adaptarTriaje);
}

/**
 * Modo demo: guarda los triajes en el arreglo recibido (se pierde al reiniciar el servidor).
 * `plantilla` es el resultado que se devuelve al procesar: aquí no hay agente que analice el texto.
 */
export function crearRepositorioMemoria(
  almacen: Triaje[],
  plantilla: TriageResponse,
  ahora: () => Date = () => new Date(),
): RepositorioTriajes {
  const buscar = (id: string) => almacen.find((t) => t.documento_id === id) ?? null;

  return {
    async listar() {
      return [...almacen].sort((a, b) => b.timestamp.localeCompare(a.timestamp));
    },

    async obtener(id) {
      return buscar(id);
    },

    async resolver(id, decision) {
      const triaje = buscar(id);
      if (!triaje) return null;
      triaje.decision_auditoria = decision;
      if (decision === "aprobado") triaje.estado = "validados";
      return triaje;
    },

    async procesar(req) {
      const nuevo = adaptarTriaje({
        ...plantilla,
        documento_id: req.documento_id,
        canal_origen: req.canal_origen,
        timestamp: ahora().toISOString(),
      });
      almacen.push(nuevo);
      return nuevo;
    },
  };
}
