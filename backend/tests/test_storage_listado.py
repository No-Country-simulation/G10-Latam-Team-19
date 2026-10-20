"""Regresión P1: el historial debe combinar R2 y OCI (no quedarse solo con R2)."""
import sys
import types

import pytest

# Stubs de SDKs externos para poder testear sin credenciales ni dependencias instaladas.
for nombre in ("oci", "oci.config", "oci.object_storage", "boto3", "botocore", "botocore.exceptions", "dotenv"):
    if nombre not in sys.modules:
        try:
            __import__(nombre)
        except ImportError:
            sys.modules[nombre] = types.ModuleType(nombre)
sys.modules["botocore.exceptions"].ClientError = getattr(sys.modules["botocore.exceptions"], "ClientError", Exception)
if not hasattr(sys.modules["dotenv"], "load_dotenv"):
    sys.modules["dotenv"].load_dotenv = lambda *a, **k: None

try:
    import pydantic  # noqa: F401
except ImportError:  # entorno sin dependencias: stub mínimo del schema que usa storage.py
    from enum import Enum

    class EstadoDocumento(str, Enum):
        RECIBIDO = "recibidos"
        PROCESADO = "procesados"
        AUDITORIA_HUMANA = "auditoria_humana"
        VALIDADO = "validados"

    stub = types.ModuleType("app.schemas")
    stub.EstadoDocumento = EstadoDocumento
    sys.modules["app.schemas"] = stub

from app.services.storage import StorageProvider  # noqa: E402


class FakeServicio:
    def __init__(self, bucket, docs, falla=False):
        self.bucket, self.docs, self.falla = bucket, docs, falla

    def listar_documentos_triage(self, estado=None):
        if self.falla:
            raise RuntimeError("caído")
        return [d for d in self.docs if estado is None or d[1]["status"] == str(getattr(estado, "value", estado))]


def doc(i, status="procesados", ts="2026-10-20T10:00:00+00:00"):
    return (f"{status}/{i}.json", {"documento_id": i, "status": status, "timestamp": ts})


def proveedor(r2, oci, preferido="r2"):
    p = StorageProvider.__new__(StorageProvider)
    p.settings = types.SimpleNamespace(STORAGE_PROVIDER=preferido)
    p._obtener_r2 = lambda: r2
    p._obtener_oci = lambda: oci
    return p


@pytest.mark.parametrize("preferido", ["r2", "oci"])
def test_combina_r2_y_oci(preferido):
    r2 = FakeServicio("bucket-r2", [doc("DOC-R2-1"), doc("DOC-R2-2")])
    oci = FakeServicio("bucket-oci", [doc("DOC-TEST-ENDPOINT-180722")])
    res = proveedor(r2, oci, preferido).listar_documentos_triage_con_bucket()
    assert {d[1]["documento_id"] for d in res} == {"DOC-R2-1", "DOC-R2-2", "DOC-TEST-ENDPOINT-180722"}
    buckets = {d[1]["documento_id"]: d[2] for d in res}
    assert buckets["DOC-TEST-ENDPOINT-180722"] == "bucket-oci"
    assert buckets["DOC-R2-1"] == "bucket-r2"


def test_duplicado_gana_el_mas_reciente():
    r2 = FakeServicio("r2", [doc("X", "auditoria_humana", "2026-10-20T10:00:00+00:00")])
    oci = FakeServicio("oci", [doc("X", "validados", "2026-10-20T11:00:00+00:00")])
    res = proveedor(r2, oci).listar_documentos_triage()
    assert len(res) == 1 and res[0][1]["status"] == "validados"


def test_filtro_por_estado_en_ambos():
    r2 = FakeServicio("r2", [doc("A", "auditoria_humana"), doc("B", "procesados")])
    oci = FakeServicio("oci", [doc("C", "auditoria_humana")])
    res = proveedor(r2, oci).listar_documentos_triage(estado="auditoria_humana")
    assert {d[1]["documento_id"] for d in res} == {"A", "C"}


def test_un_proveedor_caido_o_ausente_no_rompe():
    r2 = FakeServicio("r2", [], falla=True)
    oci = FakeServicio("oci", [doc("SOLO-OCI")])
    assert len(proveedor(r2, oci).listar_documentos_triage()) == 1
    assert len(proveedor(None, oci).listar_documentos_triage()) == 1


def test_sin_proveedores_levanta_error():
    with pytest.raises(RuntimeError):
        proveedor(None, None).listar_documentos_triage()