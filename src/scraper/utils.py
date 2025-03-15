import time
import logging
import functools
import json
from typing import Callable, Any, TypeVar
from selenium import webdriver
from selenium.common import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from webdriver_manager.chrome import ChromeDriverManager

logger = logging.getLogger(__name__)

# Definición de tipo genérico para funciones decoradas
F = TypeVar('F', bound=Callable[..., Any])


def setup_selenium_driver() -> webdriver.Chrome:
    """
    Configura un driver de Selenium para Chrome con opciones headless.

    Returns:
        Instancia configurada de webdriver.Chrome
    """
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")

    # Configurar user agent para evitar detección de headless
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

    # Inicializar el driver
    service = Service(ChromeDriverManager().install())
    # service = Service('/usr/local/bin/chromedriver')
    driver = webdriver.Chrome(service=service, options=chrome_options)

    return driver


def retry_on_failure(max_retries: int = 3, delay: int = 5) -> Callable[[F], F]:
    """
    Decorador para reintentar una función en caso de error.

    Args:
        max_retries: Número máximo de reintentos.
        delay: Tiempo de espera entre reintentos en segundos.

    Returns:
        Decorador para la función.
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries >= max_retries:
                        logger.error(f"Error en {func.__name__} después de {max_retries} intentos: {str(e)}")
                        raise

                    logger.warning(
                        f"Error en {func.__name__} (intento {retries}/{max_retries}): {str(e)}. Reintentando en {delay} segundos...")
                    time.sleep(delay)

            return None

        return wrapper

    return decorator


def save_to_json(data: Any, filename: str) -> None:
    """
    Guarda datos en un archivo JSON.

    Args:
        data: Datos a guardar.
        filename: Nombre del archivo.
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Datos guardados exitosamente en {filename}")
    except Exception as e:
        logger.error(f"Error al guardar datos en {filename}: {str(e)}")


def wait_for_element_to_have_content(parent, selector, timeout=10, check_interval=0.5):
    """
    Espera a que un elemento tenga contenido de texto o HTML

    Args:
        parent: El elemento padre donde buscar
        selector: El selector CSS para encontrar el elemento
        timeout: Tiempo máximo de espera en segundos
        check_interval: Intervalo entre comprobaciones en segundos

    Returns:
        El elemento cuando tiene contenido
    """
    end_time = time.time() + timeout

    while time.time() < end_time:
        try:
            element = parent.find_element(By.CSS_SELECTOR, selector)

            # Verificar si tiene contenido (texto o HTML)
            if element.text.strip() or element.get_attribute("innerHTML").strip():
                return element
        except:
            logger.error(f"Error en el elemento {selector} en {parent}")

        time.sleep(check_interval)

    raise TimeoutException(f"El elemento '{selector}' no tiene contenido después de {timeout} segundos")


def html_to_text(html_content):
    """Convierte HTML a texto plano usando BeautifulSoup"""
    if isinstance(html_content, list):
        html_content = ''.join(html_content)

    # Crear objeto BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')

    # Obtener solo el texto
    text = soup.get_text(separator=' ', strip=True)

    return text