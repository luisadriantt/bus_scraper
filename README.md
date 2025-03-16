# School Bus Listings Scraper

Este proyecto es un scraper de listados de autobuses escolares diseñado para extraer información detallada de sitios web de inventario de autobuses, estructurar los datos y almacenarlos en una base de datos MySQL.

## Características

- Extracción de datos completos de autobuses escolares incluyendo:
  - Información básica (título, año, marca, modelo, precio, etc.)
  - Detalles técnicos (motor, transmisión, GVWR, etc.)
  - Descripciones y características
  - Imágenes y metadatos asociados
- Soporte para diferentes bibliotecas de scraping:
  - Requests + BeautifulSoup
  - Selenium para sitios con contenido dinámico
- Procesamiento de datos:
  - Validación de datos según el esquema de base de datos
  - Limpieza y normalización de campos
  - Detección automática de duplicados
- Integración con base de datos:
  - Modelo ORM completo utilizando SQLAlchemy
  - Esquema basado en los requisitos proporcionados
  - Generación de dumps de base de datos

## Requisitos

- Python 3.8+
- Las bibliotecas especificadas en `requirements.txt`
- MySQL

## Instalación

1. Clonar el repositorio:
   ```
   git clone https://github.com/luisadriantt/bus-scraper.git
   cd bus-scraper
   ```

2. Crear un entorno virtual (recomendado):
   ```
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```

3. Instalar dependencias:
   ```
   pip install -r requirements.txt
   ```

4. Configurar base de datos:
   - Crear una base de datos MySQL
   - Copiar `.env.example` a `.env` y configurar las credenciales de la base de datos

## Uso

### Scraping de páginas de listado de autobuses

Para extraer datos de páginas que contienen listados de varios autobuses:

```bash
python -m src.main --urls https://busesforsale.com/inventory
```

El sistema detectará automáticamente que es una página de listado, extraerá las URLs de todos los autobuses individuales y luego obtendrá los datos detallados de cada uno.

### Scraping de autobuses individuales

Para extraer datos de autobuses específicos:

```bash
python -m src.main --urls {url(s}
```

### Scraping desde un archivo

Para extraer URLs desde un archivo:

```bash
python -m src.main --url-file urls.txt
```

### Opciones adicionales

- `--selenium`: Usar Selenium para el scraping (útil para sitios con JavaScript)

Cómo correr:

```bash
# Scrapear página de dimlercoaches
python -m src.main --urls https://www.daimlercoachesnorthamerica.com/pre-owned-motor-coaches --selenium

# Scrapear página de rossbus
python -m src.main --urls https://www.rossbus.com/school-buses

# Scrapear página de microbird
python -m src.main --urls https://www.microbird.com/school-vehicles
```

## Estructura del Proyecto

```
bus_scraper/
├── README.md                   # Documentación del proyecto
├── requirements.txt            # Dependencias del proyecto
├── config/
│   └── config.py               # Configuraciones globales
├── src/
│   ├── __init__.py
│   ├── scraper/
│   │   ├── __init__.py
│   │   ├── bus_scraper.py      # Clase principal del scraper
│   │   ├── parsers.py          # Funciones/clases para parsear datos
│   │   └── utils.py            # Utilidades para scraping
│   ├── database/
│   │   ├── __init__.py
│   │   ├── db_manager.py       # Gestión de conexiones y operaciones
│   │   ├── models.py           # Modelos de datos ORM
│   │   └── validators.py       # Validación de datos
│   └── main.py                 # Punto de entrada principal
└── tests/                      # Tests unitarios y de integración
    ├── __init__.py
    ├── test_scraper.py
    └── test_database.py
```

## Consideraciones Técnicas

### Rendimiento

- El scraper incluye retardos configurables entre solicitudes para evitar sobrecargar el servidor objetivo.
- Se recomienda un límite razonable de listados por ejecución para evitar bloqueos.

### Anti-detección

- El scraper utiliza user-agents realistas y retardos variables.
- Para sitios con medidas anti-bot avanzadas, utiliza la opción `--selenium`.

### Manejo de fallos

- Implementa reintentos automáticos para solicitudes fallidas.
- Mantiene logs detallados de errores y progreso.
