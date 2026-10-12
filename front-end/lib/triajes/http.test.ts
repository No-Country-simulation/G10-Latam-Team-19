import { describe, expect, it, vi } from "vitest";
import { RespuestaInvalidaError } from "./adaptador";
import { conAuditoria, triageDePrueba } from "./fixtures";
import { ApiError, crearRepositorioHttp } from "./http";

function responder(cuerpo: unknown, status = 200) {
  return vi.fn<typeof fetch>(async () => Response.json(cuerpo, { status }));
}

describe("repositorio http", () => {
  it("lista y adapta los triajes", async () => {
    const fetchFalso = responder([triageDePrueba(), conAuditoria({ documento_id: "DOC-2" })]);
    const lista = await crearRepositorioHttp("http://api/", fetchFalso).listar();

    expect(fetchFalso.mock.calls[0][0]).toBe("http://api/triage");
    expect(lista.map((t) => t.estado)).toEqual(["procesados", "auditoria_humana"]);
  });

  it("no usa datos de ejemplo si el backend falla: propaga el error", async () => {
    const repo = crearRepositorioHttp("http://api", responder({ detail: "boom" }, 500));
    await expect(repo.listar()).rejects.toMatchObject({ name: "ApiError", status: 500 });
  });

  it("no filtra el cuerpo de la respuesta de error en el mensaje", async () => {
    const repo = crearRepositorioHttp("http://api", responder({ detail: "paciente Ana Pérez" }, 500));
    await expect(repo.listar()).rejects.not.toThrow(/Ana/);
  });

  it("convierte un fallo de red en ApiError sin status", async () => {
    const caido = vi.fn<typeof fetch>(async () => {
      throw new TypeError("fetch failed");
    });
    const error = await crearRepositorioHttp("http://api", caido).listar().catch((e) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBeNull();
  });

  it("rechaza una respuesta que no es una lista", async () => {
    const repo = crearRepositorioHttp("http://api", responder({ items: [] }));
    await expect(repo.listar()).rejects.toBeInstanceOf(ApiError);
  });

  it("rechaza un triaje con forma inválida", async () => {
    const repo = crearRepositorioHttp("http://api", responder([{ documento_id: "X" }]));
    await expect(repo.listar()).rejects.toBeInstanceOf(RespuestaInvalidaError);
  });

  it("obtener devuelve null con 404", async () => {
    const repo = crearRepositorioHttp("http://api", responder({ detail: "no existe" }, 404));
    expect(await repo.obtener("DOC-X")).toBeNull();
  });

  it("codifica el ID para que no altere la ruta del backend", async () => {
    const fetchFalso = responder(triageDePrueba());
    await crearRepositorioHttp("http://api", fetchFalso).obtener("../health?x=1");
    expect(fetchFalso.mock.calls[0][0]).toBe("http://api/triage/..%2Fhealth%3Fx%3D1");
  });

  it.each([
    ["aprobado", "aprobar"],
    ["rechazado", "rechazar"],
  ] as const)("resolver %s llama a /%s por POST", async (decision, accion) => {
    const fetchFalso = responder(conAuditoria({ status: "validado" }));
    await crearRepositorioHttp("http://api", fetchFalso).resolver("DOC-1", decision);

    const [url, init] = fetchFalso.mock.calls[0];
    expect(url).toBe(`http://api/triage/DOC-1/${accion}`);
    expect(init?.method).toBe("POST");
  });

  it("resolver falla en vez de simular éxito cuando el backend rechaza la operación", async () => {
    const repo = crearRepositorioHttp("http://api", responder({ detail: "x" }, 409));
    await expect(repo.resolver("DOC-1", "aprobado")).rejects.toMatchObject({ status: 409 });
  });

  it("procesar envía el documento y devuelve el triaje adaptado", async () => {
    const fetchFalso = responder(triageDePrueba({ documento_id: "DOC-9" }));
    const req = {
      documento_id: "DOC-9",
      tipo_archivo: "TEXTO",
      documento_texto: "texto del documento",
      canal_origen: "Laboratorio",
    } as const;
    const t = await crearRepositorioHttp("http://api", fetchFalso).procesar(req);

    expect(JSON.parse(String(fetchFalso.mock.calls[0][1]?.body))).toEqual(req);
    expect(t).toMatchObject({ documento_id: "DOC-9", estado: "procesados" });
  });
});
