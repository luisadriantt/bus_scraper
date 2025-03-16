"""
Módulo para gestionar las conexiones y operaciones con la base de datos.
"""
import logging
from typing import Dict, Any, List, Optional
import pymysql
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker, Session

from config.config import DB_CONFIG
from src.database.models import Base, Bus, BusOverview, BusImage
from src.database.validators import validate_bus_data

logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Clase para gestionar las operaciones de base de datos.
    """

    def __init__(self):
        """Inicializa el gestor de base de datos."""
        self.connection_string = (
            f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@"
            f"{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}?charset={DB_CONFIG['charset']}"
        )
        self.engine = create_engine(self.connection_string)
        self.Session = sessionmaker(bind=self.engine)

    def create_database_if_not_exists(self) -> None:
        """
        Crea la base de datos si no existe.

        Utiliza una conexión directa con pymysql para crear la base de datos
        ya que SQLAlchemy requiere que la base de datos exista.
        """
        # Extraer el nombre de la base de datos de la configuración
        database_name = DB_CONFIG['database']

        # Crear una conexión sin especificar la base de datos
        connection_params = {
            'host': DB_CONFIG['host'],
            'port': DB_CONFIG['port'],
            'user': DB_CONFIG['user'],
            'password': DB_CONFIG['password'],
            'charset': DB_CONFIG['charset']
        }

        try:
            # Conectar sin especificar la base de datos
            connection = pymysql.connect(**connection_params)
            cursor = connection.cursor()

            # Intentar crear la base de datos si no existe
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{database_name}` CHARACTER SET {DB_CONFIG['charset']}")

            logger.info(f"Base de datos '{database_name}' creada o verificada exitosamente")

            # Cerrar la conexión
            cursor.close()
            connection.close()

        except pymysql.Error as e:
            logger.error(f"Error al crear la base de datos: {str(e)}")
            raise

    def create_tables(self) -> None:
        """
        Crea las tablas en la base de datos si no existen.
        """
        try:
            Base.metadata.create_all(self.engine)
            logger.info("Tablas creadas o verificadas exitosamente")
        except SQLAlchemyError as e:
            logger.error(f"Error al crear tablas: {str(e)}")
            raise

    def insert_bus_data(self, bus_data: Dict[str, Any]) -> Optional[int]:
        """
        Inserta datos de un autobús en la base de datos.

        Args:
            bus_data: Diccionario con datos del autobús y sus relaciones.

        Returns:
            ID del autobús insertado o None si hubo un error.
        """
        session = self.Session()
        try:
            # Validar datos antes de insertar
            valid, errors = validate_bus_data(bus_data)
            if not valid:
                logger.error(f"Datos de autobús inválidos: {errors}")
                return None

            # Extraer secciones de datos
            bus_info = bus_data.get("bus_info", {})
            overview_info = bus_data.get("overview_info", {})
            images_info = bus_data.get("images_info", [])

            # Verificar si el autobús ya existe (por URL o VIN)
            existing_bus = None
            if bus_info.get("source_url"):
                if 'daimler' not in bus_info.get("source_url"):
                    existing_bus = session.query(Bus).filter_by(source_url=bus_info["source_url"]).first()

            if not existing_bus and bus_info.get("vin"):
                existing_bus = session.query(Bus).filter_by(vin=bus_info["vin"]).first()

            if existing_bus:
                logger.info(f"Autobús ya existe en la base de datos, ID: {existing_bus.id}")
                return existing_bus.id

            # Crear nuevo registro de autobús
            new_bus = Bus(**bus_info)
            session.add(new_bus)
            session.flush()  # Para obtener el ID generado

            # Crear registro de descripción general
            if overview_info:
                overview_info["bus_id"] = new_bus.id
                bus_overview = BusOverview(**overview_info)
                session.add(bus_overview)

            # Crear registros de imágenes
            for img_info in images_info:
                img_info["bus_id"] = new_bus.id
                bus_image = BusImage(**img_info)
                session.add(bus_image)

            session.commit()
            logger.info(f"Autobús insertado exitosamente, ID: {new_bus.id}")
            return new_bus.id

        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error al insertar datos del autobús: {str(e)}")
            return None
        finally:
            session.close()

    def insert_many_buses(self, buses_data: List[Dict[str, Any]]) -> List[int]:
        """
        Inserta múltiples registros de autobuses en la base de datos.

        Args:
            buses_data: Lista de diccionarios con datos de autobuses.

        Returns:
            Lista de IDs de autobuses insertados.
        """
        inserted_ids = []

        for bus_data in buses_data:
            bus_id = self.insert_bus_data(bus_data)
            if bus_id:
                inserted_ids.append(bus_id)

        logger.info(f"Se insertaron {len(inserted_ids)} de {len(buses_data)} autobuses")
        return inserted_ids

    def get_bus_by_id(self, bus_id: int) -> Optional[Dict[str, Any]]:
        """
        Obtiene los datos completos de un autobús por su ID.

        Args:
            bus_id: ID del autobús.

        Returns:
            Diccionario con los datos del autobús o None si no existe.
        """
        session = self.Session()
        try:
            bus = session.query(Bus).filter_by(id=bus_id).first()

            if not bus:
                return None

            # Obtener datos relacionados
            overview = session.query(BusOverview).filter_by(bus_id=bus_id).first()
            images = session.query(BusImage).filter_by(bus_id=bus_id).all()

            # Convertir a diccionario
            result = {
                "bus_info": bus.to_dict(),
                "overview_info": overview.to_dict() if overview else {},
                "images_info": [img.to_dict() for img in images]
            }

            return result

        except SQLAlchemyError as e:
            logger.error(f"Error al obtener autobús ID {bus_id}: {str(e)}")
            return None
        finally:
            session.close()
