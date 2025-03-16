import logging

import requests
import io
import re
import pdfplumber

logger = logging.getLogger(__name__)


def extract_specs_from_pdf_url(pdf_url):
    """
    Extrae especificaciones del PDF Micro Bird G5 y las devuelve como un diccionario estructurado

    Args:
        pdf_url (str): URL del PDF

    Returns:
        dict: Diccionario con especificaciones clave
    """
    # Descargar el PDF desde la URL
    logger.info(f"Descargando PDF desde {pdf_url}...")
    response = requests.get(pdf_url)

    if response.status_code != 200:
        logger.error(f"Error al descargar el PDF. Código de estado: {response.status_code}")
        return None

    # Leer el PDF con pdfplumber
    pdf_data = io.BytesIO(response.content)

    # Diccionario para almacenar las especificaciones
    specs = {
        "body_dimension": {},
        "chassis": {},
        "options": []
    }

    with pdfplumber.open(pdf_data) as pdf:
        full_text = ""
        for page in pdf.pages:
            full_text += page.extract_text() + "\n"

        # Extraer opciones
        options_pattern = r"SCHOOL BUS\s*(.*?)\s*THE INDUSTRY LEADER"
        options_section = re.findall(options_pattern, full_text, re.DOTALL)

        if options_section:
            specs["options"] = options_section[0]

        # Buscar y extraer tablas
        for i, page in enumerate(pdf.pages):
            tables = page.extract_tables()

            for table in tables:
                # Convertir la tabla a texto para buscar palabras clave
                table_text = ' '.join([' '.join([str(cell) for cell in row if cell]) for row in table])

                # Procesar tablas de Body Dimension
                if 'Model' in table_text and ('Exterior' in table_text or 'Max passenger' in table_text):
                    process_table_to_dict(table, specs["body_dimension"])

                # Procesar tablas de Chassis
                if 'Wheelbase' in table_text or 'GVWR' in table_text:
                    process_table_to_dict(table, specs["chassis"])

    # Extraer datos específicos de interés
    result_dict = extract_key_specs(specs)

    return result_dict


def process_table_to_dict(table, target_dict):
    """
    Procesa una tabla y la convierte en un diccionario

    Args:
        table (list): Tabla extraída con pdfplumber
        target_dict (dict): Diccionario donde se almacenarán los datos
    """
    if not table or len(table) < 2:
        return

    # Limpiar la tabla
    clean_table = [['' if cell is None else str(cell).strip() for cell in row] for row in table]

    try:
        for row in clean_table[1:]:
            if row and len(row) > 1 and row[0]:
                param_name = row[0].strip()
                if param_name:
                    param_values = [cell for cell in row[1:] if cell]
                    target_dict[param_name] = param_values
    except Exception as e:
        logger.error(f"Error al procesar tabla: {str(e)}")


def extract_key_specs(specs):
    """
    Extrae especificaciones clave del diccionario y las organiza en un formato amigable

    Args:
        specs (dict): Diccionario con todas las especificaciones

    Returns:
        dict: Diccionario con especificaciones clave organizadas
    """
    result = {}

    # Procesar especificaciones de Body Dimension
    body_dim = specs["body_dimension"]
    result = {key: " ".join(value) for key, value in body_dim.items()}

    # Añadir opciones
    result["options"] = specs.get("options", "")

    return result


def get_micro_bird_specs(pdf_url: str):
    """
    Función principal para obtener las especificaciones del Micro Bird G5

    Args:
        pdf_url (str, optional): URL del PDF.

    Returns:
        dict: Diccionario con especificaciones
    """
    try:
        specs = extract_specs_from_pdf_url(pdf_url)
        return specs
    except Exception as e:
        logger.error(f"Error al extraer especificaciones: {str(e)}")
        return None
