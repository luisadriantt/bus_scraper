import os
import sys
import logging
import argparse
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config import LOG_CONFIG
from src.scraper.bus_scraper import BusScraper
from src.database.db_manager import DatabaseManager
from src.database.validators import clean_bus_data
from src.scraper.utils import save_to_json

def setup_logging() -> None:
    """Configura el sistema de logging."""
    log_level = getattr(logging, LOG_CONFIG["level"])
    log_format = LOG_CONFIG["format"]
    log_file = LOG_CONFIG["file"]

    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

def scrape_and_store(use_selenium: bool = False,
                     urls: Optional[List[str]] = None,
                     url_file: Optional[str] = None,
                     ) -> Dict[str, Any]:
    """
    Realiza el proceso completo de scraping y almacenamiento.

    Args:
        use_selenium: Si es True, utiliza Selenium para el scraping.
        urls: Lista opcional de URLs específicas para scrapear.
        url_file: Archivo opcional con lista de URLs para scrapear (una por línea).
    Returns:
        Diccionario con datos extraídos e IDs insertados.
    """
    logger = logging.getLogger(__name__)
    logger.info("Iniciando proceso de scraping y almacenamiento")

    # Inicializar variables para resultados
    raw_data = []
    cleaned_data = []
    inserted_ids = []

    try:
        # Inicializar scraper
        logger.info("Inicializando scraper")
        scraper = BusScraper(use_selenium=use_selenium)

    except Exception as e:
        logger.error(f"Error inicializando el scraper: {str(e)}", exc_info=True)
        return {"data": [], "inserted_ids": []}

    # Extraer datos
    try:
        if url_file:
            logger.info(f"Extrayendo datos de URLs en el archivo: {url_file}")
            raw_data = scraper.scrape_from_file(url_file)
        elif urls:
            logger.info(f"Extrayendo datos de {len(urls)} URLs específicas")
            raw_data = scraper.scrape_all_listings(custom_urls=urls)
        else:
            assert "Se debe pasar al menos una URL"

        logger.info(f"Se extrajeron datos de {len(raw_data)} listados")
    except Exception as e:
        logger.error(f"Error durante el scraping: {str(e)}", exc_info=True)
        return {"data": [], "inserted_ids": []}

    # Si no hay datos extraídos, salir
    if not raw_data:
        logger.warning("No se encontraron datos. Finalizando proceso.")
        return {"data": [], "inserted_ids": []}

    # Limpiar y normalizar datos
    try:
        logger.info("Limpiando y normalizando datos")
        cleaned_data = [clean_bus_data(item) for sublist in raw_data for item in sublist]
    except Exception as e:
        logger.error(f"Error durante la limpieza de datos: {str(e)}", exc_info=True)
        return {"data": [], "inserted_ids": []}

    if cleaned_data:
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            json_filename = f"bus_listings_{timestamp}.json"
            logger.info(f"Guardando datos en {json_filename}")
            save_to_json(cleaned_data, json_filename)
        except Exception as e:
            logger.error(f"Error al guardar datos en JSON: {str(e)}", exc_info=True)
            return {"data": [], "inserted_ids": []}
        try:
            logger.info("Inicializando gestor de base de datos")
            db_manager = DatabaseManager()

            # Verificar/crear tablas
            logger.info("Verificando estructura de la base de datos")
            db_manager.create_database_if_not_exists()
            db_manager.create_tables()

            # Insertar datos
            logger.info("Insertando datos en la base de datos")
            inserted_ids = db_manager.insert_many_buses(cleaned_data)
            logger.info(f"Se insertaron {len(inserted_ids)} autobuses en la base de datos")

            # Crear dump de la base de datos
            if inserted_ids:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                dump_filename = f"database_dump_{timestamp}.sql"
                # db_manager.create_database_dump(dump_filename)
        except Exception as e:
            logger.error(f"Error en operaciones de base de datos: {str(e)}", exc_info=True)

    # Generar informe de resultados
    if cleaned_data:
        try:
            results_report = {
                "total_buses_found": len(cleaned_data),
                "total_buses_inserted": len(inserted_ids),
                "buses_by_make": {},
                "buses_by_year": {},
                "buses_by_region": {}
            }

            # Analizar datos para el informe
            for bus_data in cleaned_data:
                bus_info = bus_data.get("bus_info", {})
                make = bus_info.get("make", "Unknown")
                year = bus_info.get("year", "Unknown")
                region = bus_info.get("us_region", "Unknown")

                # Incrementar contadores
                results_report["buses_by_make"][make] = results_report["buses_by_make"].get(make, 0) + 1
                results_report["buses_by_year"][year] = results_report["buses_by_year"].get(year, 0) + 1
                results_report["buses_by_region"][region] = results_report["buses_by_region"].get(region, 0) + 1

            # Guardar informe
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_filename = f"scraping_report_{timestamp}.json"
            logger.info(f"Guardando informe de resultados en {report_filename}")
            save_to_json(results_report, report_filename)
        except Exception as e:
            logger.error(f"Error al generar informe: {str(e)}", exc_info=True)

    logger.info("Proceso completado exitosamente")

    # Devolver los datos limpios y los IDs insertados para referencia
    return {
        "data": cleaned_data,
        "inserted_ids": inserted_ids
    }

def main() -> None:
    """Función principal del programa."""
    parser = argparse.ArgumentParser(description="Scraper de listados de autobuses escolares")
    parser.add_argument("--selenium", action="store_true", help="Usar Selenium para el scraping")

    url_group = parser.add_mutually_exclusive_group()
    url_group.add_argument("--urls", nargs="+", help="Lista de URLs específicas para scrapear")
    url_group.add_argument("--url-file", type=str, help="Archivo con lista de URLs para scrapear (una por línea)")

    args = parser.parse_args()

    # Configurar logging
    setup_logging()

    # Ejecutar proceso
    result = scrape_and_store(use_selenium=args.selenium, urls=args.urls, url_file=args.url_file)

    # Mostrar resumen
    data_count = len(result["data"])
    inserted_count = len(result["inserted_ids"])
    print(f"\nResumen del proceso:")
    print(f"- Autobuses encontrados: {data_count}")
    print(f"- Autobuses insertados en la base de datos: {inserted_count}")
    if data_count > 0:
        print(f"Proceso completado exitosamente.")
    else:
        print(f"No se encontraron autobuses para procesar.")

if __name__ == "__main__":
    main()