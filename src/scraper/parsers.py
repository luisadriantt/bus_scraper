"""
Definición de interfaces de parsing para el scraper de autobuses.
"""
import abc
import logging
from typing import Dict, Any, List, Tuple, Optional
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class BaseBusParser(abc.ABC):
    """
    Clase base abstracta para parsers de listados de autobuses.
    """

    @abc.abstractmethod
    def parse_listing(self, html: str, source_url: str) -> Dict[str, Any]:
        """
        Parsea el HTML de un listado de autobús y extrae la información requerida.

        Args:
            html: HTML del listado.
            source_url: URL de origen para referencias.

        Returns:
            Diccionario con la información estructurada del autobús.
        """
        pass

    @abc.abstractmethod
    def extract_bus_urls(self, html: str, base_url: str) -> List[str]:
        """
        Extrae las URLs individuales de autobuses de una página de listado.

        Args:
            html: HTML de la página de listado.
            base_url: URL base para construir URLs completas.

        Returns:
            Lista de URLs de autobuses individuales.
        """
        pass

    @abc.abstractmethod
    def _extract_basic_info(self, soup: BeautifulSoup, source_url: str) -> Dict[str, Any]:
        """
        Extrae la información básica del autobús.

        Args:
            soup: Objeto BeautifulSoup del HTML.
            source_url: URL de origen.

        Returns:
            Diccionario con la información básica.
        """
        pass

    @abc.abstractmethod
    def _extract_year_make_model(self, title: str, soup: BeautifulSoup) -> Tuple[str, str, str]:
        """
        Extrae año, marca y modelo del título o de elementos específicos.

        Args:
            title: Título del listado.
            soup: Objeto BeautifulSoup del HTML.

        Returns:
            Tupla con (año, marca, modelo).
        """
        pass

    @abc.abstractmethod
    def _extract_technical_details(self, soup: BeautifulSoup, result: Dict[str, Any]) -> None:
        """
        Extrae detalles técnicos del autobús y los agrega al resultado.

        Args:
            soup: Objeto BeautifulSoup del HTML.
            result: Diccionario de resultados a modificar.
        """
        pass

    @abc.abstractmethod
    def _extract_overview_info(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Extrae información de descripción general, interior, exterior y características.

        Args:
            soup: Objeto BeautifulSoup del HTML.

        Returns:
            Diccionario con la información detallada.
        """
        pass

    @abc.abstractmethod
    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, Any]]:
        """
        Extrae URLs de imágenes y metadatos asociados.

        Args:
            soup: Objeto BeautifulSoup del HTML.
            base_url: URL base para construir URLs completas.

        Returns:
            Lista de diccionarios con información de imágenes.
        """
        pass

    # Métodos utilitarios comunes para todos los parsers

    def _extract_numeric_price(self, price_text: str) -> str:
        """
        Extrae el valor numérico del precio sin formatos.

        Args:
            price_text: Texto del precio con formato.

        Returns:
            Precio como cadena numérica sin formato.
        """
        if not price_text:
            return ""

        # Extraer solo dígitos
        import re
        digits = re.sub(r'[^\d.]', '', price_text)
        return digits

    def _extract_state_code(self, location: str) -> str:
        """
        Extrae código de estado de la ubicación.

        Args:
            location: Texto de ubicación.

        Returns:
            Código de estado de dos letras.
        """
        # Buscar patrón común: Ciudad, Estado Código-Postal
        import re
        match = re.search(r',\s*([A-Z]{2})', location)
        if match:
            return match.group(1)
        return "default"