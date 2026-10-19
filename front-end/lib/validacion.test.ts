import { describe, expect, it } from "vitest";
import {
  esDecisionAuditoria,
  esIdDocumento,
  MAX_TEXTO,
  validarCarga,
} from "./validacion";

const valida = { texto: "Paciente con fiebre de 39 grados", canal: "Laboratorio", tipo: "TEXTO" };

describe("validarCarga", () => {
  it("acepta una carga válida y recorta el texto", () => {
    expect(validarCarga({ ...valida, texto: `  ${valida.texto}  ` })).toEqual({
      ok: true,
      datos: { documento_texto: valida.texto, canal_origen: "Laboratorio", tipo_archivo: "TEXTO" },
    });
  });

  it("envía el canal en el formato del agente", () => {
    const r = validarCarga({ ...valida, canal: "Guardia_Emergencias" });
    expect(r.ok && r.datos.canal_origen).toBe("Guardia_Emergencias");
  });

  it.each(["JSON", "PDF"])("acepta el tipo %s", (tipo) => {
    expect(validarCarga({ ...valida, tipo }).ok).toBe(true);
  });

  it.each([
    ["texto corto", { texto: "hola" }],
    ["solo espacios", { texto: "                " }],
    ["texto ausente", { texto: null }],
    ["un archivo en lugar de texto", { texto: new Blob(["contenido largo"]) }],
    ["texto demasiado largo", { texto: "a".repeat(MAX_TEXTO + 1) }],
    ["canal fuera de la lista", { canal: "Canal inventado" }],
    ["canal con el texto visible en lugar del valor", { canal: "Guardia de Emergencias" }],
    ["canal heredado del prototipo de objetos", { canal: "toString" }],
    ["canal ausente", { canal: null }],
    ["tipo IMAGEN (requiere OCR)", { tipo: "IMAGEN" }],
    ["tipo desconocido", { tipo: "EXE" }],
  ])("rechaza %s", (_nombre, cambio) => {
    const r = validarCarga({ ...valida, ...cambio });
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.error).not.toBe("");
  });

  it("acepta exactamente el máximo de caracteres", () => {
    expect(validarCarga({ ...valida, texto: "a".repeat(MAX_TEXTO) }).ok).toBe(true);
  });
});

describe("esDecisionAuditoria", () => {
  it("acepta solo aprobado y rechazado", () => {
    expect(esDecisionAuditoria("aprobado")).toBe(true);
    expect(esDecisionAuditoria("rechazado")).toBe(true);
    expect(esDecisionAuditoria("aprobar")).toBe(false);
    expect(esDecisionAuditoria(undefined)).toBe(false);
  });
});

describe("esIdDocumento", () => {
  it("acepta los IDs del backend y los generados por el front", () => {
    expect(esIdDocumento("DOC-CLIN-2026-8942")).toBe(true);
    expect(esIdDocumento("DOC-3f2b1c9e-7a4d-4c1b-9f0e-2d6a8b5c4e11")).toBe(true);
  });

  it.each(["", "../health", "DOC 1", "DOC/1", "DOC?x=1", "a".repeat(81), 42, null])(
    "rechaza %j",
    (valor) => expect(esIdDocumento(valor)).toBe(false),
  );
});
