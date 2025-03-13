import re
from typing import Dict, Any, Tuple, List, Optional

# Definiciones de restricciones basadas en el esquema
FIELD_CONSTRAINTS = {
    "title": {"type": str, "max_length": 256},
    "year": {"type": str, "max_length": 10, "pattern": r"^\d{4}$"},
    "make": {"type": str, "max_length": 25},
    "model": {"type": str, "max_length": 50},
    "engine": {"type": str, "max_length": 60},
    "transmission": {"type": str, "max_length": 60},
    "mileage": {"type": str, "max_length": 100},
    "passengers": {"type": str, "max_length": 60},
    "wheelchair": {"type": str, "max_length": 60},
    "price": {"type": str, "max_length": 30},
    "cprice": {"type": str, "max_length": 30},
    "vin": {"type": str, "max_length": 60, "pattern": r"^[A-HJ-NPR-Z0-9]{17}$", "required": False},
    "source_url": {"type": str, "max_length": 1000},
    "location": {"type": str, "max_length": 30},
    "us_region": {"type": str, "max_length": 10,
                  "allowed_values": ["NORTHEAST", "MIDWEST", "WEST", "SOUTHWEST", "SOUTHEAST", "OTHER"]},
    "airconditioning": {"type": str, "allowed_values": ["REAR", "DASH", "BOTH", "OTHER", "NONE"]}
}


def validate_string_field(field_name: str, value: Any, constraints: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Valida un campo de tipo string.

    Args:
        field_name: Nombre del campo.
        value: Valor a validar.
        constraints: Restricciones del campo.

    Returns:
        Tupla (válido, mensaje_error).
    """
    # Si el campo es None y no es requerido, es válido
    if value is None and not constraints.get("required", False):
        return True, None

    # Si el campo es None pero es requerido, es inválido
    if value is None and constraints.get("required", False):
        return False, f"El campo {field_name} es requerido"

    # Verificar tipo
    if not isinstance(value, constraints.get("type", str)):
        return False, f"El campo {field_name} debe ser de tipo {constraints.get('type', str).__name__}"

    # Verificar longitud máxima
    max_length = constraints.get("max_length")
    if max_length and len(value) > max_length:
        return False, f"El campo {field_name} excede la longitud máxima de {max_length} caracteres"

    # Verificar patrón
    pattern = constraints.get("pattern")
    if pattern and not re.match(pattern, value):
        return False, f"El campo {field_name} no coincide con el patrón requerido: {pattern}"

    # Verificar valores permitidos
    allowed_values = constraints.get("allowed_values")
    if allowed_values and value not in allowed_values:
        return False, f"El campo {field_name} debe ser uno de: {', '.join(allowed_values)}"

    return True, None


def validate_bus_data(bus_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Valida los datos de un autobús antes de insertarlos en la base de datos.

    Args:
        bus_data: Diccionario con datos del autobús.

    Returns:
        Tupla (válido, lista_errores).
    """
    errors = []

    # Obtener información del autobús
    bus_info = bus_data.get("bus_info", {})

    # Verificar que bus_info exista y tenga datos
    if not bus_info:
        return False, ["No se proporcionó información básica del autobús"]

    # Verificar campos requeridos mínimos
    required_fields = ["title", "source_url"]
    for field in required_fields:
        if field not in bus_info or not bus_info[field]:
            errors.append(f"El campo {field} es requerido")

    # Validar cada campo según las restricciones
    for field_name, constraints in FIELD_CONSTRAINTS.items():
        if field_name in bus_info:
            is_valid, error_msg = validate_string_field(field_name, bus_info[field_name], constraints)
            if not is_valid:
                errors.append(error_msg)

    # Validación específica: Si hay precio de visualización, debe haber precio calculado
    if "price" in bus_info and bus_info["price"] and "cprice" not in bus_info:
        errors.append("Si hay precio de visualización, debe haber un precio calculado")

    # Validar campo de región de EE.UU.
    if "us_region" in bus_info:
        region = bus_info["us_region"]
        valid_regions = ["NORTHEAST", "MIDWEST", "WEST", "SOUTHWEST", "SOUTHEAST", "OTHER"]
        if region not in valid_regions:
            errors.append(f"Región de EE.UU. inválida. Debe ser uno de: {', '.join(valid_regions)}")

    # Validar campos booleanos
    boolean_fields = ["published", "featured", "sold", "scraped", "draft", "luggage", "score"]
    for field in boolean_fields:
        if field in bus_info and not isinstance(bus_info[field], bool) and bus_info[field] not in (0, 1):
            errors.append(f"El campo {field} debe ser un valor booleano (True/False o 0/1)")

    return len(errors) == 0, errors


def clean_bus_data(bus_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Limpia y normaliza los datos del autobús.

    Args:
        bus_data: Diccionario con datos del autobús.

    Returns:
        Diccionario con datos limpios.
    """
    cleaned_data = {"bus_info": {}, "overview_info": {}, "images_info": []}

    # Limpiar información del autobús
    bus_info = bus_data.get("bus_info", {})
    for key, value in bus_info.items():
        # Normalizar cadenas
        if isinstance(value, str):
            value = value.strip()
            # Si el campo está vacío, establecerlo como None
            if value == "":
                value = None

        # Normalizar booleanos
        if key in ["published", "featured", "sold", "scraped", "draft", "luggage", "score"]:
            if isinstance(value, str):
                value = value.lower() in ("yes", "true", "t", "1", "on")
            elif isinstance(value, int):
                value = value == 1

        cleaned_data["bus_info"][key] = value

    # Limpiar información general
    overview_info = bus_data.get("overview_info", {})
    for key, value in overview_info.items():
        if isinstance(value, str):
            value = value.strip()
            if value == "":
                value = None
        cleaned_data["overview_info"][key] = value

    # Limpiar información de imágenes
    images_info = bus_data.get("images_info", [])
    for img in images_info:
        cleaned_img = {}
        for key, value in img.items():
            if isinstance(value, str):
                value = value.strip()
                if value == "":
                    value = None
            cleaned_img[key] = value
        cleaned_data["images_info"].append(cleaned_img)

    return cleaned_data