import sys
import yaml

def full_lockdown(e):
  e.remove_all_measures()
  e.add_closure("school", 0)
  e.add_closure("leisure", 0)
  e.add_partial_closure("shopping", 0.8)
  # mimicking a 75% reduction in social contacts.
  e.add_social_distance_imp9()
  e.add_work_from_home()
  e.add_case_isolation()
  e.add_household_isolation()


def read_vaccine_yml(e, date, ymlfile):
  with open(ymlfile) as f:
    v = yaml.safe_load(f)
  
    vaccine_effect_time = 21
    if "vaccine_effect_time" in v:
      vaccine_effect_time = v["vaccine_effect_time"]
    else:
      print("warning, {} does not contain field vaccine_effect time.".format(ymlfile))

    if date in v:
      dv = v[date]
      if "vaccines_per_day" in dv:
        e.vaccinations_available = int(dv["vaccines_per_day"])
      if "vaccine_age_limit" in dv:
        e.vaccinations_age_limit = int(dv["vaccine_age_limit"])
      if "no_symptoms" in dv:
        e.vac_no_symptoms = float(dv["no_symptoms"])
      if "no_transmission" in dv:
        e.vac_no_transmission = float(dv["no_transmission"])


      #dvb = v[date]["booster"]
      # fields:
      # boosters_per_day: 10 # this number is SUBTRACTED from vaccines_per_day.
      # booster_age_limit: 70
      # no_symptoms: 0.75
      # no_transmission: 0.6
      # TO BE IMPLEMENTED


__measure_mask_uptake = 0.0
__measure_mask_uptake_shopping = 0.0
__measure_social_distance = 0.0

def read_lockdown_yml(e, ymlfile="covid_data/measures.yml"):
  global __measure_mask_uptake, __measure_mask_uptake_shopping, __measure_social_distance
  with open(ymlfile) as f:
    m = yaml.safe_load(f)

  if(m["keyworker_fraction"]):
    e.keyworker_fraction = float(m["keyworker_fraction"])

  date_format = m["date_format"]

  # entry for backwards compatibility
  if date_format == "%d/%m/%Y":
    date_format = '%-d/%-m/%Y'

  date = e.get_date_string(date_format)

  if date in m:
    e.remove_all_measures()

    dm = m[date]

    if("case_isolation" in dm):
      if(dm["case_isolation"] == True):
        e.add_case_isolation()
      if(dm["case_isolation"] == False):
        e.reset_case_isolation()
    if("household_isolation" in dm):
      if(dm["household_isolation"] == True):
        e.add_household_isolation()
      if(dm["household_isolation"] == False):
        e.reset_household_isolation()

    if("external_multiplier" in dm):
      e.external_travel_multiplier = float(dm["external_multiplier"])

    if("partial_closure" in dm):
      for pc_key in dm["partial_closure"]:
        e.add_partial_closure(pc_key, dm["partial_closure"][pc_key])

    if("closure" in dm):
      for loc_name in dm["closure"]:
        e.add_closure(loc_name, 0) # add closure starting immediately (indicated by the 0)

    if("work_from_home" in dm):
      e.add_work_from_home(float(dm["work_from_home"]))


    # Social distance variable parsing.
    do_sd = False #bool to indicate whether social distancing needs to be recalculated.

    if("mask_uptake" in dm):
      __measure_mask_uptake = float(dm["mask_uptake"])
      do_sd = True

    if("mask_uptake_shopping" in dm):
      __measure_mask_uptake_shopping = float(dm["mask_uptake_shopping"])
      do_sd = True

    if("social_distance" in dm):
      __measure_social_distance = float(dm["social_distance"])  
      do_sd = True

    if do_sd:
      e.add_social_distance(2.0, compliance = __measure_social_distance, mask_uptake=__measure_mask_uptake, mask_uptake_shopping=__measure_mask_uptake_shopping)


    if("traffic_multiplier" in dm):
      e.traffic_multiplier = float(dm["traffic_multiplier"])

    if("track_trace_efficiency" in dm):
      e.track_trace__multiplier = 1.0 - float(dm["track_trace_efficiency"])

    print(date)
    print(dm)


def update_hospital_protection_factor_uk(e, t):
  e.hospital_protection_factor = 1.0
  if t == 30: # start of testing ramp up in early april.
    e.hospital_protection_factor = 0.8
  if t == 40: 
    e.hospital_protection_factor = 0.6
  if t == 50:
    e.hospital_protection_factor = 0.45
  if t == 60:
    e.hospital_protection_factor = 0.3
  if t == 70: # testing ramped up considerably by the end of April.
    e.hospital_protection_factor = 0.2
  if t == 85:
    e.hospital_protection_factor = 0.15
  if t == 100:
    e.hospital_protection_factor = 0.10


def calculate_mutating_infection_rate(fraction, source=0.07, dest=0.1):
  # Original infection rate is 0.07 (COVID-19 disease.yml)
  # destination infection rate is "up to 70% higher", so we set it to 0.07*1.5=0.105.

  if fraction > 1.0:
    print("Error: fraction > 1.0", file=sys.stderr)
    sys.exit()

  return (1.0-fraction)*source + (fraction*dest)


def enact_measures_and_evolutions(e, t, measures_yml, vaccinations_yml):

  # add in Alpha mutation
  # Prevalence increases linearly from Oct 22 (1%) to Jan 30th (100%)
  if t > 235 and t < 336:
    a = e.disease.infection_rate
    fraction = (t - 235) * 0.01
    e.disease.infection_rate = calculate_mutating_infection_rate(fraction, 0.07, 0.11) # https://cmmid.github.io/topics/covid19/uk-novel-variant.html
    print("infection rate adjusted from ",a," to ", e.disease.infection_rate, file=sys.stderr)


  # add in Delta mutation
  # Prevalence increases linearly from Apr 21 (1%) to June 10th (100%)
  if t > 416 and t < 467:
    fraction = (t - 416) * 0.02
    e.disease.infection_rate = calculate_mutating_infection_rate(fraction, 0.11, 0.165) # https://www.ecdc.europa.eu/en/publications-data/threat-assessment-emergence-and-impact-sars-cov-2-delta-variant

    # our estimate is 50% here, as Delta gains full dominance in this period.
    # https://www.gov.uk/government/news/confirmed-cases-of-covid-19-variants-identified-in-uk#:~:text=The%20Delta%20variant%20currently%20accounts,of%20cases%20across%20the%20UK.&text=In%20total%2C%203%2C692%20people%20have,the%20Delta%20and%20Beta%20variants.l
    print("infection rate adjusted to ", e.disease.infection_rate, file=sys.stderr)

  read_vaccine_yml(e, e.get_date_string(), "covid_data/{}.yml".format(vaccinations_yml))

  update_hospital_protection_factor_uk(e,t)

  e.vac_duration = 273
  e.immunity_duration = 273

  read_lockdown_yml(e, "covid_data/{}.yml".format(measures_yml))


