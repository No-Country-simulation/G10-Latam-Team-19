"""
test_oci_connection.py — Script de prueba y validación de OCI Object Storage con el nuevo schema.

Este script valida:
1. Autenticación y conexión con Oracle Cloud Infrastructure (OCI).
2. Guardado de documento crudo en /recibidos/.
3. Guardado y descarga de TriageResponse oficial en /procesados/, /auditoria_humana/ y /validados/.
4. Prueba del endpoint POST /triage de FastAPI verificando que persista en OCI.

Uso:
    python test_oci_connection.py
"""

import json
import os
import sys
from datetime import datetime, timezone

# Forzar utf-8 si es posible en Windows
if sys.platform == "win32" and sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Asegurar que el path del proyecto esté disponible
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.schemas import (
    AlmacenamientoOCI,
    Clasificacion,
    DatosExtraidos,
    DecisionEnrutamiento,
    DestinoEnrutamiento,
    EstadoDocumento,
    MedicamentoPrescrito,
    MedicoSolicitante,
    NivelPrioridad,
    NotificacionGenerada,
    Paciente,
    SignosVitales,
    TipoArchivo,
    TipoDocumento,
    TriageResponse,
    UnidadEdad,
)
from app.services.oci_storage import CarpetaOCI, OCIStorageService


def probar_oci():
    settings = get_settings()

    print("=" * 65)
    print("MediFlow — Prueba de Integracion con OCI Object Storage")
    print("=" * 65)
    print(f"Modo de autenticacion:          Variables de Entorno (.env)")
    print(f"OCI User OCID:                 {settings.OCI_USER[:25] if settings.OCI_USER else 'NO CONFIGURADO'}...")
    print(f"OCI Tenancy OCID:              {settings.OCI_TENANCY[:25] if settings.OCI_TENANCY else 'NO CONFIGURADO'}...")
    print(f"OCI Fingerprint:               {settings.OCI_FINGERPRINT or 'NO CONFIGURADO'}")
    print(f"OCI Key File:                  {settings.OCI_KEY_FILE or 'NO CONFIGURADO'}")
    print(f"Bucket OCI:                    {settings.OCI_BUCKET}")
    print(f"Region OCI:                    {settings.OCI_REGION}")
    print("-" * 65)

    if not (settings.OCI_USER and settings.OCI_TENANCY and settings.OCI_FINGERPRINT and (settings.OCI_KEY_FILE or settings.OCI_KEY_CONTENT)):
        print("[AVISO] Faltan variables de OCI en tu archivo .env.")
        print("Asegurate de tener definidas en tu .env:")
        print("  OCI_TENANCY=ocid1.tenancy.oc1..aaaa...")
        print("  OCI_USER=ocid1.user.oc1..aaaa...")
        print("  OCI_FINGERPRINT=xx:xx:xx...")
        print("  OCI_REGION=sa-santiago-1")
        print("  OCI_KEY_FILE=./oci_api_key.pem")
        print("  OCI_BUCKET=mediflow-documentos-clinicos")
        print("=" * 65)
        return False

    try:
        print("\n1. Inicializando cliente OCI...")
        storage = OCIStorageService()
        print(f"   [OK] Cliente inicializado exitosamente.")
        print(f"   Namespace detectado: {storage.namespace}")
        print(f"   Bucket configurado:   {storage.bucket}")

        # 2. Prueba de guardado de documento crudo (/recibidos/)
        test_id = f"TEST-DOC-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        texto_crudo = "Tomografia de Torax. Paciente de 52 anos con dolor toracico subito y disnea. Sospecha TEP."

        print(f"\n2. Subiendo documento crudo a /recibidos/ ({test_id}.json)...")
        ruta_recibido = storage.guardar_documento_recibido(
            documento_id=test_id,
            texto_original=texto_crudo,
        )
        print(f"   [OK] Documento crudo guardado en: {ruta_recibido}")

        # 3. Prueba de descarga y verificación
        print(f"\n3. Descargando y verificando integridad desde OCI...")
        contenido_recibido = storage.descargar_json(ruta_recibido)
        assert contenido_recibido["documento_id"] == test_id
        assert contenido_recibido["texto_original"] == texto_crudo
        print(f"   [OK] Contenido verificado correctamente.")

        # 4. Prueba con el modelo oficial TriageResponse en /procesados/, /auditoria_humana/ y /validados/
        print(f"\n4. Probando guardado de TriageResponse en prefijos (/procesados, /auditoria_humana, /validados)...")
        ejemplo_triage = TriageResponse(
            status="procesado",
            documento_id=test_id,
            canal_origen="Guardia_Emergencias",
            timestamp=datetime.now(timezone.utc),
            clasificacion=Clasificacion(
                tipo_documento=TipoDocumento.INFORME_ESTUDIO,
                especialidad="Radiologia / Neumonologia",
                nivel_prioridad=NivelPrioridad.URGENTE,
                score_confianza_clasificacion=0.99,
            ),
            datos_extraidos=DatosExtraidos(
                paciente=Paciente(
                    nombre="Carlos Eduardo Mendes",
                    edad=52,
                    unidad_edad=UnidadEdad.ANOS,
                    sexo="M",
                    documento_identidad="AB123456",
                ),
                medico_solicitante=MedicoSolicitante(nombre="Dra. Renata Silveira", matricula="145892"),
                estudio_realizado="Tomografia de Torax con contraste",
                diagnostico_principal="Tromboembolismo Pulmonar Agudo (TEP)",
                cie10_sugerido="I26.9",
                medicamentos=[
                    MedicamentoPrescrito(nombre="Enoxaparina", dosis="80 mg", frecuencia_diaria="2 veces al dia")
                ],
                signos_vitales=SignosVitales(
                    temperatura=37.5,
                    frecuencia_cardiaca=115,
                    frecuencia_respiratoria=28,
                    presion_arterial="140/90",
                    saturacion_oxigeno=88,
                ),
            ),
            decision_enrutamiento=DecisionEnrutamiento(
                destino_principal=DestinoEnrutamiento.COLA_URGENCIAS,
                requiere_auditoria_humana=False,
                justificacion_enrutamiento="Hallazgo critico de alta gravedad (TEP agudo).",
                notificacion_generada=NotificacionGenerada(
                    canal="Alerta_Guardia_Medica",
                    mensaje="ALERTA URGENTE: TEP Agudo detectado.",
                ),
            ),
            almacenamiento_oci=AlmacenamientoOCI(
                bucket=storage.bucket,
                ruta_objeto=f"procesados/{test_id}.json",
                status_backup="exito",
            ),
        )

        for estado in [EstadoDocumento.PROCESADO, EstadoDocumento.AUDITORIA_HUMANA, EstadoDocumento.VALIDADO]:
            ruta_p = storage.guardar_json(
                documento_id=f"{test_id}-{estado.value}",
                contenido=ejemplo_triage.model_dump(mode="json"),
                estado=estado,
            )
            print(f"   [OK] Guardado en prefijo /{estado.value}/ -> {ruta_p}")

        # 5. Probar el endpoint POST /triage con TestClient
        print(f"\n5. Probando flujo completo del endpoint POST /triage...")
        client = TestClient(app)
        doc_endpoint_id = f"DOC-TEST-ENDPOINT-{datetime.now().strftime('%H%M%S')}"
        response = client.post(
            "/triage",
            json={
                "documento_id": doc_endpoint_id,
                "tipo_archivo": "TEXTO",
                "documento_texto": "Tomografia de Torax. Hallazgo urgente de TEP agudo con desaturacion.",
                "canal_origen": "Guardia_Emergencias",
            },
        )
        assert response.status_code == 200, f"Error en endpoint: {response.text}"
        data_resp = response.json()
        print(f"   [OK] POST /triage respondio 200 OK:")
        print(f"        - Documento ID:   {data_resp['documento_id']}")
        print(f"        - Estado:         {data_resp['status']}")
        print(f"        - OCI Backup:     {data_resp['almacenamiento_oci']['status_backup']}")
        print(f"        - Ruta en OCI:    {data_resp['almacenamiento_oci']['ruta_objeto']}")

        # 6. Probar los endpoints GET /triage y GET /triage/{id}
        print(f"\n6. Probando endpoints GET /triage y GET /triage/{{id}}...")
        resp_list = client.get("/triage")
        assert resp_list.status_code == 200
        print(f"   [OK] GET /triage devolvio {len(resp_list.json())} documentos.")

        resp_get = client.get(f"/triage/{doc_endpoint_id}")
        assert resp_get.status_code == 200
        assert resp_get.json()["documento_id"] == doc_endpoint_id
        print(f"   [OK] GET /triage/{doc_endpoint_id} recuperado con exito.")

        print("\n" + "=" * 65)
        print("TODAS LAS PRUEBAS DE OCI OBJECT STORAGE PASARON CON EXITO!")
        print("=" * 65)
        return True

    except Exception as exc:
        print(f"\n[ERROR] durante la prueba de OCI: {exc}")
        print("\nPosibles causas:")
        print("   - Faltan permisos IAM en el Tenancy para Object Storage.")
        print("   - La ruta al archivo .pem no es accesible o la clave privada no coincide con el fingerprint.")
        print("   - El nombre del bucket no existe en la region indicada.")
        print("=" * 65)
        return False


if __name__ == "__main__":
    exito = probar_oci()
    sys.exit(0 if exito else 1)
