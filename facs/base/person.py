"""Module for the Person class."""

import random
import sys

import numpy as np
import yaml

from .needs import Needs
from .location_types import building_types_dict, building_types_data
from .utils import (
    probability,
    get_random_int,
    log_infection,
    log_hospitalisation,
    log_recovery,
    log_death,
)


needs = Needs("covid_data/needs.csv", list(building_types_dict.keys()))
antivax_chance = yaml.safe_load(open("covid_data/vaccinations.yml", encoding="utf-8"))[
    "antivax_fraction"
]


class Person:
    """Class for a person."""

    def __init__(self, location, household, ages):
        self.location = location  # current location
        self.location.increment_num_agents()
        self.home_location = location
        self.household = household
        self.mild_version = True
        self.hospitalised = False
        self.dying = False
        self.work_from_home = False
        self.school_from_home = False
        self.phase_duration = 0.0  # duration to next phase.
        self.symptoms_suppressed = (
            False  # Symptoms suppressed, e.g. due to vaccination, but still infectious.
        )

        self.antivax = False  # Refuses vaccines if true.
        if np.random.rand() < antivax_chance:  # 5% are antivaxxers.
            self.antivax = True

        self.status = "susceptible"
        # states: susceptible, exposed, infectious, recovered, dead, immune.
        self.symptomatic = False  # may be symptomatic if infectious
        self.status_change_time = -1

        self.age = np.random.choice(91, p=ages)  # age in years
        self.job = np.random.choice(4, 1, p=[0.865, 0.015, 0.08, 0.04])[
            0
        ]  # 0=default, 1=teacher (1.5%), 2=shop worker (8%), 3=health worker (4%)
        self.groups = {}  # used to assign a grouping to a person.
        self.hospital = None  # hospital location

    def assign_group(self, location_type, num_groups):
        """
        Used to assign a grouping to a person.
        For example, a campus may have 30 classes (num_groups = 30). Then you would use:
        assign_group("school", 30)
        The location type should match the corresponding personal needs category
        (e.g., school or supermarket).
        """
        self.groups[building_types_dict[location_type]] = get_random_int(num_groups)

    def location_has_grouping(self, lid):
        """Check if a location has a particular grouping."""

        return lid in list(self.groups)

    def vaccinate(self, time, vac_no_symptoms, vac_no_transmission, vac_duration):
        """Vaccinate a person."""

        self.status_change_time = time  # necessary if vaccines give temporary immunity.
        if vac_duration > 0:
            if vac_duration > 100:
                self.phase_duration = np.random.gamma(vac_duration / 20.0, 20.0)
                # shape parameter is changed with variable, scale parameter is kept
                # fixed at 20 (assumption).

            else:
                self.phase_duration = np.poisson(vac_duration)

        if self.status == "susceptible":
            if probability(vac_no_transmission):
                self.status = "immune"
            elif probability(vac_no_symptoms):
                self.symptoms_suppressed = True
        # print("vac", self.status, self.symptoms_suppressed, self.phase_duration)

    def plan_visits(self, e):
        """
        Plan visits for the day.
        TODO: plan visits to classes not using nearest location (make an override).
        """

        if self.status in [
            "susceptible",
            "exposed",
            "infectious",
        ]:  # recovered people are assumed to be immune.
            personal_needs = needs.get_needs(self)
            for k, minutes in enumerate(personal_needs):
                nearest_locs = self.home_location.nearest_locations

                if minutes < 1:
                    continue
                elif k == building_types_dict["hospital"] and self.hospitalised:
                    location_to_visit = self.hospital

                elif k == building_types_dict["office"] and self.job > 0:
                    if self.job == 1:  # teacher
                        location_to_visit = nearest_locs[building_types_dict["school"]]
                    if self.job == 2:  # shop employee
                        location_to_visit = nearest_locs[
                            building_types_dict["shopping"]
                        ]
                    if self.job == 3:  # health worker
                        location_to_visit = nearest_locs[
                            building_types_dict["hospital"]
                        ]

                elif self.location_has_grouping(k):
                    location_to_visit = e.get_location_by_group(k, self.groups[k])

                elif nearest_locs[k]:
                    location_to_visit = nearest_locs[k]
                else:  # no known nearby locations.
                    continue

                e.visit_minutes += minutes

                if isinstance(location_to_visit, list):
                    loc_type = location_to_visit[0].loc_type

                    if building_types_data[loc_type]["weighted"]:
                        sizes = [x.sqm for x in location_to_visit]
                        prob = [x / sum(sizes) for x in sizes]
                        location_to_visit = np.random.choice(location_to_visit, p=prob)

                    else:
                        location_to_visit = random.choice(location_to_visit)

    def print_needs(self):
        print(self.age, needs.get_needs(self))

    def get_needs(self):
        return needs.get_needs(self)

    def get_hospitalisation_chance(self, disease):
        age = int(min(self.age, len(disease.hospital) - 1))
        return disease.hospital[age]

    def get_mortality_chance(self, disease):
        age = int(min(self.age, len(disease.hospital) - 1))
        return disease.mortality[age]

    def infect(self, e, severity="exposed", location_type="house"):
        # severity can be overridden to infectious when rigidly inserting cases.
        # but by default, it should be exposed.
        self.status = severity
        self.status_change_time = e.time
        self.mild_version = True
        self.hospitalised = False
        self.phase_duration = max(1, np.random.poisson(e.disease.incubation_period))
        e.num_infections_today += log_infection(
            e.time,
            self.location.location_x,
            self.location.location_y,
            location_type,
            e.rank,
            self.phase_duration,
        )

    def recover(self, e, location):
        if e.disease.immunity_duration > 0:
            self.phase_duration = np.random.gamma(
                e.disease.immunity_duration / 20.0, 20.0
            )  # shape parameter is changed with variable,
            # scale parameter is kept fixed at 20 (assumption).
        self.status = "recovered"
        self.status_change_time = e.time
        e.num_recoveries_today = log_recovery(
            e.time, self.location.location_x, self.location.location_x, location, e.rank
        )

    def progress_condition(self, e, t, disease):
        if self.status_change_time > t:
            return
        if self.status == "exposed":
            # print("exposed", t, self.status_change_time, self.phase_duration)
            if t - self.status_change_time >= int(self.phase_duration):
                self.status = "infectious"
                self.status_change_time = t
                if (
                    probability(self.get_hospitalisation_chance(disease))
                    and self.symptoms_suppressed is False
                ):
                    self.mild_version = False
                    # self.phase_duration =
                    # np.random.poisson(disease.period_to_hospitalisation
                    # - disease.incubation_period)
                    self.phase_duration = max(
                        1,
                        np.random.poisson(disease.period_to_hospitalisation)
                        - self.phase_duration,
                    )
                else:
                    self.mild_version = True
                    # self.phase_duration =
                    # np.random.poisson(disease.mild_recovery_period
                    # - disease.incubation_period)
                    self.phase_duration = max(
                        1,
                        np.random.poisson(disease.mild_recovery_period)
                        - self.phase_duration,
                    )

        elif self.status == "infectious":
            # mild version (may require hospital visits, but not ICU visits)
            if self.mild_version:
                if t - self.status_change_time >= self.phase_duration:
                    self.recover(e, "house")

            # non-mild version (will involve ICU visit)
            else:
                if not self.hospitalised:
                    if t - self.status_change_time >= self.phase_duration:
                        self.hospitalised = True
                        self.hospital = e.find_hospital()
                        if self.hospital is None:
                            print(
                                "Error: agent is hospitalised, but there are no "
                                "hospitals in the location graph."
                            )
                            sys.exit()
                        e.num_hospitalised += 1
                        e.num_hospitalisations_today = log_hospitalisation(
                            t,
                            self.location.location_x,
                            self.location.location_y,
                            self.age,
                            e.rank,
                        )

                        self.status_change_time = t
                        # hospitalisation is a status change,
                        # because recovery_period is from date of hospitalisation.
                        if probability(
                            self.get_mortality_chance(disease)
                            / self.get_hospitalisation_chance(disease)
                        ):
                            # avg mortality rate (divided by the average hospitalization rate).
                            # task: read from YML.
                            self.dying = True
                            self.phase_duration = np.random.poisson(
                                disease.mortality_period
                            )
                        else:
                            self.dying = False
                            self.phase_duration = np.random.poisson(
                                disease.recovery_period
                            )
                else:
                    if (
                        t - self.status_change_time >= self.phase_duration
                    ):  # from hosp. date
                        self.hospitalised = False
                        e.num_hospitalised -= 1
                        self.status_change_time = t
                        # decease
                        if self.dying:
                            self.status = "dead"
                            e.num_deaths_today = log_death(
                                t,
                                self.location.location_x,
                                self.location.location_y,
                                "hospital",
                                e.rank,
                            )
                        # hospital discharge
                        else:
                            self.recover(e, "hospital")

        elif e.disease.immunity_duration > 0 and (
            self.status in ("recovered", "immune")
        ):
            if t - self.status_change_time >= self.phase_duration:
                # print("susc.", self.status, self.phase_duration)
                self.status = "susceptible"
                self.symptoms_suppressed = False
