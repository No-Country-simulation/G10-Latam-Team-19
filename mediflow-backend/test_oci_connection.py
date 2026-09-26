"""
test_oci_connection.py — Script de prueba y validación de OCI Object Storage.

Este script permite probar la conexión con Oracle Cloud Infrastructure (OCI) Always Free:
1. Verifica la carga de credenciales desde ~/.oci/config o variables de entorno.
2. Consulta el Namespace del Tenancy.
3. Prueba subir un archivo JSON a /recibidos/
4. Prueba descargar el archivo y validar su contenido.
5. Verifica las 4 carpetas prefijo:
   - /recibidos/
   - /procesados/
   - /auditoria_humana/
   - /validados/

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

from app.config import get_settings
from app.schemas import EstadoDocumento
from app.services.oci_storage import CarpetaOCI, OCIStorageService


def probar_oci():
    settings = get_settings()

    print("=" * 65)
    print("🏥 MediFlow — Prueba de Integración con OCI Object Storage")
    print("=" * 65)
    print("🔑 Modo de autenticación:         Variables de Entorno (.env)")
    print(f"👤 OCI User OCID:                {settings.OCI_USER[:25] if settings.OCI_USER else 'NO CONFIGURADO'}...")
    print(f"🏢 OCI Tenancy OCID:             {settings.OCI_TENANCY[:25] if settings.OCI_TENANCY else 'NO CONFIGURADO'}...")
    print(f"🏷️  OCI Fingerprint:              {settings.OCI_FINGERPRINT or 'NO CONFIGURADO'}")
    print(f"🔑 OCI Key File:                 {settings.OCI_KEY_FILE or 'NO CONFIGURADO'}")
    print(f"🪣 Bucket OCI:                   {settings.OCI_BUCKET}")
    print(f"🌍 Región OCI:                   {settings.OCI_REGION}")
    print("-" * 65)

    if not (settings.OCI_USER and settings.OCI_TENANCY and settings.OCI_FINGERPRINT and (settings.OCI_KEY_FILE or settings.OCI_KEY_CONTENT)):
        print("⚠️  AVISO: Faltan variables de OCI en tu archivo .env")
        print("\nℹ️  Asegúrate de tener definidas en tu .env:")
        print("     OCI_TENANCY=ocid1.tenancy.oc1..aaaa...")
        print("     OCI_USER=ocid1.user.oc1..aaaa...")
        print("     OCI_FINGERPRINT=xx:xx:xx...")
        print("     OCI_REGION=sa-santiago-1")
        print("     OCI_KEY_FILE=./oci_api_key.pem")
        print("     OCI_BUCKET=mediflow-documentos-clinicos")
        print("=" * 65)
        return False

    try:
        print("\n1️⃣  Inicializando cliente OCI...")
        storage = OCIStorageService()
        print(f"   ✅ Cliente inicializado exitosamente.")
        print(f"   🏷️  Namespace detectado: {storage.namespace}")
        print(f"   🪣 Bucket configurado:   {storage.bucket}")

        # 2. Prueba de subida
        test_id = f"TEST-DOC-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        test_content = {
            "test_id": test_id,
            "mensaje": "Prueba de integración MediFlow - OCI Always Free",
            "creado_en": datetime.now(timezone.utc).isoformat(),
            "carpetas_soportadas": [c.value for c in CarpetaOCI],
        }

        print(f"\n2️⃣  Subiendo documento de prueba a /recibidos/ ({test_id}.json)...")
        ruta_subida = storage.guardar_json(
            documento_id=test_id,
            contenido=test_content,
            estado=EstadoDocumento.RECIBIDO,
        )
        print(f"   ✅ Archivo subido con éxito a: {ruta_subida}")

        # 3. Prueba de descarga
        print(f"\n3️⃣  Descargando y verificando integridad del archivo...")
        contenido_descargado = storage.descargar_json(ruta_subida)
        assert contenido_descargado["test_id"] == test_id, "El ID del archivo no coincide"
        print(f"   ✅ Archivo descargado e integridad verificada.")
        print(f"   📄 Contenido leído: {json.dumps(contenido_descargado, indent=2)}")

        # 4. Probar creación/subida en las otras 3 carpetas
        print(f"\n4️⃣  Probando guardado en los demás prefijos (/procesados, /auditoria_humana, /validados)...")
        for estado in [EstadoDocumento.PROCESADO, EstadoDocumento.AUDITORIA_HUMANA, EstadoDocumento.VALIDADO]:
            ruta = storage.guardar_json(
                documento_id=f"{test_id}-{estado.value}",
                contenido={"estado": estado.value, "timestamp": datetime.now(timezone.utc).isoformat()},
                estado=estado,
            )
            print(f"   ✅ Subido en prefijo /{estado.value}/ -> {ruta}")

        # 5. Listar objetos en el bucket
        print(f"\n5️⃣  Listando objetos en el bucket...")
        objetos = storage.listar_objetos()
        print(f"   📦 Total de objetos encontrados en el bucket: {len(objetos)}")
        for obj in objetos[:10]:
            print(f"      - {obj}")
        if len(objetos) > 10:
            print(f"      ... y {len(objetos) - 10} más.")

        print("\n" + "=" * 65)
        print("🎉 ¡TODAS LAS PRUEBAS DE OCI OBJECT STORAGE PASARON CON ÉXITO!")
        print("=" * 65)
        return True

    except Exception as exc:
        print(f"\n❌ ERROR durante la prueba de OCI: {exc}")
        print("\n🔍 Posibles causas:")
        print("   - El archivo ~/.oci/config no tiene los permisos o rutas correctas a la clave privada.")
        print("   - El nombre del bucket no existe en tu Tenancy/Compartimento.")
        print("   - Las políticas IAM de OCI no tienen permiso para Object Storage (manage object-family).")
        print("=" * 65)
        return False


if __name__ == "__main__":
    exito = probar_oci()
    sys.exit(0 if exito else 1)
