import time
import logging
import requests
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from config.config import SCRAPING_CONFIG
from src.scraper.parser_factory import ParserFactory
from src.scraper.utils import setup_selenium_driver, retry_on_failure

logger = logging.getLogger(__name__)

class BusScraper:
    """
    Clase principal para extraer información de autobuses escolares.
    """

    def __init__(self, use_selenium: bool = False):
        """
        Inicializa el scraper.

        Args:
            use_selenium: Si es True, utiliza Selenium para scraping.
                          Si es False, utiliza requests.
        """
        self.base_url = None
        self.pagination_pattern = SCRAPING_CONFIG["pagination_pattern"]
        self.min_listings = SCRAPING_CONFIG["min_listings"]
        self.delay = SCRAPING_CONFIG["request_delay"]
        self.headers = {"User-Agent": SCRAPING_CONFIG["user_agent"]}
        self.timeout = SCRAPING_CONFIG["timeout"]
        self.use_selenium = use_selenium
        self.driver = None
        self.parser_factory = ParserFactory()

        if use_selenium:
            self.driver = setup_selenium_driver()

    def __del__(self):
        """Cierra el driver de Selenium si está en uso."""
        if self.driver:
            self.driver.quit()

    @retry_on_failure(max_retries=SCRAPING_CONFIG["max_retries"])
    def fetch_page(self, url: str) -> str:
        """
        Obtiene el HTML de una página.

        Args:
            url: URL de la página a extraer.

        Returns:
            El contenido HTML de la página.
        """
        if self.use_selenium:
            self.driver.get(url)
            time.sleep(self.delay)  # Espera para carga dinámica
            return self.driver.page_source
        else:
            response = requests.get(url, headers=self.headers, timeout=self.timeout, verify=False)
            response.raise_for_status()
            time.sleep(self.delay)  # Respeta los límites de tasa
            return response.text

    def get_listing_urls(self, max_pages: int = 10) -> List[str]:
        """
        Obtiene las URLs de todos los listados de autobuses.

        Args:
            max_pages: Número máximo de páginas a extraer.

        Returns:
            Lista de URLs de listados individuales.
        """
        all_listing_urls = []
        page = 1

        while page <= max_pages and len(all_listing_urls) < self.min_listings:
            try:
                if page == 1:
                    url = self.base_url
                else:
                    url = f"{self.base_url}?{self.pagination_pattern.format(page_num=page)}"

                logger.info(f"Extrayendo URLs de listados de la página {page}: {url}")
                html = self.fetch_page(url)
                soup = BeautifulSoup(html, 'lxml')

                # Extraer URLs de listados individuales (ajustar selector según el sitio real)
                listing_elements = soup.select('.bus-listing a.detail-link')  # Ajustar selector

                if not listing_elements:
                    logger.warning(f"No se encontraron listados en la página {page}")
                    break

                # Extraer y normalizar URLs
                page_urls = [urljoin(self.base_url, elem['href']) for elem in listing_elements]
                all_listing_urls.extend(page_urls)

                logger.info(f"Se encontraron {len(page_urls)} listados en la página {page}")
                page += 1

            except Exception as e:
                logger.error(f"Error al extraer URLs de la página {page}: {str(e)}")
                break

        return all_listing_urls[:max(self.min_listings, len(all_listing_urls))]

    def scrape_listing(self, url: str) -> Dict[str, Any]:
        """
        Extrae información detallada de un listado individual.

        Args:
            url: URL del listado a extraer.

        Returns:
            Diccionario con la información extraída.
        """
        try:
            logger.info(f"Extrayendo datos del listado: {url}")
            html = self.fetch_page(url)

            # Obtener el parser adecuado para esta URL
            parser = self.parser_factory.get_parser(url)

            # Parsear el HTML para extraer todos los datos requeridos
            bus_data = parser.parse_listing(html, url)

            return bus_data

        except Exception as e:
            logger.error(f"Error al extraer datos del listado {url}: {str(e)}")
            return {}

    def scrape_all_listings(self, custom_urls: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Extrae información de todos los listados de autobuses.

        Args:
            custom_urls: Lista opcional de URLs específicas para scrapear directamente.

        Returns:
            Lista de diccionarios con la información extraída.
        """
        # Si se proporcionan URLs personalizadas, usar esas en lugar de obtenerlas del sitio
        if custom_urls:
            listing_urls = custom_urls
            logger.info(f"Usando {len(listing_urls)} URLs personalizadas proporcionadas")
        else:
            listing_urls = self.get_listing_urls()

        logger.info(f"Comenzando a extraer {len(listing_urls)} listados")

        all_listings = []
        for url in listing_urls:
            listing_data = self.scrape_listing(url)
            if listing_data:
                all_listings.append(listing_data)
            # Log de progreso cada 5 listados
            if len(all_listings) % 5 == 0:
                logger.info(f"Progreso: {len(all_listings)}/{len(listing_urls)} listados procesados")

        logger.info(f"Extracción completada. Se obtuvieron datos de {len(all_listings)} listados")
        return all_listings

    def scrape_from_file(self, filename: str) -> List[Dict[str, Any]]:
        """
        Extrae información de listados a partir de un archivo con URLs.

        Args:
            filename: Nombre del archivo con las URLs (una por línea).

        Returns:
            Lista de diccionarios con la información extraída.
        """
        try:
            with open(filename, 'r') as f:
                urls = [line.strip() for line in f if line.strip()]

            logger.info(f"Leyendo {len(urls)} URLs desde el archivo {filename}")
            return self.scrape_all_listings(custom_urls=urls)

        except Exception as e:
            logger.error(f"Error al leer URLs desde el archivo {filename}: {str(e)}")
            return []