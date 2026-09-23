# PRUEBA MANUAL OPCIONAL: ejemplos ficticios para inspeccionar un proveedor real.
# No forma parte del flujo del agente ni reemplaza las pruebas automáticas.
# Al ejecutar este archivo requiere credenciales y consume llamadas al LLM.
import argparse

from pathlib import Path

from dotenv import load_dotenv

from nodes import extraction_node


CASES = {
    "receta": (
        "DOCUMENTO FICTICIO PARA PRUEBAS. "
        "Paciente: Ana Ejemplo, 35 años. "
        "Médico solicitante: Dr. Luis Prueba, matrícula TEST-123. "
        "Diagnóstico principal: rinitis alérgica. "
        "Código CIE-10: J30.4. "
        "Medicamento: loratadina. Dosis: 10 mg una vez al día."
    ),
    "sin_nombre": (
        "DOCUMENTO FICTICIO PARA PRUEBAS. "
        "Informe de laboratorio. Paciente de 42 años. "
        "Nombre del paciente no consignado. "
        "Médico solicitante: Dra. Marta Prueba, matrícula TEST-456. "
        "Estudio realizado: hemograma completo. "
        "No se consigna diagnóstico, código CIE-10 ni tratamiento."
    ),
    "epicrisis": (
        "DOCUMENTO FICTICIO PARA PRUEBAS. "
        "EPICRISIS / INFORME DE ALTA. "
        "Paciente: Elena Ejemplo, 60 años. "
        "Diagnóstico principal al alta: neumonía. "
        "No se consigna código CIE-10. "
        "No se identifica médico solicitante. "
        "No se detallan estudios realizados ni medicamentos al alta."
    ),
}


def main():
    parser = argparse.ArgumentParser(
        description="Prueba manual de extracción con una llamada real al LLM."
    )
    parser.add_argument("caso", choices=CASES)
    args = parser.parse_args()

    load_dotenv(
        Path(__file__).resolve().parent / ".env",
        override=True,
    )

    result = extraction_node({"document_text": CASES[args.caso]})

    print("Caso:", args.caso)
    print(result["extracted_data"].model_dump_json(indent=2))
    print("Campos críticos faltantes:", result["missing_critical_fields"])


if __name__ == "__main__":
    main()
