import { describe, expect, it } from "vitest";
import { etiquetaCanal, etiquetaDestino, formatearFecha } from "./formato";

describe("formatearFecha", () => {
  it("formatea en UTC sin depender de la zona del servidor", () => {
    expect(formatearFecha("2026-09-29T14:32:10Z")).toBe("29/9/26, 14:32");
  });

  it("no rompe con una fecha inválida", () => {
    expect(formatearFecha("no es una fecha")).toBe("—");
  });
});

describe("etiquetaDestino", () => {
  it("traduce los destinos conocidos con tildes", () => {
    expect(etiquetaDestino("Cola_Revision_Humana")).toBe("Cola de Revisión Humana");
  });

  it("muestra legible un destino que el front aún no conoce", () => {
    expect(etiquetaDestino("Nueva_Cola")).toBe("Nueva Cola");
  });
});

describe("etiquetaCanal", () => {
  it("traduce los canales del formulario", () => {
    expect(etiquetaCanal("Guardia_Emergencias")).toBe("Guardia de Emergencias");
  });

  it("muestra legible un canal que no está en la lista", () => {
    expect(etiquetaCanal("Mesa_Entradas")).toBe("Mesa Entradas");
  });

  it("deja igual los canales guardados con el formato anterior", () => {
    expect(etiquetaCanal("Guardia de Emergencias")).toBe("Guardia de Emergencias");
  });
});
