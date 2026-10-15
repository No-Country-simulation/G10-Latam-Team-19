import { describe, expect, it } from "vitest";
import { adaptarTriaje, esTriageResponse, RespuestaInvalidaError } from "./adaptador";
import { conAuditoria, triageDePrueba } from "./fixtures";

describe("adaptarTriaje", () => {
  it("marca como procesado un documento que no requiere auditoría", () => {
    const t = adaptarTriaje(triageDePrueba());
    expect(t.estado).toBe("procesados");
    expect(t.decision_auditoria).toBeNull();
  });

  it("envía a auditoría humana cuando el agente lo pide", () => {
    expect(adaptarTriaje(conAuditoria()).estado).toBe("auditoria_humana");
  });

  it("traduce status validado a estado validados + decisión aprobado", () => {
    const t = adaptarTriaje(conAuditoria({ status: "validado" }));
    expect(t).toMatchObject({ estado: "validados", decision_auditoria: "aprobado" });
  });

  it("deja el rechazado en auditoría pero con la decisión registrada", () => {
    const t = adaptarTriaje(conAuditoria({ status: "rechazado" }));
    expect(t).toMatchObject({ estado: "auditoria_humana", decision_auditoria: "rechazado" });
  });

  it("respeta estado y decisión cuando el backend ya los envía", () => {
    const t = adaptarTriaje({ ...triageDePrueba(), estado: "validados", decision_auditoria: "aprobado" });
    expect(t).toMatchObject({ estado: "validados", decision_auditoria: "aprobado" });
  });

  it("ignora un estado desconocido y lo infiere", () => {
    const t = adaptarTriaje({ ...triageDePrueba(), estado: "borrado", decision_auditoria: "quizás" });
    expect(t).toMatchObject({ estado: "procesados", decision_auditoria: null });
  });

  it.each([
    ["null", null],
    ["un texto", "error interno"],
    ["una lista", []],
    ["un objeto sin id", { ...triageDePrueba(), documento_id: "" }],
    ["sin clasificación", { ...triageDePrueba(), clasificacion: null }],
    ["confianza no numérica", {
      ...triageDePrueba(),
      clasificacion: { ...triageDePrueba().clasificacion, score_confianza_clasificacion: "0.9" },
    }],
    ["sin paciente", { ...triageDePrueba(), datos_extraidos: {} }],
  ])("rechaza %s", (_nombre, valor) => {
    expect(esTriageResponse(valor)).toBe(false);
    expect(() => adaptarTriaje(valor)).toThrow(RespuestaInvalidaError);
  });
});
