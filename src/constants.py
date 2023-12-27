"""Module for constants used in the project."""

from dataclasses import dataclass


@dataclass
class Path:
    """Class for path constants."""

    data_dir: str = "covid_data"

    buildings_file: str = "calarasi_buildings.csv"
    demographics_file: str = "calarasi_demographics.csv"
    disease_file: str = "calarasi_disease.csv"
    vaccination_file: str = "calarasi_vaccination.csv"

    def __post_init__(self):
        """Ensure that all the parameters are strings."""

        for attr in self.__dict__:
            if not isinstance(getattr(self, attr), str):
                raise TypeError(f"{attr} must be str")

            if attr.endswith("_file"):
                setattr(self, attr, f"{self.data_dir}/{getattr(self, attr)}")


path = Path()
