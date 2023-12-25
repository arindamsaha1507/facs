"""Module for location class"""

from __future__ import annotations

from typing import TYPE_CHECKING
from dataclasses import dataclass, field
from enum import Enum

import pandas as pd

from src.constants import path


if TYPE_CHECKING:
    from src.person import Person


class InvalidLocation(ValueError):
    """Exception for invalid location"""

    def __init__(self, message):
        """Constructor for InvalidLocation"""
        self.message = message
        super().__init__(self.message)


class LocationType(Enum):
    """Enum for location types"""

    HOUSE = 1
    OFFICE = 2
    SCHOOL = 3
    HOSPITAL = 4
    LEISURE = 5
    SHOPPING = 6
    SUPERMARKET = 7
    PARK = 8

    def __repr__(self):
        """String representation of LocationType"""
        return self.name.title()


@dataclass
class LatLon:
    """Class to represent a longitude and latitude"""

    lat: float
    lon: float

    def __post_init__(self):
        if self.lon < -180 or self.lon > 180:
            raise InvalidLocation("Longitude must be between -180 and 180")
        if self.lat < -90 or self.lat > 90:
            raise InvalidLocation("Latitude must be between -90 and 90")

    def __repr__(self):
        """String representation of LonLat"""

        if self.lon < 0:
            lon = f"{- self.lon} W"
        else:
            lon = f"{self.lon} E"

        if self.lat < 0:
            lat = f"{- self.lat} S"
        else:
            lat = f"{self.lat} N"

        return f"({lat}, {lon})"


@dataclass
class Location:
    """Class to represent a location"""

    index: int
    coords: LatLon
    size: int

    def __post_init__(self):
        """Post init method to set default values"""

        if self.size < 0:
            raise InvalidLocation("Size must be greater or equal to 0")


@dataclass
class House(Location):
    """Class to represent a house"""

    location_type: LocationType = field(default=LocationType.HOUSE, init=False)
    size: int = field(default=0, init=False)

    agents: list[Person] = field(default_factory=list, init=False, repr=False)


@dataclass
class Amenity(Location):
    """Class to represent an amenity"""

    location_type: LocationType

    def __post_init__(self):
        """Post init method to set default values"""

        if self.location_type == LocationType.HOUSE:
            raise InvalidLocation("Amenity cannot be a house")


class LocationFactory:
    """Factory class for locations"""

    @staticmethod
    def read_locations_file(filename: str) -> pd.DataFrame:
        """Read locations from a file"""

        data = pd.read_csv(filename, header=None)
        data.columns = ["location_type", "lon", "lat", "size"]
        data["index"] = data.index

        return data

    @staticmethod
    def create_house(index: int, lon: float, lat: float) -> House:
        """Create a house"""
        return House(index, LatLon(lat, lon))

    @staticmethod
    def bulk_create_houses(data: pd.DataFrame) -> list[House]:
        """Create a list of houses"""

        return list(
            map(
                lambda x: LocationFactory.create_house(x["index"], x["lon"], x["lat"]),
                data.to_dict("records"),
            )
        )

    @staticmethod
    def bulk_create_amenities(
        data: pd.DataFrame, location_type: LocationType
    ) -> list[Amenity]:
        """Create a list of amenities"""

        return list(
            map(
                lambda x: LocationFactory.create_amenity(
                    x["index"],
                    x["lon"],
                    x["lat"],
                    x["size"],
                    location_type,
                ),
                data.to_dict("records"),
            )
        )

    @staticmethod
    def create_amenity(
        index: int, lon: float, lat: float, size: int, location_type: LocationType
    ) -> Amenity:
        """Create an amenity"""
        return Amenity(index, LatLon(lat, lon), size, location_type)

    @staticmethod
    def create_all_buildings(filename: str) -> dict[LocationType, list[Location]]:
        """Create all buildings from a file"""

        data = LocationFactory.read_locations_file(filename)

        buildings = {}

        for location_type in LocationType:
            buildings_data = data[data["location_type"] == location_type.name.lower()]

            if location_type == LocationType.HOUSE:
                buildings[location_type] = LocationFactory.bulk_create_houses(
                    buildings_data
                )
            else:
                buildings[location_type] = LocationFactory.bulk_create_amenities(
                    buildings_data, location_type
                )

        return buildings


if __name__ == "__main__":
    print(House(1, LatLon(2, 3)))
    print(Amenity(2, LatLon(4, 5), 5, LocationType.HOSPITAL))
    print(LocationFactory.create_all_buildings(path.buildings_file))
    # print(LocationType.HOUSE.name)
