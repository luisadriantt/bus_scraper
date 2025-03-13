"""
Implementaciones concretas de parsers para diferentes sitios web de autobuses escolares.
"""
import re
import logging
from typing import Dict, Any, List, Tuple, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from soupsieve.util import lower

from src.scraper.parsers import BaseBusParser

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

        # Título específico para BusesForSale

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

    def extract_bus_urls(self, html: str, base_url: str) -> List[str]:
        """
        Extrae las URLs individuales de autobuses de DaimlerParser.com

        Args:
            html: HTML de la página de listado.
            base_url: URL base para construir URLs completas.

        Returns:
            Lista de URLs de autobuses individuales.
        """
        soup = BeautifulSoup(html, 'lxml')
        urls = []

        # DaimlerParser.com usa estos selectores para sus listados
        links = soup.select('.vehicle-listing a.vehicle-link, .inventory-grid .vehicle-item a')
        for link in links:
            href = link.get('href')
            if href:
                full_url = urljoin(base_url, href)
                urls.append(full_url)

        return urls

    def parse_listing(self, html: str, source_url: str) -> Dict[str, Any]:
        """Parsea el HTML específico del sitio DaimlerParser."""
        soup = BeautifulSoup(html, 'lxml')

        bus_info = {}
        overview_info = {}
        images_info = []

        try:
            # Extraer información básica
            bus_info = self._extract_basic_info(soup, source_url)

            # Extraer descripciones
            overview_info = self._extract_overview_info(soup)

            # Extraer imágenes
            images_info = self._extract_images(soup, base_url=source_url)

        except Exception as e:
            logger.error(f"Error al parsear listado DaimlerParser {source_url}: {str(e)}")

        return {
            "bus_info": bus_info,
            "overview_info": overview_info,
            "images_info": images_info
        }

    def _extract_basic_info(self, soup: BeautifulSoup, source_url: str) -> Dict[str, Any]:
        """Extrae información básica específica del sitio DaimlerParser."""
        result = {
            "source": "daimlercoachesnorthamerica.com",
            "source_url": source_url,
            "scraped": 1,
            "published": 1,
            "draft": 0
        }

        # Título específico para DaimlerParser
        title_elem = soup.select_one('.vehicle-title, h1.title')
        if title_elem:
            result["title"] = title_elem.text.strip()

        # Extraer año, marca y modelo
        year, make, model = self._extract_year_make_model(result.get("title", ""), soup)
        result["year"] = year
        result["make"] = make
        result["model"] = model

        # Precio específico para DaimlerParser
        price_elem = soup.select_one('.vehicle-price, .price')
        if price_elem:
            price_text = price_elem.text.strip()
            result["price"] = price_text
            result["cprice"] = self._extract_numeric_price(price_text)

        # Extraer detalles técnicos
        self._extract_technical_details(soup, result)

        # VIN específico para DaimlerParser
        vin_elem = soup.select_one('.vehicle-vin, .vin')
        if vin_elem:
            result["vin"] = vin_elem.text.strip()

        return result

    def _extract_year_make_model(self, title: str, soup: BeautifulSoup) -> Tuple[str, str, str]:
        """Extrae año, marca y modelo específicos del sitio DaimlerParser."""
        year, make, model = "", "", ""

        # DaimlerParser normalmente usa una estructura de "details" con etiquetas
        detail_labels = soup.select('.vehicle-details .detail-label, .specs-table th')
        detail_values = soup.select('.vehicle-details .detail-value, .specs-table td')

        for i in range(min(len(detail_labels), len(detail_values))):
            label = detail_labels[i].text.strip().lower()
            value = detail_values[i].text.strip()

            if 'year' in label:
                year = value
            elif 'make' in label:
                make = value
            elif 'model' in label:
                model = value

        # Si no se encuentra en elementos específicos, intentar extraer del título
        if not year or not make or not model:
            if title:
                match = re.search(r'(\d{4})\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)\s+([A-Za-z0-9]+(?:\s+[A-Za-z0-9]+)*)', title)
                if match:
                    if not year:
                        year = match.group(1)
                    if not make:
                        make = match.group(2)
                    if not model:
                        model = match.group(3)

        return year, make, model

    def _extract_technical_details(self, soup: BeautifulSoup, result: Dict[str, Any]) -> None:
        """Extrae detalles técnicos específicos del sitio DaimlerParser."""
        # DaimlerParser normalmente usa una estructura de "details" con etiquetas
        detail_labels = soup.select('.vehicle-details .detail-label, .specs-table th')
        detail_values = soup.select('.vehicle-details .detail-value, .specs-table td')

        for i in range(min(len(detail_labels), len(detail_values))):
            label = detail_labels[i].text.strip().lower()
            value = detail_values[i].text.strip()

            if 'mileage' in label or 'odometer' in label:
                result['mileage'] = value
            elif 'passenger' in label or 'capacity' in label:
                result['passengers'] = value
            elif 'wheelchair' in label or 'accessible' in label:
                result['wheelchair'] = value
            elif 'engine' in label:
                result['engine'] = value
            elif 'transmission' in label:
                result['transmission'] = value
            elif 'gvwr' in label or 'gross weight' in label:
                result['gvwr'] = value
            elif 'color' in label and 'interior' not in label and 'exterior' not in label:
                result['color'] = value
            elif 'exterior color' in label:
                result['exterior_color'] = value
            elif 'interior color' in label:
                result['interior_color'] = value

    def _extract_overview_info(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extrae información descriptiva específica del sitio DaimlerParser."""
        result = {}

        # Descripción general
        description_elem = soup.select_one('.vehicle-description, .description')
        if description_elem:
            result["mdesc"] = description_elem.text.strip()

        # DaimlerParser a veces tiene secciones específicas
        sections = soup.select('.description-section')
        for section in sections:
            heading = section.select_one('h3, h4')
            content = section.select_one('.section-content')

            if heading and content:
                heading_text = heading.text.strip().lower()
                content_text = content.text.strip()

                if 'interior' in heading_text:
                    result["intdesc"] = content_text
                elif 'exterior' in heading_text:
                    result["extdesc"] = content_text
                elif 'feature' in heading_text:
                    result["features"] = content_text
                elif 'spec' in heading_text:
                    result["specs"] = content_text

        return result

    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, Any]]:
        """Extrae imágenes específicas del sitio DaimlerParser."""
        images = []

        # Galería de imágenes específica de DaimlerParser
        image_elements = soup.select('.vehicle-gallery img, .gallery img, .carousel img')

        for idx, img in enumerate(image_elements):
            # DaimlerParser a veces usa data-src para carga diferida
            src = img.get('data-src') or img.get('src', '')

            image_info = {
                "image_index": idx,
                "url": urljoin(base_url, src),
                "name": f"bus_image_{idx}",
            }

            # Extraer descripción/alt text si está disponible
            if img.get('alt'):
                image_info["description"] = img.get('alt')

            images.append(image_info)

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

        # MicrobirdParser.com usa estos selectores para sus listados
        links = soup.select('.inventory-list .bus-item a.detail-link, .bus-grid .bus-card a.view-details')
        for link in links:
            href = link.get('href')
            if href:
                full_url = urljoin(base_url, href)
                urls.append(full_url)

        return urls

    def parse_listing(self, html: str, source_url: str) -> Dict[str, Any]:
        """Parsea el HTML específico del sitio MicrobirdParser."""
        soup = BeautifulSoup(html, 'lxml')

        bus_info = {}
        overview_info = {}
        images_info = []

        try:
            # Extraer información básica
            bus_info = self._extract_basic_info(soup, source_url)

            # Extraer descripciones
            overview_info = self._extract_overview_info(soup)

            # Extraer imágenes
            images_info = self._extract_images(soup, base_url=source_url)

        except Exception as e:
            logger.error(f"Error al parsear listado MicrobirdParser {source_url}: {str(e)}")

        return {
            "bus_info": bus_info,
            "overview_info": overview_info,
            "images_info": images_info
        }

    def _extract_basic_info(self, soup: BeautifulSoup, source_url: str) -> Dict[str, Any]:
        """Extrae información básica específica del sitio MicrobirdParser."""
        result = {
            "source": "microbird.com",
            "source_url": source_url,
            "scraped": 1,
            "published": 1,
            "draft": 0
        }

        # Título específico para MicrobirdParser
        title_elem = soup.select_one('.inventory-title, .product-title')
        if title_elem:
            result["title"] = title_elem.text.strip()

        # Extraer año, marca y modelo
        year, make, model = self._extract_year_make_model(result.get("title", ""), soup)
        result["year"] = year
        result["make"] = make
        result["model"] = model

        # Precio específico para MicrobirdParser
        price_elem = soup.select_one('.inventory-price, .price')
        if price_elem:
            price_text = price_elem.text.strip()
            result["price"] = price_text
            result["cprice"] = self._extract_numeric_price(price_text)

        # Extraer detalles técnicos
        self._extract_technical_details(soup, result)

        # VIN específico para MicrobirdParser
        vin_elem = soup.select_one('.inventory-vin, .vin')
        if vin_elem:
            result["vin"] = vin_elem.text.strip()

        return result

    def _extract_year_make_model(self, title: str, soup: BeautifulSoup) -> Tuple[str, str, str]:
        """Extrae año, marca y modelo específicos del sitio MicrobirdParser."""
        year, make, model = "", "", ""

        # MicrobirdParser normalmente muestra estos datos en una lista de detalles
        detail_list = soup.select('.inventory-details li, .details li')
        for item in detail_list:
            text = item.text.strip().lower()
            if 'year:' in text:
                year = text.split('year:')[1].strip()
            elif 'make:' in text:
                make = text.split('make:')[1].strip()
            elif 'model:' in text:
                model = text.split('model:')[1].strip()

        # Si no se encuentra en elementos específicos, intentar extraer del título
        if not year or not make or not model:
            if title:
                match = re.search(r'(\d{4})\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)\s+([A-Za-z0-9]+(?:\s+[A-Za-z0-9]+)*)', title)
                if match:
                    if not year:
                        year = match.group(1)
                    if not make:
                        make = match.group(2)
                    if not model:
                        model = match.group(3)

        return year, make, model

    def _extract_technical_details(self, soup: BeautifulSoup, result: Dict[str, Any]) -> None:
        """Extrae detalles técnicos específicos del sitio MicrobirdParser."""
        # MicrobirdParser normalmente muestra estos datos en una lista de detalles
        detail_list = soup.select('.inventory-details li, .details li, .specs li')

        for item in detail_list:
            text = item.text.strip().lower()

            if 'mileage:' in text or 'miles:' in text:
                if 'mileage:' in text:
                    result['mileage'] = text.split('mileage:')[1].strip()
                else:
                    result['mileage'] = text.split('miles:')[1].strip()
            elif 'passenger:' in text or 'capacity:' in text:
                if 'passenger:' in text:
                    result['passengers'] = text.split('passenger:')[1].strip()
                else:
                    result['passengers'] = text.split('capacity:')[1].strip()
            elif 'wheelchair:' in text:
                result['wheelchair'] = text.split('wheelchair:')[1].strip()
            elif 'engine:' in text:
                result['engine'] = text.split('engine:')[1].strip()
            elif 'transmission:' in text:
                result['transmission'] = text.split('transmission:')[1].strip()
            elif 'gvwr:' in text:
                result['gvwr'] = text.split('gvwr:')[1].strip()
            elif 'color:' in text and 'interior color:' not in text and 'exterior color:' not in text:
                result['color'] = text.split('color:')[1].strip()
            elif 'exterior color:' in text:
                result['exterior_color'] = text.split('exterior color:')[1].strip()
            elif 'interior color:' in text:
                result['interior_color'] = text.split('interior color:')[1].strip()

    def _extract_overview_info(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extrae información descriptiva específica del sitio MicrobirdParser."""
        result = {}

        # Descripción general
        description_elem = soup.select_one('.inventory-description, .description')
        if description_elem:
            result["mdesc"] = description_elem.text.strip()

        # MicrobirdParser a veces segmenta la descripción en secciones
        sections = soup.select('.description-section, .info-section')
        for section in sections:
            heading = section.select_one('h3, h4')
            content = section.select_one('.section-content, .content')

            if heading and content:
                heading_text = heading.text.strip().lower()
                content_text = content.text.strip()

                if 'interior' in heading_text:
                    result["intdesc"] = content_text
                elif 'exterior' in heading_text:
                    result["extdesc"] = content_text
                elif 'feature' in heading_text:
                    result["features"] = content_text
                elif 'spec' in heading_text:
                    result["specs"] = content_text

        return result

    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, Any]]:
        """Extrae imágenes específicas del sitio MicrobirdParser."""
        images = []

        # Galería de imágenes específica de MicrobirdParser
        image_elements = soup.select('.inventory-gallery img, .gallery img, .slider img')

        for idx, img in enumerate(image_elements):
            # MicrobirdParser a veces usa data-src para carga diferida
            src = img.get('data-src') or img.get('src', '')

            image_info = {
                "image_index": idx,
                "url": urljoin(base_url, src),
                "name": f"bus_image_{idx}",
            }

            # Extraer descripción/alt text si está disponible
            if img.get('alt'):
                image_info["description"] = img.get('alt')

            images.append(image_info)

        return images