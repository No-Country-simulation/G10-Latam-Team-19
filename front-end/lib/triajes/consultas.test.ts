import { describe, expect, it } from "vitest";
import { adaptarTriaje } from "./adaptador";
import {
  buscarTriajes,
  contarPor,
  filtrarPendientesAuditoria,
  porcentaje,
  resumirTriajes,
} from "./consultas";
import { conAuditoria, triageDePrueba } from "./fixtures";

const rutina = adaptarTriaje(triageDePrueba({ documento_id: "DOC-A" }));
const urgente = adaptarTriaje(
  triageDePrueba({
    documento_id: "DOC-B",
    clasificacion: {
      tipo_documento: "Informe de Estudio",
      especialidad: "Radiología",
      nivel_prioridad: "Urgente",
      score_confianza_clasificacion: 1,
    },
  }),
);
const pendiente = adaptarTriaje(conAuditoria({ documento_id: "DOC-C" }));
const rechazado = adaptarTriaje(conAuditoria({ documento_id: "DOC-D", status: "rechazado" }));
const aprobado = adaptarTriaje(conAuditoria({ documento_id: "DOC-E", status: "validado" }));

describe("filtrarPendientesAuditoria", () => {
  it("deja solo los que esperan decisión", () => {
    const ids = filtrarPendientesAuditoria([rutina, pendiente, rechazado, aprobado]).map(
      (t) => t.documento_id,
    );
    expect(ids).toEqual(["DOC-C"]);
  });
});

describe("buscarTriajes", () => {
  const todos = [rutina, urgente];

  it("devuelve todo si la consulta está vacía o son espacios", () => {
    expect(buscarTriajes(todos, "")).toBe(todos);
    expect(buscarTriajes(todos, "   ")).toBe(todos);
  });

  it("busca por ID, paciente o tipo sin distinguir mayúsculas", () => {
    expect(buscarTriajes(todos, "doc-b")).toEqual([urgente]);
    expect(buscarTriajes(todos, "ANA")).toEqual(todos);
    expect(buscarTriajes(todos, "informe de estudio")).toEqual([urgente]);
  });

  it("devuelve vacío si nada coincide", () => {
    expect(buscarTriajes(todos, "inexistente")).toEqual([]);
  });
});

describe("porcentaje", () => {
  it("redondea al entero", () => expect(porcentaje(1, 3)).toBe(33));
  it("no divide por cero", () => expect(porcentaje(0, 0)).toBe(0));
});

describe("contarPor", () => {
  it("agrupa por clave", () => {
    const conteo = contarPor(["a", "b", "a"], (x) => x);
    expect([...conteo]).toEqual([["a", 2], ["b", 1]]);
  });
});

describe("resumirTriajes con la forma REAL del backend", () => {
  const aprobadoReal = adaptarTriaje({
    ...triageDePrueba({ documento_id: "DOC-R1", status: "validados" as never }),
    decision_auditoria: "aprobado",
  });
  const rechazadoReal = adaptarTriaje({
    ...conAuditoria({ documento_id: "DOC-R2", status: "auditoria_humana" as never }),
    decision_auditoria: "rechazado",
  });

  it("cuenta como intervención los casos ya revisados, aunque requiere_auditoria_humana sea false", () => {
    const r = resumirTriajes([rutina, urgente, aprobadoReal, rechazadoReal]);
    expect(r.pctConIntervencion).toBe(50);
    expect(r.pctResueltosPorAgente).toBe(50);
  });
});

describe("resumirTriajes", () => {
  it("devuelve ceros sin documentos", () => {
    expect(resumirTriajes([])).toEqual({
      total: 0,
      urgentes: 0,
      pendientesAuditoria: 0,
      pctResueltosPorAgente: 0,
      pctConIntervencion: 0,
      confianzaMedia: 0,
    });
  });

  it("calcula las métricas del dashboard", () => {
    // 4 documentos: 2 sin auditoría, 2 con auditoría (1 pendiente, 1 aprobado).
    expect(resumirTriajes([rutina, urgente, pendiente, aprobado])).toEqual({
      total: 4,
      urgentes: 1,
      pendientesAuditoria: 1,
      pctResueltosPorAgente: 50,
      pctConIntervencion: 50,
      confianzaMedia: 93, // (0.9 + 1 + 0.9 + 0.9) / 4 = 0.925
    });
  });
});
