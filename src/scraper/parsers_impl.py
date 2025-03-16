import re
import logging
from time import sleep
from typing import Dict, Any, List, Tuple, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from selenium.common import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.ie.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from src.pdf_parser.extract_specs import get_micro_bird_specs
from src.scraper.parsers import BaseBusParser
from src.scraper.utils import wait_for_element_to_have_content, html_to_text

logger = logging.getLogger(__name__)


class DefaultBusParser(BaseBusParser):
    """
    Parser genérico para cuando no hay un parser específico disponible.
    Intenta extraer datos con selectores comunes.
    """

    def parse_listing(self, html: str, source_url: str) -> Dict[str, Any]:
        """
        Parsea el HTML de un listado de autobús y extrae la información requerida.

        Args:
            html: HTML del listado.
            source_url: URL de origen para referencias.

        Returns:
            Diccionario con la información estructurada del autobús.
        """
        soup = BeautifulSoup(html, 'lxml')

        # Contenedores para el resultado
        bus_info = {}
        overview_info = {}
        images_info = []

        try:
            # Extraer información básica del autobús
            bus_info = self._extract_basic_info(soup, source_url)

            # Extraer descripciones y características
            overview_info = self._extract_overview_info(soup)

            # Extraer imágenes
            images_info = self._extract_images(soup, base_url=source_url)

        except Exception as e:
            logger.error(f"Error al parsear listado {source_url}: {str(e)}")

        return {
            "bus_info": bus_info,
            "overview_info": overview_info,
            "images_info": images_info
        }

    def _extract_basic_info(self, soup: BeautifulSoup, source_url: str) -> Dict[str, Any]:
        """
        Intenta extraer la información básica del autobús con selectores genéricos.

        Args:
            soup: Objeto BeautifulSoup del HTML.
            source_url: URL de origen.

        Returns:
            Diccionario con la información básica.
        """
        result = {
            "source": "web_scraper",
            "source_url": source_url,
            "scraped": 1,
            "published": 1,
            "draft": 0
        }

        # Buscar título en elementos comunes
        title_selectors = ['h1', '.product-title', '.item-title', '.listing-title', 'h1.title']
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                result["title"] = title_elem.text.strip()
                break

        # Extraer año, marca y modelo
        year, make, model = self._extract_year_make_model(result.get("title", ""), soup)
        result["year"] = year
        result["make"] = make
        result["model"] = model

        # Buscar precio en elementos comunes
        price_selectors = ['.price', '.product-price', '.item-price', '.listing-price', '.amount']
        for selector in price_selectors:
            price_elem = soup.select_one(selector)
            if price_elem:
                price_text = price_elem.text.strip()
                result["price"] = price_text
                result["cprice"] = self._extract_numeric_price(price_text)
                break

        # Extraer detalles técnicos
        self._extract_technical_details(soup, result)

        # Buscar VIN en elementos comunes
        vin_selectors = ['.vin', '.product-vin', '.item-vin', '.listing-vin']
        for selector in vin_selectors:
            vin_elem = soup.select_one(selector)
            if vin_elem:
                result["vin"] = vin_elem.text.strip()
                break

        return result

    def _extract_year_make_model(self, title: str, soup: BeautifulSoup) -> Tuple[str, str, str]:
        """
        Intenta extraer año, marca y modelo del título o elementos específicos.

        Args:
            title: Título del listado.
            soup: Objeto BeautifulSoup del HTML.

        Returns:
            Tupla con (año, marca, modelo).
        """
        year, make, model = "", "", ""

        # Intentar extraer del título con regex
        if title:
            # Patrón común: "2015 Blue Bird Vision" o similar
            match = re.search(r'(\d{4})\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)\s+([A-Za-z0-9]+(?:\s+[A-Za-z0-9]+)*)', title)
            if match:
                year = match.group(1)
                make = match.group(2)
                model = match.group(3)

        # Buscar en elementos comunes si no se pudo extraer del título
        if not year:
            year_selectors = ['.year', '.product-year', '.item-year', '.listing-year']
            for selector in year_selectors:
                year_elem = soup.select_one(selector)
                if year_elem:
                    year = year_elem.text.strip()
                    break

        if not make:
            make_selectors = ['.make', '.brand', '.product-make', '.item-make', '.listing-make']
            for selector in make_selectors:
                make_elem = soup.select_one(selector)
                if make_elem:
                    make = make_elem.text.strip()
                    break

        if not model:
            model_selectors = ['.model', '.product-model', '.item-model', '.listing-model']
            for selector in model_selectors:
                model_elem = soup.select_one(selector)
                if model_elem:
                    model = model_elem.text.strip()
                    break

        return year, make, model

    def _extract_technical_details(self, soup: BeautifulSoup, result: Dict[str, Any]) -> None:
        """
        Intenta extraer detalles técnicos con selectores genéricos.

        Args:
            soup: Objeto BeautifulSoup del HTML.
            result: Diccionario de resultados a modificar.
        """
        # Mapa de campos a buscar con sus selectores posibles
        field_selectors = {
            "mileage": ['.mileage', '.miles', '.odometer', '.product-mileage', '.item-mileage'],
            "passengers": ['.passengers', '.capacity', '.product-passengers', '.item-passengers'],
            "wheelchair": ['.wheelchair', '.accessible', '.product-wheelchair', '.item-wheelchair'],
            "engine": ['.engine', '.engine-type', '.product-engine', '.item-engine'],
            "transmission": ['.transmission', '.trans', '.product-transmission', '.item-transmission'],
            "gvwr": ['.gvwr', '.gross-weight', '.product-gvwr', '.item-gvwr'],
            "color": ['.color', '.product-color', '.item-color'],
            "exterior_color": ['.exterior-color', '.ext-color', '.product-exterior-color'],
            "interior_color": ['.interior-color', '.int-color', '.product-interior-color']
        }

        # Intentar encontrar cada campo en la página
        for field, selectors in field_selectors.items():
            for selector in selectors:
                elem = soup.select_one(selector)
                if elem:
                    result[field] = elem.text.strip()
                    break

        # Buscar en tablas de especificaciones
        spec_tables = soup.select('table.specs, table.specifications, .specs-table')
        for table in spec_tables:
            rows = table.select('tr')
            for row in rows:
                cells = row.select('td, th')
                if len(cells) >= 2:
                    key = cells[0].text.strip().lower()
                    value = cells[1].text.strip()

                    if 'mileage' in key or 'miles' in key:
                        result['mileage'] = value
                    elif 'passenger' in key or 'capacity' in key:
                        result['passengers'] = value
                    elif 'wheelchair' in key or 'accessible' in key:
                        result['wheelchair'] = value
                    elif 'engine' in key:
                        result['engine'] = value
                    elif 'transmission' in key or 'trans' in key:
                        result['transmission'] = value
                    elif 'gvwr' in key or 'gross' in key:
                        result['gvwr'] = value
                    elif 'color' in key and 'interior' not in key and 'exterior' not in key:
                        result['color'] = value
                    elif 'exterior color' in key or 'ext color' in key:
                        result['exterior_color'] = value
                    elif 'interior color' in key or 'int color' in key:
                        result['interior_color'] = value

    def _extract_overview_info(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Intenta extraer información descriptiva con selectores genéricos.

        Args:
            soup: Objeto BeautifulSoup del HTML.

        Returns:
            Diccionario con la información detallada.
        """
        result = {}

        # Buscar descripción general
        description_selectors = ['.description', '.product-description', '.item-description', '.listing-description']
        for selector in description_selectors:
            desc_elem = soup.select_one(selector)
            if desc_elem:
                result["mdesc"] = desc_elem.text.strip()
                break

        # Buscar descripción interior
        interior_selectors = ['.interior-description', '.int-desc', '.product-interior', '.item-interior']
        for selector in interior_selectors:
            interior_elem = soup.select_one(selector)
            if interior_elem:
                result["intdesc"] = interior_elem.text.strip()
                break

        # Buscar descripción exterior
        exterior_selectors = ['.exterior-description', '.ext-desc', '.product-exterior', '.item-exterior']
        for selector in exterior_selectors:
            exterior_elem = soup.select_one(selector)
            if exterior_elem:
                result["extdesc"] = exterior_elem.text.strip()
                break

        # Buscar características
        features_selectors = ['.features', '.product-features', '.item-features', '.listing-features']
        for selector in features_selectors:
            features_elem = soup.select_one(selector)
            if features_elem:
                result["features"] = features_elem.text.strip()
                break

        # Buscar especificaciones
        specs_selectors = ['.specs', '.specifications', '.product-specs', '.item-specs']
        for selector in specs_selectors:
            specs_elem = soup.select_one(selector)
            if specs_elem:
                result["specs"] = specs_elem.text.strip()
                break

        return result

    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, Any]]:
        """
        Intenta extraer imágenes con selectores genéricos.

        Args:
            soup: Objeto BeautifulSoup del HTML.
            base_url: URL base para construir URLs completas.

        Returns:
            Lista de diccionarios con información de imágenes.
        """
        images = []

        # Selectores comunes para galerías de imágenes
        image_selectors = [
            '.gallery img',
            '.product-gallery img',
            '.item-gallery img',
            '.listing-gallery img',
            '.carousel img',
            '.slider img',
            '.product-images img',
            '.photos img',
            'a[rel="gallery"] img',
            '[data-gallery] img'
        ]

        # Probar cada selector
        found_images = False
        for selector in image_selectors:
            image_elements = soup.select(selector)
            if image_elements:
                found_images = True
                for idx, img in enumerate(image_elements):
                    image_info = {
                        "image_index": idx,
                        "url": urljoin(base_url, img.get('src', '')),
                        "name": f"bus_image_{idx}",
                    }

                    # Extraer descripción/alt text si está disponible
                    if img.get('alt'):
                        image_info["description"] = img.get('alt')

                    images.append(image_info)
                break

        # Si no se encuentran imágenes con los selectores, buscar todas las imágenes grandes
        if not found_images:
            all_images = soup.find_all('img')
            large_images = [img for img in all_images if img.get('width') and int(img.get('width')) >= 300]
            for idx, img in enumerate(large_images):
                image_info = {
                    "image_index": idx,
                    "url": urljoin(base_url, img.get('src', '')),
                    "name": f"bus_image_{idx}",
                }

                if img.get('alt'):
                    image_info["description"] = img.get('alt')

                images.append(image_info)

        return images


class RossBusParser(BaseBusParser):
    """
    Parser específico para el sitio RossBusParser.com
    """

    def extract_bus_urls(self, html: str, base_url: str) -> List[str]:
        """
        Extrae las URLs individuales de autobuses de RossBusParser.com

        Args:
            html: HTML de la página de listado.
            base_url: URL base para construir URLs completas.

        Returns:
            Lista de URLs de autobuses individuales.
        """
        soup = BeautifulSoup(html, 'lxml')
        urls = []
        from src.scraper.bus_scraper import BusScraper
        bus_scraper = BusScraper()

        # RossBusParser.com usa estos selectores para sus listados
        buses_container = soup.find('section', class_='IdxBusesWrap')
        links = buses_container.select('.FillYellowBtn a')
        for link in links:
            href = link.get('href')
            if href:
                full_url = urljoin(base_url, href)
                html = bus_scraper.fetch_page(full_url)
                soup = BeautifulSoup(html, 'lxml')
                buses_container = soup.find('div', class_='BusListWrapper TwoBtnWrap')
                links = buses_container.select('.FillYellowBtn a')
                for link in links:
                    href = link.get('href')
                    if href:
                        full_url = urljoin(base_url, href)
                        urls.append(full_url)

        return urls

    def parse_listing(self, html: str, source_url: str) -> List[Dict[str, Any]]:
        """Parsea el HTML específico del sitio RossBusParser."""

        bus_data_list = []
        from src.scraper.bus_scraper import BusScraper
        bus_scraper = BusScraper()

        try:
            # Extract URLs
            urls_to_scrap = self.extract_bus_urls(html, source_url)
            for source_url in urls_to_scrap:
                html = bus_scraper.fetch_page(source_url)
                soup = BeautifulSoup(html, 'lxml')

                # Extraer información básica
                bus_info = self._extract_basic_info(soup, source_url)

                # Extraer descripciones
                overview_info = self._extract_overview_info(soup)

                # Extraer imágenes
                images_info = self._extract_images(soup, base_url=source_url)

                bus_data = {
                    "bus_info": bus_info,
                    "overview_info": overview_info,
                    "images_info": images_info
                }

                bus_data_list.append(bus_data)

        except Exception as e:
            logger.error(f"Error al parsear listado RossBusParser {source_url}: {str(e)}")

        return bus_data_list

    def _extract_year_make_model(self, title: str, soup: BeautifulSoup) -> Tuple[str, str, str]:
        pass

    def _extract_basic_info(self, soup: BeautifulSoup, source_url: str) -> Dict[str, Any]:
        """Extrae información básica específica del sitio RossBusParser."""
        result = {
            "source": "RossBusParser.com",
            "source_url": source_url,
            "scraped": 1,
            "published": 1,
            "draft": 0
        }

        if title_elem := soup.select_one('h5.BlueTitle'):
            result["title"] = title_elem.text.strip()
        if description_elem := soup.select_one('.Describe.FParagraph1.EditorText'):
            result["description"] = description_elem.text.strip()
        if wheelchair := soup.select_one('.Extra_Info_Wrap'):
            result["wheelchair"] = 'Yes' if 'Lift Equipped :Yes' in wheelchair.text.strip() else 'No'

        # Extraer detalles técnicos
        self._extract_technical_details(soup, result)

        # VIN específico para BusesForSale
        vin_elem = soup.select_one('.bus-vin')
        if vin_elem:
            result["vin"] = vin_elem.text.strip()

        return result

    def _extract_technical_details(self, soup: BeautifulSoup, result: Dict[str, Any]) -> None:
        """Extrae detalles técnicos específicos del sitio BusesForSale."""
        specs = soup.select_one('.DeepDetails')
        if not specs:
            return
        specs = soup.select_one('.DeepDetails').find_all('ul', class_='NoBullet')
        specs_list = [spec for spec in specs[0]]
        field_selectors = [
            "capacity",
            "engine",
            "transmission",
            "gvwr",
        ]

        for spec in specs_list:
            if isinstance(spec, str):
                continue
            spec_name = spec.select_one('.First').text.strip().lower()
            if spec_name in field_selectors:
                spec_name = 'passengers' if spec_name == 'capacity' else spec_name
                result[spec_name] = spec.select_one('.Last').text.strip().lower()[:56]

    def _extract_overview_info(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extrae información descriptiva específica del sitio BusesForSale."""
        result = {}

        # Descripción general
        description_elem = soup.select_one('.bus-description, .listing-description')
        if description_elem:
            result["mdesc"] = description_elem.text.strip()

        # Descripción interior
        interior_desc_elem = soup.select_one('.bus-interior-description, .listing-interior')
        if interior_desc_elem:
            result["intdesc"] = interior_desc_elem.text.strip()

        # Descripción exterior
        exterior_desc_elem = soup.select_one('.bus-exterior-description, .listing-exterior')
        if exterior_desc_elem:
            result["extdesc"] = exterior_desc_elem.text.strip()

        # Características
        features_elem = soup.select_one('.bus-features, .listing-features')
        if features_elem:
            result["features"] = features_elem.text.strip()

        # Especificaciones
        specs_elem = soup.select_one('.bus-specs, .listing-specs')
        if specs_elem:
            result["specs"] = specs_elem.text.strip()

        return result

    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, Any]]:
        """Extrae imágenes específicas del sitio BusesForSale."""
        images = []

        # Galería de imágenes específica de BusesForSale
        image_elements = soup.find('ul', class_='slides')
        if not image_elements:
            return images

        for idx, img in enumerate(image_elements):
            if isinstance(img, str):
                continue
            image = img.select_one('img')
            if not image:
                continue
            image_info = {
                "image_index": idx,
                "url": urljoin(base_url, image.get('src')),
                "name": f"bus_image_{idx}",
            }

            # Extraer descripción/alt text si está disponible
            if img.get('alt'):
                image_info["description"] = img.get('alt')

            images.append(image_info)

        return images


class DaimlerParser(BaseBusParser):
    """
    Parser específico para el sitio DaimlerParser.com
    """

    def extract_bus_urls(self, driver: WebDriver, base_url: str) -> List[WebElement]:
        """
        Extrae las URLs individuales de autobuses de DaimlerParser.com

        Args:
            driver: selenium driver.
            base_url: URL base para construir URLs completas.

        Returns:
            Lista de URLs de autobuses individuales.
        """
        if buses := driver.find_elements(By.CSS_SELECTOR, ".coaches-models-wrapper"):
            buses = buses[1].find_elements(By.CSS_SELECTOR, ".coaches-models-box")
        return buses

    def parse_listing(self, driver: str|WebDriver, source_url:str) -> List[Dict[str, Any]]:
        bus_data_list = []

        try:
            buses_to_scrap = self.extract_bus_urls(driver, source_url)
            for bus in buses_to_scrap:
                # Extraer información básica
                bus_info = self._extract_basic_info(bus, source_url, driver)

                # Extraer imágenes
                images_info = self._extract_images(bus, base_url=source_url, driver=driver)

                bus_data = {
                    "bus_info": bus_info,
                    "overview_info": {},
                    "images_info": images_info
                }

                bus_data_list.append(bus_data)

        except Exception as e:
            logger.error(f"Error al parsear listado DaimlerParser {source_url}: {str(e)}")

        return bus_data_list

    def _extract_basic_info(self, bus: WebElement, source_url: str, driver: WebDriver) -> Dict[str, Any]:
        """Extrae información básica específica del sitio DaimlerParser."""
        result = {
            "source": "daimlercoachesnorthamerica.com",
            "source_url": source_url,
            "scraped": 1,
            "published": 1,
            "draft": 0
        }
        max_attempts = 5
        attempt = 0

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.coaches-models-content h4"))
        )

        try:
            content_div = wait_for_element_to_have_content(
                bus,
                "div.coaches-models-content h4",
                timeout=15
            )

            title_elem = content_div.get_attribute("innerHTML").strip() or content_div.text.strip()
            title_elem = html_to_text(title_elem)
            title_elem = title_elem.split('–')
            result["title"] = title_elem[0].strip()
            # result["gvwr"] = title_elem[1]
            result["passengers"] = title_elem[2].strip()
            result["price"] = title_elem[-1].split('|')[-1].strip()
            result["cprice"] = self._extract_numeric_price(title_elem[-1].split('|')[-1].strip())
            result["year"] = title_elem[0].split(' ')[0].strip()
            result["make"] = title_elem[0].split(' ')[1].strip()
            result["model"] = " ".join(title_elem[0].split(' ')[1:]).strip()


        except TimeoutException as e:
            logger.error(f"Error al conectar para h4 {source_url}: {str(e)}")
            return {}
        except Exception as e:
            logger.error(f"Error al conectar para h4 {source_url}: {str(e)}")
            return {}

        try:
            content_div = wait_for_element_to_have_content(
                bus,
                "div.coaches-models-content div",
                timeout=15
            )
            bus_info = content_div.get_attribute("innerHTML").strip() or content_div.text.strip()
            bus_info = html_to_text(bus_info)
            bus_info = bus_info.split(' ')
            result["vin"] = bus_info[1]
            result["engine"] = bus_info[3]
            result["mileage"] = bus_info[5]


        except TimeoutException as e:
            logger.error(f"Error al conectar para div {source_url}: {str(e)}")
            return {}
        except Exception as e:
            logger.error(f"Error al conectar para div {source_url}: {str(e)}")
            return {}

        return result

    def _extract_year_make_model(self, title: str, soup: BeautifulSoup) -> Tuple[str, str, str]:
        pass

    def _extract_technical_details(self, soup: BeautifulSoup, result: Dict[str, Any]) -> None:
        pass

    def _extract_overview_info(self, soup: BeautifulSoup) -> Dict[str, Any]:
        pass

    def _extract_images(self, element: WebElement, base_url: str, driver: WebDriver) -> List[Dict[str, Any]]:
        """Extrae imágenes específicas del sitio DaimlerParser."""

        images = []

        try:
            gallery_link = element.find_element(By.CSS_SELECTOR, "a.fancybox-gallery")
            driver.execute_script("arguments[0].click();", gallery_link)

            # Esperar a que se abra la galería
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".fancybox-thumbs__list"))
            )

            # Obtener las miniaturas
            thumbs_container = driver.find_element(By.CLASS_NAME, "fancybox-thumbs__list")
            thumb_links = thumbs_container.find_elements(By.TAG_NAME, "a")

            pattern = r"background-image: url\((.*?)\)"

            for idx, link in enumerate(thumb_links):
                style_attr = link.get_attribute("style")

                match = re.search(pattern, style_attr)
                if match:
                    url = match.group(1)
                    url = url.strip("'\"")
                    image_info = {
                        "image_index": idx,
                        "url": urljoin(base_url, url),
                        "name": f"bus_image_{idx}",
                    }
                    images.append(image_info)

        except Exception as e:
            print(f"Error extracting images: {str(e)}")

        # finally:
        #     # Cerrar fancybox
        #     try:
        #         close_button = driver.find_element(By.CSS_SELECTOR, ".fancybox-button fancybox-button--close")
        #         close_button.click()
        #     except Exception as e:
        #         print(f"Error cerrando fb: {str(e)}")

        return images


class MicrobirdParser(BaseBusParser):
    """
    Parser específico para el sitio MicrobirdParser.com
    """

    def extract_bus_urls(self, html: str, base_url: str) -> List[str]:
        """
        Extrae las URLs individuales de autobuses de MicrobirdParser.com

        Args:
            html: HTML de la página de listado.
            base_url: URL base para construir URLs completas.

        Returns:
            Lista de URLs de autobuses individuales.
        """
        soup = BeautifulSoup(html, 'lxml')
        urls = []

        links = soup.select('.comp-kyd72ft7-container .comp-kyd72fuw1')
        for link in links:
            href = link.find(attrs={"data-testid": "linkElement"}).get('href')
            if href:
                full_url = urljoin(base_url, href)
                urls.append(full_url)

        return urls

    def parse_listing(self, html: str, source_url: str) -> List[Dict[str, Any]]:
        """Parsea el HTML específico del sitio MicrobirdParser."""
        soup = BeautifulSoup(html, 'lxml')

        bus_data_list = []
        from src.scraper.bus_scraper import BusScraper
        bus_scraper = BusScraper()
        overview_info = {}

        try:
            urls_to_scrap = self.extract_bus_urls(html, source_url)
            for source_url in urls_to_scrap:
                html = bus_scraper.fetch_page(source_url)
                soup = BeautifulSoup(html, 'lxml')
                # Extraer información básica
                bus_info = self._extract_basic_info(soup, source_url)

                if pdf_link := soup.find('a', class_="VU4Mnk wixui-button PlZyDq"):
                    pdf_link = pdf_link.get('href')
                    # Extraer detalles desde pdf
                    bus_details = get_micro_bird_specs(pdf_link)
                    # Extraer detalles técnicos
                    self._extract_technical_details(bus_details, bus_info)
                    # Extraer descripciones
                    overview_info = self._extract_overview_info(bus_details)

                # Extraer imágenes
                images_info = self._extract_images(soup, base_url=source_url)

                bus_data = {
                    "bus_info": bus_info,
                    "overview_info": overview_info,
                    "images_info": images_info
                }

                bus_data_list.append(bus_data)

        except Exception as e:
            logger.error(f"Error al parsear listado MicrobirdParser {source_url}: {str(e)}")

        return bus_data_list

    def _extract_basic_info(self, soup: BeautifulSoup, source_url: str) -> Dict[str, Any]:
        """Extrae información básica específica del sitio MicrobirdParser."""
        result = {
            "source": "microbird.com",
            "source_url": source_url,
            "scraped": 1,
            "published": 1,
            "draft": 0
        }

        if title_elem := soup.select_one('.comp-kx0qksd52, .comp-kx0r6sgl3, .comp-kwgt0yu2'):
            result["title"] = title_elem.text.strip()
        if description := soup.select_one(".comp-kx0qksa2, .comp-kwgruj2u, .comp-kx0r6sdf"):
            desc = '\n'.join([desc.text.strip() for desc in description.find_all("p")])
            result["description"] = desc
        if wheelchair := soup.find('h3', {'id': 'title_3', 'class': 'question-title'}):
            result["wheelchair"] = 'Yes' if 'Special' in wheelchair.text else 'No'

        return result

    def _extract_year_make_model(self, title: str, soup: BeautifulSoup) -> Tuple[str, str, str]:
        pass

    def _extract_technical_details(self, bus_details: dict, result: Dict[str, Any]) -> None:
        """Extrae detalles técnicos específicos del sitio MicrobirdParser desde archivo PDF."""
        field_selectors = [
            "capacity",
            "engine",
            "transmission",
            "gvwr",
            "brake",
            "passengers",
            "transmission",
            "chassis",
            "brake"
        ]

        if not bus_details:
            return

        for key, value in bus_details.items():
            if key.lower() in field_selectors:
                result[key.lower()] = value[:50]


    def _extract_overview_info(self, bus_details: dict) -> Dict[str, Any]:
        """Extrae información descriptiva específica del sitio MicrobirdParser."""
        interior_desc = 'Interior: '
        exterior_desc = 'Exterior: '
        features = 'Features: '
        options = 'Options: '

        # bus_details = get_micro_bird_specs(pdf_url)
        if not bus_details:
            return {}

        for key, value in bus_details.items():
            if 'exterior' in key.lower():
                exterior_desc += value
            elif 'interior' in key.lower():
                interior_desc += value
            elif 'options' in key.lower():
                options += value
            else:
                features += value
        result = {
            "intdesc": interior_desc,
            "extdesc": exterior_desc,
            "features": features,
            "mdesc": options,
        }

        return result

    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, Any]]:
        images = []
        if wow_image := soup.find('wow-image', {'id': 'img-comp-kx0qksbs'}):
            img = wow_image.find('img')
            if img and 'src' in img.attrs:
                img_url = img['src']
                image_info = {
                    "image_index": 0,
                    "url": urljoin(base_url, img_url),
                    "name": f"bus_image_{0}",
                }
                images.append(image_info)
        return images
