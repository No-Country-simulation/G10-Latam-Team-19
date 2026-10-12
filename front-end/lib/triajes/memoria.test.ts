import { describe, expect, it } from "vitest";
import { conAuditoria, triageDePrueba } from "./fixtures";
import { crearRepositorioMemoria, sembrarTriajes } from "./memoria";

function crear() {
  const almacen = sembrarTriajes([
    triageDePrueba({ documento_id: "DOC-VIEJO", timestamp: "2026-01-01T00:00:00Z" }),
    conAuditoria({ documento_id: "DOC-AUDIT", timestamp: "2026-02-01T00:00:00Z" }),
  ]);
  const repo = crearRepositorioMemoria(
    almacen,
    triageDePrueba(),
    () => new Date("2026-03-01T00:00:00Z"),
  );
  return { almacen, repo };
}

describe("repositorio en memoria", () => {
  it("lista del más reciente al más antiguo sin mutar el almacén", async () => {
    const { almacen, repo } = crear();
    const lista = await repo.listar();
    expect(lista.map((t) => t.documento_id)).toEqual(["DOC-AUDIT", "DOC-VIEJO"]);
    expect(almacen[0].documento_id).toBe("DOC-VIEJO");
  });

  it("devuelve null si el documento no existe", async () => {
    const { repo } = crear();
    expect(await repo.obtener("NO-EXISTE")).toBeNull();
    expect(await repo.resolver("NO-EXISTE", "aprobado")).toBeNull();
  });

  it("aprobar valida el documento", async () => {
    const { repo } = crear();
    await repo.resolver("DOC-AUDIT", "aprobado");
    expect(await repo.obtener("DOC-AUDIT")).toMatchObject({
      estado: "validados",
      decision_auditoria: "aprobado",
    });
  });

  it("rechazar registra la decisión y lo deja en auditoría", async () => {
    const { repo } = crear();
    await repo.resolver("DOC-AUDIT", "rechazado");
    expect(await repo.obtener("DOC-AUDIT")).toMatchObject({
      estado: "auditoria_humana",
      decision_auditoria: "rechazado",
    });
  });

  it("procesar guarda el documento nuevo y queda consultable", async () => {
    const { repo } = crear();
    const nuevo = await repo.procesar({
      documento_id: "DOC-NUEVO",
      tipo_archivo: "PDF",
      documento_texto: "texto del documento",
      canal_origen: "Farmacia",
    });
    expect(nuevo).toMatchObject({
      documento_id: "DOC-NUEVO",
      canal_origen: "Farmacia",
      timestamp: "2026-03-01T00:00:00.000Z",
    });
    expect((await repo.listar())[0].documento_id).toBe("DOC-NUEVO");
    expect(await repo.obtener("DOC-NUEVO")).not.toBeNull();
  });
});
