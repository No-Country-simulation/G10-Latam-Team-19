import { describe, expect, it, vi } from "vitest";
import { ErrorOcr, transcribirConBackend, validarArchivoOcr } from "./ocr";

const archivo = new Blob([new Uint8Array([1, 2, 3])], { type: "image/png" });

const responder = (cuerpo: unknown, status = 200) =>
  vi.fn<typeof fetch>().mockResolvedValue(new Response(JSON.stringify(cuerpo), { status }));

const fallo = (promesa: Promise<unknown>) => promesa.then(() => null, (e: unknown) => e as ErrorOcr);

describe("transcribirConBackend", () => {
  it("manda el archivo como multipart a POST /ocr y devuelve el texto", async () => {
    const fetchMock = responder({ texto: "Paracetamol 500 mg", paginas: 1, paginas_totales: 1 });
    const r = await transcribirConBackend("http://api.test/", archivo, "receta.png", fetchMock);

    expect(r).toEqual({ texto: "Paracetamol 500 mg", paginas: 1, paginasTotales: 1 });

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("http://api.test/ocr"); // sin barra doble
    expect(init?.method).toBe("POST");
    const form = init?.body as FormData;
    expect((form.get("archivo") as File).name).toBe("receta.png");
  });

  it("informa cuántas páginas se leyeron de un PDF largo", async () => {
    const fetchMock = responder({ texto: "x", paginas: 3, paginas_totales: 8 });
    const r = await transcribirConBackend("http://api.test", archivo, "a.pdf", fetchMock);
    expect([r.paginas, r.paginasTotales]).toEqual([3, 8]);
  });

  it.each([
    [413, "El archivo supera el máximo de 10 MB."],
    [415, "Formato no soportado. Usá una imagen JPG o PNG, o un PDF."],
    [422, "No se encontró texto legible en el documento."],
  ])("muestra tal cual el detalle de los errores del usuario (%i)", async (status, detail) => {
    const e = await fallo(transcribirConBackend("http://api.test", archivo, "a.png", responder({ detail }, status)));
    expect(e).toBeInstanceOf(ErrorOcr);
    expect(e).toMatchObject({ message: detail, estado: status });
  });

  it("no filtra detalles internos de un 503 (variables de entorno, claves)", async () => {
    const e = await fallo(
      transcribirConBackend(
        "http://api.test",
        archivo,
        "a.png",
        responder({ detail: "Configuración del agente inválida: Falta GROQ_API_KEY en el .env" }, 503),
      ),
    );
    expect(e?.estado).toBe(503);
    expect(e?.message).not.toMatch(/GROQ|\.env|API_KEY/);
    expect(e?.message).toMatch(/no está disponible/);
  });

  it("no filtra la excepción del proveedor en un 502", async () => {
    const e = await fallo(
      transcribirConBackend(
        "http://api.test",
        archivo,
        "a.png",
        responder({ detail: "El proveedor de LLM no pudo leer el documento (RuntimeError: 429 …)" }, 502),
      ),
    );
    expect(e?.estado).toBe(502);
    expect(e?.message).not.toMatch(/RuntimeError|429|LLM/);
  });

  it("ignora un detail que no es texto (error de validación de FastAPI)", async () => {
    const e = await fallo(
      transcribirConBackend("http://api.test", archivo, "a.png", responder({ detail: [{ loc: ["body"] }] }, 422)),
    );
    expect(e?.message).toMatch(/No se pudo leer el archivo/);
  });

  it("sin respuesta del backend: estado 0 y mensaje claro", async () => {
    const caido = vi.fn<typeof fetch>().mockRejectedValue(new TypeError("fetch failed"));
    const e = await fallo(transcribirConBackend("http://api.test", archivo, "a.png", caido));
    expect(e).toMatchObject({ estado: 0 });
    expect(e?.message).toMatch(/conexión con el backend/);
  });

  it("una respuesta 200 sin texto es un error, no una transcripción vacía", async () => {
    for (const cuerpo of [{}, { texto: "   " }, { texto: 5 }, null]) {
      const e = await fallo(transcribirConBackend("http://api.test", archivo, "a.png", responder(cuerpo)));
      expect(e).toMatchObject({ estado: 502 });
    }
  });

  it("tolera una respuesta sin JSON válido", async () => {
    const mal = vi.fn<typeof fetch>().mockResolvedValue(new Response("<html>Bad gateway</html>", { status: 502 }));
    const e = await fallo(transcribirConBackend("http://api.test", archivo, "a.png", mal));
    expect(e).toMatchObject({ estado: 502 });
  });
});

describe("validarArchivoOcr", () => {
  it.each(["foto.jpg", "foto.JPEG", "foto.png", "escaneo.pdf"])("acepta %s", (name) => {
    expect(validarArchivoOcr({ name, size: 1000 })).toBeNull();
  });

  it.each(["notas.txt", "datos.json", "virus.exe", "foto.gif"])("rechaza %s con 415", (name) => {
    expect(validarArchivoOcr({ name, size: 1000 })).toMatchObject({ estado: 415 });
  });

  it("rechaza archivos vacíos (422) o demasiado grandes (413), como el backend", () => {
    expect(validarArchivoOcr({ name: "a.jpg", size: 0 })).toMatchObject({ estado: 422, message: expect.stringMatching(/vacío/) });
    expect(validarArchivoOcr({ name: "a.jpg", size: 11 * 1024 * 1024 })).toMatchObject({
      estado: 413,
      message: expect.stringMatching(/10 MB/),
    });
  });
});
