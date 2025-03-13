from typing import Dict, Any
from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, Enum, DateTime, func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Bus(Base):
    """Modelo de tabla buses (información principal del autobús)."""

    __tablename__ = 'buses'

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(256))
    year = Column(String(10))
    make = Column(String(25))
    model = Column(String(50))
    body = Column(String(25))
    chassis = Column(String(25))
    engine = Column(String(60))
    transmission = Column(String(60))
    mileage = Column(String(100))
    passengers = Column(String(60))
    wheelchair = Column(String(60))
    color = Column(String(60))
    interior_color = Column(String(60))
    exterior_color = Column(String(60))
    published = Column(Boolean, default=False)
    featured = Column(Boolean, default=False)
    sold = Column(Boolean, default=False)
    scraped = Column(Boolean, default=False)
    draft = Column(Boolean, default=False)
    source = Column(String(300))
    source_url = Column(String(1000))
    price = Column(String(30))
    cprice = Column(String(30))
    vin = Column(String(60))
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
    created_at = Column(DateTime, default=func.current_timestamp())
    gvwr = Column(String(50))
    dimensions = Column(String(300))
    luggage = Column(Boolean, default=False)
    state_bus_standard = Column(String(25))
    airconditioning = Column(Enum('REAR', 'DASH', 'BOTH', 'OTHER', 'NONE'), default='NONE')
    location = Column(String(30))
    brake = Column(String(30))
    contact_email = Column(String(100))
    contact_phone = Column(String(100))
    us_region = Column(Enum('NORTHEAST', 'MIDWEST', 'WEST', 'SOUTHWEST', 'SOUTHEAST', 'OTHER'), default='OTHER')
    description = Column(Text)
    score = Column(Boolean, default=False)
    category_id = Column(Integer, default=0)

    def to_dict(self) -> Dict[str, Any]:
        """Convierte el modelo a un diccionario."""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class BusOverview(Base):
    """Modelo de tabla buses_overview (información adicional)."""

    __tablename__ = 'buses_overview'

    id = Column(Integer, primary_key=True, autoincrement=True)
    bus_id = Column(Integer, ForeignKey('buses.id'))
    mdesc = Column(Text)
    intdesc = Column(Text)
    extdesc = Column(Text)
    features = Column(Text)
    specs = Column(Text)

    def to_dict(self) -> Dict[str, Any]:
        """Convierte el modelo a un diccionario."""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class BusImage(Base):
    """Modelo de tabla buses_images (imágenes)."""

    __tablename__ = 'buses_images'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64))
    url = Column(String(1000))
    description = Column(Text)
    image_index = Column(Integer, default=0)
    bus_id = Column(Integer, ForeignKey('buses.id'))

    def to_dict(self) -> Dict[str, Any]:
        """Convierte el modelo a un diccionario."""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}