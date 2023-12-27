"""Module to represent a neighbourhood"""

from __future__ import annotations

from dataclasses import dataclass

from src.utils import haversine_distance
from src.location import House, Amenity, LocationType
from src.exceptions import InvalidLocation


@dataclass
class Neighbour:
    """Class to represent a neighbour"""

    house: House
    amenity: Amenity

    @property
    def distance(self) -> float:
        """Calculate the distance between a house and an amenity"""

        return haversine_distance(self.house.coords, self.amenity.coords)

    @property
    def score(self) -> float:
        """Calculate the score of a neighbour"""

        return self.amenity.size / self.distance

    @property
    def amenity_type(self) -> LocationType:
        """Return the type of the amenity"""

        return self.amenity.location_type

    def __lt__(self, other: Neighbour) -> bool:
        """Compare two neighbours"""

        return self.score < other.score

    def __gt__(self, other: Neighbour) -> bool:
        """Compare two neighbours"""

        return self.score > other.score

    def __eq__(self, other: Neighbour) -> bool:
        """Compare two neighbours"""

        return self.score == other.score

    def __repr__(self):
        """String representation of Neighbour"""

        return f"Neighbour({self.house.index}, {self.amenity.index}, {self.distance}, {self.score})"


@dataclass
class Neighbourhood:
    """Class to represent a neighbourhood"""

    house: House
    neighbours: dict[LocationType, list[Neighbour]]

    def __post_init__(self):
        """Post init method to set default values"""

        for location_type in self.neighbours:
            for neighbour in self.neighbours[location_type]:
                if neighbour.house != self.house:
                    raise InvalidLocation(
                        "House and neighbours must be in the same location"
                    )
