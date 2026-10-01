# 🏥 MediFlow Backend

Backend para el pipeline autónomo de triaje, extracción y enrutamiento inteligente de documentos clínicos desarrollado con **FastAPI** y **Oracle Cloud Infrastructure (OCI) Object Storage** (capa Always Free).

---

## 🎯 Objetivos y Estado Actual

- **Endpoint Autónomo:** `POST /triage` recibe `DocumentoClinicoRequest` y responde con una estructura tipada `TriageResponse` mockeada, permitiendo al resto del equipo (Frontend / Datos / Agente) trabajar e integrarse sin bloqueos.
- **Persistencia en OCI Object Storage:**
  - `/recibidos/`: Guarda el documento crudo apenas ingresa al sistema.
  - `/procesados/`: Almacena el JSON con el resultado de triaje procesado.
  - `/auditoria_humana/`: Casos derivados a revisión humana.
  - `/validados/`: Casos auditados y aprobados por personal médico.

---

## 📋 Requisitos Previos

- **Python:** 3.10 o superior (recomendado 3.11 o 3.12).
- **Cuenta en Oracle Cloud (OCI):** Capa *Always Free* con un bucket de Object Storage creado (por defecto `mediflow-documentos-clinicos`).

---

## 🚀 Instalación y Puesta en Marcha Local

### 1. Clonar el repositorio
```bash
git clone <URL_DEL_REPOSITORIO>
cd mediflow-backend
```

### 2. Crear y activar entorno virtual
- **En Windows (PowerShell):**
  ```powershell
  python -m venv venv
  .\venv\Scripts\Activate.ps1
  ```
- **En Linux / macOS:**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

---

## ⚙️ Configuración de Variables de Entorno y OCI

### 1. Variables de Entorno (`.env`)
Copia el archivo `.env.example` a `.env`:
```bash
copy .env.example .env     # En Windows
# cp .env.example .env     # En Linux/macOS
```

### 2. Configurar credenciales de Oracle Cloud (OCI) en `.env`

Copia tu archivo de clave privada `.pem` en la carpeta del proyecto (o define su ruta) y completa tu archivo `.env`:

```env
ENV=development

# OCI Object Storage
OCI_BUCKET=mediflow-documentos-clinicos
OCI_NAMESPACE=axcqfz4mzit6
OCI_REGION=sa-santiago-1

# Credenciales de API Key
OCI_USER=ocid1.user.oc1..aaaa...
OCI_FINGERPRINT=xx:xx:xx:xx:...
OCI_TENANCY=ocid1.tenancy.oc1..aaaa...
OCI_KEY_FILE=./oci_api_key.pem
```

*(Nota: Tanto `.env` como `*.pem` están protegidos en `.gitignore` para nunca subirse a GitHub).*

### 3. Probar la conexión con OCI
Ejecuta el script de verificación para validar que tus credenciales del `.env` funcionan correctamente:
```bash
python test_oci_connection.py
```
Este script prueba la conexión, sube un archivo de prueba a `/recibidos/`, lo descarga para validar integridad y prueba los 4 prefijos del bucket.

---

## 🏃‍♂️ Ejecutar el Servidor FastAPI

Inicia el servidor con recarga automática:
```bash
uvicorn app.main:app --reload --port 8000
```

El backend estará disponible en:
- **API Base:** `http://localhost:8000`
- **Health Check:** `http://localhost:8000/health`
- **Documentación Interactiva (Swagger UI):** `http://localhost:8000/docs`
- **Documentación ReDoc:** `http://localhost:8000/redoc`

---

## 🧪 Cómo Probar el Endpoint `POST /triage`

### Opción A: Desde Swagger UI (`/docs`)
1. Abre en tu navegador `http://localhost:8000/docs`.
2. Expande el endpoint `POST /triage`.
3. Haz clic en **Try it out**.
4. Envía el siguiente JSON de prueba:
   ```json
   {
     "documento_id": "DOC-CLIN-2026-8942",
     "tipo_archivo": "TEXTO",
     "documento_texto": "Tomografia de Torax con contraste. Se evidencia tromboembolismo pulmonar agudo en rama principal derecha.",
     "canal_origen": "Guardia_Emergencias"
   }
   ```
5. Haz clic en **Execute** y verifica la respuesta `200 OK` con el modelo `TriageResponse`.

### Opción B: Desde Terminal (cURL / PowerShell)
```powershell
curl -X POST "http://localhost:8000/triage" `
     -H "Content-Type: application/json" `
     -d '{
       "documento_id": "DOC-CLIN-2026-8942",
       "tipo_archivo": "TEXTO",
       "documento_texto": "Tomografia de Torax con contraste. Se evidencia tromboembolismo pulmonar agudo en rama principal derecha.",
       "canal_origen": "Guardia_Emergencias"
     }'
```

---

## 📁 Estructura del Código

```text
app/
├── schemas.py           # Schemas oficiales Pydantic (DocumentoClinicoRequest, TriageResponse, Enums)
├── config.py            # Gestión centralizada de configuración mediante Settings
├── main.py              # Aplicación FastAPI, CORS y definición de endpoint POST /triage
└── services/
    └── oci_storage.py   # Servicio de integración con OCI Object Storage y prefijos
```
