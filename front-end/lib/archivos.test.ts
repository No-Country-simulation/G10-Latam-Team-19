import { describe, expect, it } from "vitest";
import { clasificarArchivo, extension, formatearTamano, MAX_BYTES } from "./archivos";

describe("extension", () => {
  it("devuelve la extensión en minúsculas", () => expect(extension("Informe.PDF")).toBe(".pdf"));
  it("usa solo el último punto", () => expect(extension("a.b.txt")).toBe(".txt"));
  it("devuelve vacío sin extensión o en archivos ocultos", () => {
    expect(extension("LEEME")).toBe("");
    expect(extension(".env")).toBe("");
  });
});

describe("clasificarArchivo", () => {
  it("lee .txt y .json como texto", () => {
    expect(clasificarArchivo({ name: "a.txt", size: 10 })).toEqual({ clase: "texto", tipo: "TEXTO" });
    expect(clasificarArchivo({ name: "a.json", size: 10 })).toEqual({ clase: "texto", tipo: "JSON" });
  });

  it("marca el PDF para extracción", () => {
    expect(clasificarArchivo({ name: "receta.PDF", size: 10 })).toEqual({ clase: "pdf" });
  });

  it.each(["foto.jpg", "foto.jpeg", "foto.png"])("rechaza la imagen %s porque requiere OCR", (name) => {
    const r = clasificarArchivo({ name, size: 10 });
    expect(r).toMatchObject({ clase: "rechazado" });
    if (r.clase === "rechazado") expect(r.motivo).toMatch(/OCR/);
  });

  it.each(["virus.exe", "macro.docm", "sin-extension", "doble.pdf.exe"])(
    "rechaza el formato de %s",
    (name) => expect(clasificarArchivo({ name, size: 10 }).clase).toBe("rechazado"),
  );

  it("rechaza archivos vacíos", () => {
    expect(clasificarArchivo({ name: "a.txt", size: 0 }).clase).toBe("rechazado");
  });

  it("acepta justo 10 MB y rechaza un byte más", () => {
    expect(clasificarArchivo({ name: "a.pdf", size: MAX_BYTES }).clase).toBe("pdf");
    expect(clasificarArchivo({ name: "a.pdf", size: MAX_BYTES + 1 }).clase).toBe("rechazado");
  });
});

describe("formatearTamano", () => {
  it("muestra KB (mínimo 1) y MB con un decimal", () => {
    expect(formatearTamano(10)).toBe("1 KB");
    expect(formatearTamano(2048)).toBe("2 KB");
    expect(formatearTamano(1024 * 1024 * 2.5)).toBe("2.5 MB");
  });
});
