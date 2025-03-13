import re
import logging
from urllib.parse import urlparse
from typing import Dict, Type

from src.scraper.parsers import BaseBusParser
from src.scraper.parsers_impl import (
    DefaultBusParser,
    RossBusParser,
    DaimlerParser,
    MicrobirdParser
)

logger = logging.getLogger(__name__)


class ParserFactory:
    """
    Fábrica que proporciona el parser adecuado según la URL.
    """

    def __init__(self):
        """Inicializa el registro de parsers."""
        self.parsers_by_domain: Dict[str, Type[BaseBusParser]] = {}
        self.parsers_by_pattern: Dict[re.Pattern, Type[BaseBusParser]] = {}
        self.default_parser = DefaultBusParser

        # Registrar parsers conocidos
        self._register_parsers()

    def _register_parsers(self):
        """Registra todos los parsers conocidos."""
        # Registro por dominio exacto
        self.register_parser_for_domain("rossbus.com", RossBusParser)
        self.register_parser_for_domain("www.rossbus.com", RossBusParser)
        self.register_parser_for_domain("https://www.rossbus.com", RossBusParser)
        self.register_parser_for_domain("https://www.daimlercoachesnorthamerica.com/pre-owned-motor-coaches", DaimlerParser)
        self.register_parser_for_domain("www.daimlercoachesnorthamerica.com/pre-owned-motor-coaches", DaimlerParser)
        self.register_parser_for_domain("https://www.microbird.com/school-vehicles", MicrobirdParser)
        self.register_parser_for_domain("www.microbird.com/school-vehicles", MicrobirdParser)

    def register_parser_for_domain(self, domain: str, parser_class: Type[BaseBusParser]):
        """
        Registra un parser para un dominio específico.

        Args:
            domain: Dominio para el que aplica este parser.
            parser_class: Clase de parser a utilizar.
        """
        self.parsers_by_domain[domain] = parser_class

    def register_parser_for_pattern(self, pattern: str, parser_class: Type[BaseBusParser]):
        """
        Registra un parser para un patrón de URL (usando regex).

        Args:
            pattern: Patrón regex para URLs.
            parser_class: Clase de parser a utilizar.
        """
        compiled_pattern = re.compile(pattern)
        self.parsers_by_pattern[compiled_pattern] = parser_class

    def get_parser(self, url: str) -> BaseBusParser:
        """
        Obtiene el parser apropiado para una URL.

        Args:
            url: URL a parsear.

        Returns:
            Instancia del parser adecuado.
        """
        try:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc

            # Intentar encontrar por dominio exacto
            if domain in self.parsers_by_domain:
                parser_class = self.parsers_by_domain[domain]
                logger.info(f"Usando parser específico para dominio {domain}: {parser_class.__name__}")
                return parser_class()

            # Intentar encontrar por patrón en la URL completa
            for pattern, parser_class in self.parsers_by_pattern.items():
                if pattern.search(url):
                    logger.info(f"Usando parser específico para patrón {pattern.pattern}: {parser_class.__name__}")
                    return parser_class()

            # Si no se encuentra un parser específico, usar el parser por defecto
            logger.warning(f"No se encontró un parser específico para {url}. Usando parser por defecto.")
            return self.default_parser()

        except Exception as e:
            logger.error(f"Error al determinar el parser para {url}: {str(e)}. Usando parser por defecto.")
            return self.default_parser()