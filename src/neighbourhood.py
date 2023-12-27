"""Module to represent a neighbourhood"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.utils import haversine_distance

if TYPE_CHECKING:
    from src.location import House, Amenity, LocationType


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


class NeighbourhoodFactory:
    """Class to create a neighbourhood"""

    @staticmethod
    def create_neighbours_of_location_type(
        house: House,
        amenities: list[Amenity],
        location_type: LocationType,
        number_of_neighbours: int,
    ) -> list[Neighbour]:
        """Create neighbours of a specific location type"""

        amenities_of_location_type = [
            amenity for amenity in amenities if amenity.location_type == location_type
        ]

        neighbours = [
            Neighbour(house, amenity) for amenity in amenities_of_location_type
        ]

        neighbours.sort(reverse=True)

        if number_of_neighbours < 0:
            return neighbours

        return neighbours[:number_of_neighbours]

    @staticmethod
    def create_neighbourhood(
        house: House,
        amenities: dict[LocationType, list[Amenity]],
        number_of_neighbours: dict[LocationType, int],
    ) -> Neighbourhood:
        """Create a neighbourhood"""

        neighbours = [
            NeighbourhoodFactory.create_neighbours_of_location_type(
                house, amenities[key], key, value
            )
            for key, value in number_of_neighbours.items()
        ]

        return Neighbourhood(house, neighbours)
