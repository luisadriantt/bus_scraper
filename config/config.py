import os

SCRAPING_CONFIG = {
    "pagination_pattern": "page={page_num}",
    "min_listings": 30,
    "request_delay": 10,  # segundos entre solicitudes
    "max_retries": 3,
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "timeout": 30,
}

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "bus_listings"),
    "charset": "utf8mb4",
}

LOG_CONFIG = {
    "level": os.getenv("LOG_LEVEL", "INFO"),
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": os.getenv("LOG_FILE", "bus_scraper.log"),
}

# Mapeo de regiones de EE.UU.
US_REGIONS = {
    "CA": "WEST",
    "NY": "NORTHEAST",
    "FL": "SOUTHEAST",
    "default": "OTHER",
}