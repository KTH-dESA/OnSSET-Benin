# Author: Christopher Arderne
# Date: 26 November 2016
# Python version: 3.5

# Updated June 2018 by Andreas Sahlberg (KTH dESA)
# Modified grid algorithm and population calibration to improve computational speed

import logging
import pandas as pd
from math import pi, exp, log, sqrt, ceil
# from pyproj import Proj
import numpy as np
from collections import defaultdict
import os

logging.basicConfig(format='%(asctime)s\t\t%(message)s', level=logging.DEBUG)

# general
LHV_DIESEL = 9.9445485  # (kWh/l) lower heating value
HOURS_PER_YEAR = 8760

# Columns in settlements file must match these exactly
SET_COUNTRY = 'Country'  # This cannot be changed, lots of code will break
SET_X = 'X'  # Coordinate in metres/kilometres
SET_Y = 'Y'  # Coordinate in metres/kilometres
SET_X_DEG = 'X_deg'  # Coordinates in degrees
SET_Y_DEG = 'Y_deg'
SET_POP = 'Pop'  # Population in people per point (equally, people per km2)
SET_POP_CALIB = 'PopStartCalibrated'  # Calibrated population to reference year, same units
SET_POP_FUTURE = 'PopFuture'  # Project future population, same units
SET_GRID_DIST_CURRENT = 'GridDistCurrent'  # Distance in km from current grid
SET_GRID_DIST_PLANNED = 'GridDistPlan'  # Distance in km from current and future grid
SET_ROAD_DIST = 'RoadDist'  # Distance in km from road network
SET_NIGHT_LIGHTS = 'VIIRS'  # Intensity of night time lights (from NASA), range 0 - 63
SET_TRAVEL_HOURS = 'TravelHours'  # Travel time to large city in hours
SET_GHI = 'GHI'  # Global horizontal irradiance in kWh/m2/day
SET_WINDVEL = 'WindVel'  # Wind velocity in m/s
SET_WINDCF = 'WindCF'  # Wind capacity factor as percentage (range 0 - 1)
SET_HYDRO = 'Hydropower'  # Hydropower potential in kW
SET_HYDRO_DIST = 'HydropowerDist'  # Distance to hydropower site in km
SET_HYDRO_FID = 'HydropowerFID'  # the unique tag for eah hydropower, to not over-utilise
SET_SUBSTATION_DIST = 'SubstationDist'
SET_ELEVATION = 'Elevation'  # in metres
SET_SLOPE = 'Slope'  # in degrees
SET_LAND_COVER = 'LandCover'
SET_SOLAR_RESTRICTION = 'SolarRestriction'
SET_ROAD_DIST_CLASSIFIED = 'RoadDistClassified'
SET_SUBSTATION_DIST_CLASSIFIED = 'SubstationDistClassified'
SET_ELEVATION_CLASSIFIED = 'ElevationClassified'
SET_SLOPE_CLASSIFIED = 'SlopeClassified'
SET_LAND_COVER_CLASSIFIED = 'LandCoverClassified'
SET_COMBINED_CLASSIFICATION = 'GridClassification'
SET_GRID_PENALTY = 'GridPenalty'
SET_URBAN = 'IsUrban'  # Whether the site is urban (0 or 1)
SET_ENERGY_PER_HH = 'EnergyPerHH'
SET_NUM_PEOPLE_PER_HH = 'NumPeoplePerHH'
SET_ELEC_CURRENT = 'ElecStart'  # If the site is currently electrified (0 or 1)
SET_ELEC_FUTURE = 'ElecFuture'  # If the site has the potential to be 'easily' electrified in future
SET_NEW_CONNECTIONS = 'NewConnections'  # Number of new people with electricity connections
SET_NEW_CONNECTIONS_PROD = 'New_Connections_Prod' # Number of new people with electricity connections plus productive uses corresponding
SET_MIN_GRID_DIST = 'MinGridDist'
SET_LCOE_GRID = 'Grid'  # All lcoes in USD/kWh
SET_LCOE_SA_PV = 'SA_PV'
SET_LCOE_SA_DIESEL = 'SA_Diesel'
SET_LCOE_MG_WIND = 'MG_Wind'
SET_LCOE_MG_DIESEL = 'MG_Diesel'
SET_LCOE_MG_PV = 'MG_PV'
SET_LCOE_MG_HYDRO = 'MG_Hydro'
SET_LCOE_MG_HYBRID = 'MG_Hybrid'
SET_MIN_OFFGRID = 'MinimumOffgrid'  # The technology with lowest lcoe (excluding grid)
SET_MIN_OVERALL = 'MinimumOverall'  # Same as above, but including grid
SET_MIN_OFFGRID_LCOE = 'MinimumTechLCOE'  # The lcoe value for minimum tech
SET_MIN_OVERALL_LCOE = 'MinimumOverallLCOE'  # The lcoe value for overall minimum
SET_MIN_OVERALL_CODE = 'MinimumOverallCode'  # And a code from 1 - 7 to represent that option
SET_MIN_CATEGORY = 'MinimumCategory'  # The category with minimum lcoe (grid, minigrid or standalone)
SET_NEW_CAPACITY = 'NewCapacity'  # Capacity in kW
SET_INVESTMENT_COST = 'InvestmentCost'  # The investment cost in USD

# Columns in the specs file must match these exactly
SPE_COUNTRY = 'Country'
SPE_POP = 'Pop2016'  # The actual population in the base year
SPE_URBAN = 'UrbanRatio2016'  # The ratio of urban population (range 0 - 1) in base year
SPE_POP_FUTURE = 'Pop2030'
SPE_URBAN_FUTURE = 'UrbanRatio2030'
SPE_URBAN_MODELLED = 'UrbanRatioModelled'  # The urban ratio in the model after calibration (for comparison)
SPE_URBAN_CUTOFF = 'UrbanCutOff'  # The urban cutoff population calirated by the model, in people per km2
SPE_URBAN_GROWTH = 'UrbanGrowth'  # The urban growth rate as a simple multplier (urban pop future / urban pop present)
SPE_RURAL_GROWTH = 'RuralGrowth'  # Same as for urban
SPE_NUM_PEOPLE_PER_HH_RURAL = 'NumPeoplePerHHRural'
SPE_NUM_PEOPLE_PER_HH_URBAN = 'NumPeoplePerHHUrban'
SPE_DIESEL_PRICE_LOW = 'DieselPriceLow'  # Diesel price in USD/litre
SPE_DIESEL_PRICE_HIGH = 'DieselPriceHigh'  # Same, with a high forecast var
SPE_GRID_PRICE = 'GridPrice'  # Grid price of electricity in USD/kWh
SPE_GRID_CAPACITY_INVESTMENT = 'GridCapacityInvestmentCost'  # grid capacity investments costs from TEMBA USD/kW
SPE_GRID_LOSSES = 'GridLosses'  # As a ratio (0 - 1)
SPE_BASE_TO_PEAK = 'BaseToPeak'  # As a ratio (0 - 1)
SPE_EXISTING_GRID_COST_RATIO = 'ExistingGridCostRatio'
SPE_MAX_GRID_DIST = 'MaxGridDist'
SPE_ELEC = 'ElecActual'  # Actual current percentage electrified population (0 - 1)
SPE_ELEC_MODELLED = 'ElecModelled'  # The modelled version after calibration (for comparison)
SPE_MIN_NIGHT_LIGHTS = 'MinNightLights'
SPE_MAX_GRID_EXTENSION_DIST = 'MaxGridExtensionDist'
SPE_MAX_ROAD_DIST = 'MaxRoadDist'
SPE_POP_CUTOFF1 = 'PopCutOffRoundOne'
SPE_POP_CUTOFF2 = 'PopCutOffRoundTwo'


class Technology:
    """
    Used to define the parameters for each electricity access technology, and to calculate the LCOE depending on
    input parameters.
    """

    start_year = 2016
    end_year = 2030
    discount_rate = 0.08
    grid_cell_area = 1  # in km2, normally 1km2

    mv_line_cost = 9000  # USD/km
    lv_line_cost = 5000  # USD/km
    mv_line_capacity = 50  # kW/line
    lv_line_capacity = 10  # kW/line
    lv_line_max_length = 30  # km
    hv_line_cost = 53000  # USD/km
    mv_line_max_length = 50  # km
    hv_lv_transformer_cost = 5000  # USD/unit
    mv_increase_rate = 0.1  # percentage

    def __init__(self,
                 tech_life,  # in years
                 base_to_peak_load_ratio,
                 distribution_losses=0,  # percentage
                 connection_cost_per_hh=0,  # USD/hh
                 om_costs=0.0,  # OM costs as percentage of capital costs
                 capital_cost=0,  # USD/kW
                 capacity_factor=1.0,  # percentage
                 efficiency=1.0,  # percentage
                 diesel_price=0.0,  # USD/litre
                 grid_price=0.0,  # USD/kWh for grid electricity
                 standalone=False,
                 mg_pv=False,
                 mg_wind=False,
                 mg_diesel=False,
                 mg_hydro=False,
                 grid_capacity_investment=0.0,  # USD/kW for on-grid capacity investments (excluding grid itself)
                 diesel_truck_consumption=0,  # litres/hour
                 diesel_truck_volume=0,  # litres
                 om_of_td_lines=0):  # percentage

        self.distribution_losses = distribution_losses
        self.connection_cost_per_hh = connection_cost_per_hh
        self.base_to_peak_load_ratio = base_to_peak_load_ratio
        self.tech_life = tech_life
        self.om_costs = om_costs
        self.capital_cost = capital_cost
        self.capacity_factor = capacity_factor
        self.efficiency = efficiency
        self.diesel_price = diesel_price
        self.grid_price = grid_price
        self.standalone = standalone
        self.mg_pv = mg_pv
        self.mg_wind = mg_wind
        self.mg_diesel = mg_diesel
        self.mg_hydro = mg_hydro
        self.grid_capacity_investment = grid_capacity_investment
        self.diesel_truck_consumption = diesel_truck_consumption
        self.diesel_truck_volume = diesel_truck_volume
        self.om_of_td_lines = om_of_td_lines

    def pv_diesel_hybrid(self,
                         energy_per_hh,  # kWh/household/year as defined
                         max_ghi,  # highest annual GHI value encountered in the GIS data
                         max_travel_hours,  # highest value for travel hours encountered in the GIS data
                         diesel_no=1, # 50,  # number of diesel generators simulated
                         pv_no=1, #70, # number of PV panel sizes simulated
                         n_chg=0.92,  # charge efficiency of battery
                         n_dis=0.92,  # discharge efficiency of battery
                         lpsp=0.05,  # maximum loss of load allowed over the year, in share of kWh
                         battery_cost=150,  # battery capital capital cost, USD/kWh of storage capacity
                         pv_cost=2490,  # PV panel capital cost, USD/kW peak power
                         diesel_cost=550,  # diesel generator capital cost, USD/kW rated power
                         pv_life=20,  # PV panel expected lifetime, years
                         diesel_life=15,  # diesel generator expected lifetime, years
                         pv_om=0.015,  # annual OM cost of PV panels
                         diesel_om=0.1,  # annual OM cost of diesel generator
                         k_t=0.005):  # temperature factor of PV panels
        ghi = pd.read_csv('Supplementary_files\GHI_hourly.csv', usecols=[4], sep=';', skiprows=21).as_matrix()
        # hourly GHI values downloaded from SoDa for one location in the country
        temp = pd.read_csv('Supplementary_files\Temperature_hourly.csv', usecols=[4], sep=';', skiprows=21).as_matrix()
        # hourly temperature values downloaded from SoDa for one location in the country
        hour_numbers = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23) * 365

        LHV_DIESEL = 9.9445485
        dod_max = 0.8  # maximum depth of discharge of battery

        # the values below define the load curve for the five tiers. The values reflect the share of the daily demand
        # expected in each hour of the day (sum of all values for one tier = 1)
        tier5_load_curve = np.array([0.021008403, 0.021008403, 0.021008403, 0.021008403, 0.027310924, 0.037815126,
                                     0.042016807, 0.042016807, 0.042016807, 0.042016807, 0.042016807, 0.042016807,
                                     0.042016807, 0.042016807, 0.042016807, 0.042016807, 0.046218487, 0.050420168,
                                     0.067226891, 0.084033613, 0.073529412, 0.052521008, 0.033613445, 0.023109244])
        tier4_load_curve = np.array([0.017167382, 0.017167382, 0.017167382, 0.017167382, 0.025751073, 0.038626609,
                                     0.042918455, 0.042918455, 0.042918455, 0.042918455, 0.042918455, 0.042918455,
                                     0.042918455, 0.042918455, 0.042918455, 0.042918455, 0.0472103, 0.051502146,
                                     0.068669528, 0.08583691, 0.075107296, 0.053648069, 0.034334764, 0.021459227])
        tier3_load_curve = np.array([0.013297872, 0.013297872, 0.013297872, 0.013297872, 0.019060284, 0.034574468,
                                     0.044326241, 0.044326241, 0.044326241, 0.044326241, 0.044326241, 0.044326241,
                                     0.044326241, 0.044326241, 0.044326241, 0.044326241, 0.048758865, 0.053191489,
                                     0.070921986, 0.088652482, 0.077570922, 0.055407801, 0.035460993, 0.019946809])
        tier2_load_curve = np.array([0.010224949, 0.010224949, 0.010224949, 0.010224949, 0.019427403, 0.034764826,
                                     0.040899796, 0.040899796, 0.040899796, 0.040899796, 0.040899796, 0.040899796,
                                     0.040899796, 0.040899796, 0.040899796, 0.040899796, 0.04601227, 0.056237219,
                                     0.081799591, 0.102249489, 0.089468303, 0.06390593, 0.038343558, 0.017893661])
        tier1_load_curve = np.array([0, 0, 0, 0, 0.012578616, 0.031446541, 0.037735849, 0.037735849, 0.037735849,
                                     0.037735849, 0.037735849, 0.037735849, 0.037735849, 0.037735849, 0.037735849,
                                     0.037735849, 0.044025157, 0.062893082, 0.100628931, 0.125786164, 0.110062893,
                                     0.078616352, 0.044025157, 0.012578616])
        if energy_per_hh < 75:
            load_curve = tier1_load_curve * energy_per_hh / 365
        elif energy_per_hh < 365:
            load_curve = tier2_load_curve * energy_per_hh / 365
        elif energy_per_hh < 1241:
            load_curve = tier3_load_curve * energy_per_hh / 365
        elif energy_per_hh < 2993:
            load_curve = tier4_load_curve * energy_per_hh / 365
        else:
            load_curve = tier5_load_curve * energy_per_hh / 365


        def pv_diesel_capacities(pv_capacity, battery_size, diesel_capacity, initital_condition=False):
            condition = 1
            ren_limit = 0
            break_hour = 17
            while condition > lpsp:
                dod = np.zeros(24)
                battery_use = np.zeros(24)  # Stores the amount of battery discharge during the day
                fuel_result = 0
                battery_life = 0
                soc = 0.5
                unmet_demand = 0
                annual_diesel_gen = 0
                for i in range(8760):
                    diesel_gen = 0
                    battery_use[hour_numbers[i]] = 0.0002 * soc  # Battery self-discharge
                    soc *= 0.9998
                    t_cell = temp[i] + 0.0256 * ghi[i]  # PV cell temperature
                    pv_gen = pv_capacity * 0.9 * ghi[i] / 1000 * (
                    1 - k_t * (t_cell - 298.15))  # PV generation in the hour
                    net_load = load_curve[hour_numbers[i]] - pv_gen  # remaining load not met by PV panels
                    if net_load <= 0:  # If pv generation is greater than load the excess energy is stored in battery
                        if battery_size > 0:
                            soc -= n_chg * net_load / battery_size
                        net_load = 0
                    max_diesel = min(diesel_capacity, net_load + (1 - soc) * battery_size / n_chg)
                    #  Maximum aount of diesel needed to supply load and charge battery, limited by rated diesel capacity

                    # Below is the dispatch strategy for the diesel generator as described in word document
                    if break_hour + 1 > hour_numbers[i] > 4 and net_load > soc * battery_size * n_dis:
                        diesel_gen = min(diesel_capacity, max(0.4 * diesel_capacity, net_load))
                    elif 23 > hour_numbers[i] > break_hour and max_diesel > 0.40 * diesel_capacity:
                        diesel_gen = max_diesel
                    elif n_dis * soc * battery_size < net_load:
                        diesel_gen = max(0.4 * diesel_capacity, max_diesel)

                    if diesel_gen > 0:  # Fuel consumption is stored
                        fuel_result += diesel_capacity * 0.08145 + diesel_gen * 0.246
                        annual_diesel_gen += diesel_gen

                    if (net_load - diesel_gen) > 0:  # If diesel generator cannot meet load the battery is also used
                        if battery_size > 0:
                            soc -= (net_load - diesel_gen) / n_dis / battery_size
                            battery_use[hour_numbers[i]] += (net_load - diesel_gen) / n_dis / battery_size
                            if soc < 0:  # If battery and diesel generator cannot supply load there is unmet demand
                                unmet_demand -= soc * n_dis * battery_size
                                battery_use[hour_numbers[i]] += soc
                                soc = 0
                    else:  # If diesel generation is larger than load the excess energy is stored in battery
                        if battery_size > 0:
                            soc += (diesel_gen - net_load) * n_chg / battery_size

                    if battery_size == 0:  # If no battery and diesel generation < net load there is unmet demand
                        unmet_demand += net_load - diesel_gen
                    soc = min(soc, 1)  # Battery state of charge cannot be >1

                    dod[hour_numbers[i]] = 1 - soc  # The depth of discharge in every hour of the day is storeed
                    if hour_numbers[i] == 23 and max(dod) > 0:  # The battery wear during the last day is calculated
                        battery_life += sum(battery_use) / (531.52764 * max(0.1, (max(dod) * dod_max)) ** -1.12297)

                condition = unmet_demand / energy_per_hh  # lpsp is calculated
                if initital_condition:  # During the first calculation the minimum PV size with no diesel generator is calculated
                    if condition > lpsp:
                        pv_capacity *= (1 + unmet_demand / energy_per_hh / 4)
                elif condition > lpsp or (annual_diesel_gen > (1 - ren_limit) * energy_per_hh):  # For the remaining configurations the solution is considered unusable if lpsp criteria is not met
                    diesel_capacity = 99
                    condition = 0
                    battery_life = 1
                elif condition < lpsp:  # If lpsp criteria is met the expected battery life is stored
                    battery_life = np.round(1 / battery_life)
            return pv_capacity, diesel_capacity, battery_size, fuel_result, battery_life

        # Initial PV size when no diesel generator is used is calculated and used as reference
        ref = pv_diesel_capacities(energy_per_hh / 3000, 2 * energy_per_hh / 365, 0, initital_condition=True)

        battery_sizes = [0.3 * energy_per_hh / 365, 0.5 * energy_per_hh / 365, 0.75 * energy_per_hh / 365, energy_per_hh / 365, 2 * energy_per_hh / 365, 0]  # [2 * energy_per_hh / 365, energy_per_hh / 365, 0]
        ref_battery_size = np.zeros((len(battery_sizes), pv_no, diesel_no))
        ref_panel_size = np.zeros((len(battery_sizes), pv_no, diesel_no))
        ref_diesel_cap = np.zeros((len(battery_sizes), pv_no, diesel_no))
        ref_fuel_result = np.zeros((len(battery_sizes), pv_no, diesel_no))
        ref_battery_life = np.zeros((len(battery_sizes), pv_no, diesel_no))

        # For the number of diesel, pv and battery capacities the lpsp, battery lifetime and fuel usage is calculated
        for k in range(len(battery_sizes)):
            for i in range(pv_no):
                for j in range(diesel_no):
                    a = pv_diesel_capacities(ref[0] * (pv_no - i) / pv_no, battery_sizes[k],
                                             j * max(load_curve) / diesel_no)
                    ref_panel_size[k, i, j] = a[0]
                    ref_diesel_cap[k, i, j] = a[1]
                    ref_battery_size[k, i, j] = a[2]
                    ref_fuel_result[k, i, j] = a[3]
                    ref_battery_life[k, i, j] = min(20, a[4])  # Battery life limited to maximum 20 years

        # Neccessary information for calculation of LCOE is defined
        project_life = self.end_year - self.start_year
        ghi_steps = int(
            ceil((max_ghi - 1000) / 50) + 1)  # GHI values rounded to nearest 50 are used for reference matrix
        diesel_cost_max = 2 * self.diesel_price * self.diesel_truck_consumption * max_travel_hours / self.diesel_truck_volume / LHV_DIESEL
        diesel_steps = int(
            ceil(diesel_cost_max * 100) + 1)  # Diesel values rounded to 0.01 USD used for reference matrix
        generation = np.ones(project_life) * energy_per_hh
        generation[0] = 0
        year = np.arange(project_life)
        discount_factor = (1 + self.discount_rate) ** year
        investment_table = np.zeros((ghi_steps, diesel_steps))  # Stores least-cost configuration investments
        pv_table = np.zeros((ghi_steps, diesel_steps))  # Stores PV size for least-cost configuraton
        diesel_table = np.zeros((ghi_steps, diesel_steps))  # Stores diesel capacity for least-cost configuration
        lcoe_table = np.ones((ghi_steps, diesel_steps)) * 99  # Stores LCOE for least-cost configuration
        choice_table = np.zeros((ghi_steps, diesel_steps))

        # For each combination of GHI and diesel price the least costly configuration is calculated by iterating through
        # the different configurations specified above
        for i in range(ghi_steps):
            pv_size = ref_panel_size * ghi.sum() / 1000 / (1000 + 50 * i)
            for j in range(diesel_steps):
                for k in range(pv_no):
                    for l in range(diesel_no):
                        for m in range(len(battery_sizes)):
                            investments = np.zeros(project_life)
                            salvage = np.zeros(project_life)
                            fuel_costs = np.ones(project_life) * ref_fuel_result[m, k, l] * (self.diesel_price + 0.01 * j)
                            investments[0] = pv_size[m, k, l] * pv_cost + ref_diesel_cap[m, k, l] * diesel_cost
                            salvage[-1] = ref_diesel_cap[m, k, l] * diesel_cost * (1 - project_life / diesel_life) + \
                                          pv_size[m, k, l] * pv_cost * (1 - project_life / pv_life)
                            om = np.ones(project_life) * (
                                pv_size[m, k, l] * pv_cost * pv_om + ref_diesel_cap[m, k, l] * diesel_cost * diesel_om)
                            if pv_life < project_life:
                                investments[pv_life] = pv_size[m, k, l] * pv_cost
                            if diesel_life < project_life:
                                investments[diesel_life] = ref_diesel_cap[m, k, l] * diesel_cost
                            for n in range(project_life):
                                if year[n] % ref_battery_life[m, k, l] == 0:
                                    investments[n] += ref_battery_size[m, k, l] * battery_cost / dod_max
                            salvage[-1] += (1 - (
                            (project_life % ref_battery_life[m, k, l]) / ref_battery_life[m, k, l])) * \
                                           battery_cost * ref_battery_size[m, k, l] / dod_max + ref_diesel_cap[
                                                                                                    m, k, l] * \
                                                                                                diesel_cost * (1 - (
                            project_life % diesel_life) / diesel_life) \
                                           + pv_size[m, k, l] * pv_cost * (1 - (project_life % pv_life) / pv_life)
                            discount_investments = (investments + fuel_costs - salvage + om) / discount_factor
                            discount_generation = generation / discount_factor
                            lcoe = np.sum(discount_investments) / np.sum(discount_generation)
                            if lcoe < lcoe_table[i, j]:
                                lcoe_table[i, j] = lcoe
                                pv_table[i, j] = pv_size[m, k, l]
                                diesel_table[i, j] = ref_diesel_cap[m, k, l]
                                investment_table[i, j] = np.sum(discount_investments)
                                choice_table[i, j] = (l + 1) * 10 + (k + 1) * 10000 + m + 1
                                # first number is PV size, second is diesel, third is battery
        return lcoe_table, pv_table, diesel_table, investment_table, load_curve[19], choice_table

    @classmethod
    def set_default_values(cls, start_year, end_year, discount_rate, grid_cell_area, mv_line_cost, lv_line_cost,
                           mv_line_capacity, lv_line_capacity, lv_line_max_length, hv_line_cost, mv_line_max_length,
                           hv_lv_transformer_cost, mv_increase_rate):
        cls.start_year = start_year
        cls.end_year = end_year
        cls.discount_rate = discount_rate
        cls.grid_cell_area = grid_cell_area
        cls.mv_line_cost = mv_line_cost
        cls.lv_line_cost = lv_line_cost
        cls.mv_line_capacity = mv_line_capacity
        cls.lv_line_capacity = lv_line_capacity
        cls.lv_line_max_length = lv_line_max_length
        cls.hv_line_cost = hv_line_cost
        cls.mv_line_max_length = mv_line_max_length
        cls.hv_lv_transformer_cost = hv_lv_transformer_cost
        cls.mv_increase_rate = mv_increase_rate

    def get_lcoe(self, energy_per_hh, people, num_people_per_hh, additional_mv_line_length=0, capacity_factor=0,
                 mv_line_length=0, travel_hours=0, ghi=0, urban=0, get_capacity=False, mini_grid=False, pv=False,
                 urban_hybrid=0, rural_hybrid=0, get_investment_cost=False, mg_pv=False, mg_wind=False,
                 mg_hydro=False, mg_diesel=False, mg_hybrid=False):
        """
        Calculates the LCOE depending on the parameters. Optionally calculates the investment cost instead.

        The only required parameters are energy_per_hh, people and num_people_per_hh
        additional_mv_line_length requried for grid
        capacity_factor required for PV and wind
        mv_line_length required for hydro
        travel_hours required for diesel
        """

        if people == 0:
            # If there are no people, the investment cost is zero.
            if get_investment_cost:
                return 0
            # Otherwise we set the people low (prevent div/0 error) and continue.
            else:
                people = 0.00001

        # If a new capacity factor isn't given, use the class capacity factor (for hydro, diesel etc)
        if capacity_factor == 0:
            capacity_factor = self.capacity_factor

        consumption = people / num_people_per_hh * energy_per_hh  # kWh/year
        average_load = consumption / (1 - self.distribution_losses) / HOURS_PER_YEAR  # kW

        if mg_hybrid and urban == 1:
            peak_load = urban_hybrid[4] * consumption
            # peak_load = people / num_people_per_hh * urban_hybrid[4] * (1 + self.distribution_losses)
        elif mg_hybrid and urban == 0:
            peak_load = rural_hybrid[4] * consumption
            # peak_load = people / num_people_per_hh * rural_hybrid[4] * (1 + self.distribution_losses)
        else:
            peak_load = average_load / self.base_to_peak_load_ratio  # kW

        no_mv_lines = peak_load / self.mv_line_capacity
        no_lv_lines = peak_load / self.lv_line_capacity
        lv_networks_lim_capacity = no_lv_lines / no_mv_lines
        lv_networks_lim_length = ((self.grid_cell_area / no_mv_lines) / (self.lv_line_max_length / sqrt(2))) ** 2
        actual_lv_lines = min([people / num_people_per_hh, max([lv_networks_lim_capacity, lv_networks_lim_length])])
        hh_per_lv_network = (people / num_people_per_hh) / (actual_lv_lines * no_mv_lines)
        lv_unit_length = sqrt(self.grid_cell_area / (people / num_people_per_hh)) * sqrt(2) / 2
        lv_lines_length_per_lv_network = 1.333 * hh_per_lv_network * lv_unit_length
        total_lv_lines_length = no_mv_lines * actual_lv_lines * lv_lines_length_per_lv_network
        line_reach = (self.grid_cell_area / no_mv_lines) / (2 * sqrt(self.grid_cell_area / no_lv_lines))
        total_length_of_lines = min([line_reach, self.mv_line_max_length]) * no_mv_lines
        additional_hv_lines = max(
            [0, round(sqrt(self.grid_cell_area) / (2 * min([line_reach, self.mv_line_max_length])) / 10, 3) - 1])
        hv_lines_total_length = (sqrt(self.grid_cell_area) / 2) * additional_hv_lines * sqrt(self.grid_cell_area)
        num_transformers = additional_hv_lines + no_mv_lines + (no_mv_lines * actual_lv_lines)
        generation_per_year = average_load * HOURS_PER_YEAR

        # The investment and O&M costs are different for grid and non-grid solutions
        if self.grid_price > 0 :
            td_investment_cost = hv_lines_total_length * self.hv_line_cost + \
                                 total_length_of_lines * self.mv_line_cost + \
                                 total_lv_lines_length * self.lv_line_cost + \
                                 num_transformers * self.hv_lv_transformer_cost + \
                                 (people / num_people_per_hh) * self.connection_cost_per_hh + \
                                 additional_mv_line_length * (
                                     self.mv_line_cost * (1 + self.mv_increase_rate) **
                                     ((additional_mv_line_length / 5) - 1))
            td_om_cost = td_investment_cost * self.om_of_td_lines
            total_investment_cost = td_investment_cost
            total_om_cost = td_om_cost
            fuel_cost = self.grid_price

        else:
            total_lv_lines_length *= 0 if self.standalone else 0.75
            mv_total_line_cost = self.mv_line_cost * mv_line_length
            lv_total_line_cost = self.lv_line_cost * total_lv_lines_length
            td_investment_cost = mv_total_line_cost + lv_total_line_cost + (
                    people / num_people_per_hh) * self.connection_cost_per_hh
            td_om_cost = td_investment_cost * self.om_of_td_lines
            installed_capacity = peak_load / capacity_factor

            if self.standalone:
                if self.diesel_price > 0:
                        if (installed_capacity / people / num_people_per_hh) < 1:
                            installed_capacity = 1 * people / num_people_per_hh
                if installed_capacity / (people / num_people_per_hh) < 0.020:
                    capital_investment = installed_capacity * self.capital_cost[0.020]
                    total_investment_cost = td_investment_cost + capital_investment
                    total_om_cost = td_om_cost + (self.capital_cost[0.020] * self.om_costs * installed_capacity)
                elif installed_capacity / (people / num_people_per_hh) < 0.050:
                    capital_investment = installed_capacity * self.capital_cost[0.050]
                    total_investment_cost = td_investment_cost + capital_investment
                    total_om_cost = td_om_cost + (self.capital_cost[0.050] * self.om_costs * installed_capacity)
                elif installed_capacity / (people / num_people_per_hh) < 0.100:
                    capital_investment = installed_capacity * self.capital_cost[0.100]
                    total_investment_cost = td_investment_cost + capital_investment
                    total_om_cost = td_om_cost + (self.capital_cost[0.100] * self.om_costs * installed_capacity)
                elif installed_capacity / (people / num_people_per_hh) < 0.200:
                    capital_investment = installed_capacity * self.capital_cost[0.200]
                    total_investment_cost = td_investment_cost + capital_investment
                    total_om_cost = td_om_cost + (self.capital_cost[0.200] * self.om_costs * installed_capacity)
                else:
                    capital_investment = installed_capacity * self.capital_cost[0.300]
                    total_investment_cost = td_investment_cost + capital_investment
                    total_om_cost = td_om_cost + (self.capital_cost[0.300] * self.om_costs * installed_capacity)
            elif self.mg_pv:
                if installed_capacity < 50:
                    capital_investment = installed_capacity * self.capital_cost[50]
                    total_investment_cost = td_investment_cost + capital_investment
                    total_om_cost = td_om_cost + (self.capital_cost[50] * self.om_costs * installed_capacity)
                elif installed_capacity < 75:
                    capital_investment = installed_capacity * self.capital_cost[75]
                    total_investment_cost = td_investment_cost + capital_investment
                    total_om_cost = td_om_cost + (self.capital_cost[75] * self.om_costs * installed_capacity)
                elif installed_capacity < 100:
                    capital_investment = installed_capacity * self.capital_cost[100]
                    total_investment_cost = td_investment_cost + capital_investment
                    total_om_cost = td_om_cost + (self.capital_cost[100] * self.om_costs * installed_capacity)
                else:
                    capital_investment = installed_capacity * self.capital_cost[200]
                    total_investment_cost = td_investment_cost + capital_investment
                    total_om_cost = td_om_cost + (self.capital_cost[200] * self.om_costs * installed_capacity)
            elif self.mg_wind:
                if installed_capacity < 100:
                    capital_investment = installed_capacity * self.capital_cost[100]
                    total_investment_cost = td_investment_cost + capital_investment
                    total_om_cost = td_om_cost + (self.capital_cost[100] * self.om_costs * installed_capacity)
                elif installed_capacity < 1000:
                    capital_investment = installed_capacity * self.capital_cost[1000]
                    total_investment_cost = td_investment_cost + capital_investment
                    total_om_cost = td_om_cost + (self.capital_cost[1000] * self.om_costs * installed_capacity)
                else:
                    capital_investment = installed_capacity * self.capital_cost[10000]
                    total_investment_cost = td_investment_cost + capital_investment
                    total_om_cost = td_om_cost + (self.capital_cost[10000] * self.om_costs * installed_capacity)
            elif self.mg_hydro:
                if installed_capacity < 1:
                    capital_investment = installed_capacity * self.capital_cost[1]
                    total_investment_cost = td_investment_cost + capital_investment
                    total_om_cost = td_om_cost + (self.capital_cost[1] * self.om_costs * installed_capacity)
                elif installed_capacity < 100:
                    capital_investment = installed_capacity * self.capital_cost[100]
                    total_investment_cost = td_investment_cost + capital_investment
                    total_om_cost = td_om_cost + (self.capital_cost[100] * self.om_costs * installed_capacity)
                else:
                    capital_investment = installed_capacity * self.capital_cost[5000]
                    total_investment_cost = td_investment_cost + capital_investment
                    total_om_cost = td_om_cost + (self.capital_cost[5000] * self.om_costs * installed_capacity)
            elif self.mg_diesel:
                if installed_capacity < 100:
                    capital_investment = installed_capacity * self.capital_cost[100]
                    total_investment_cost = td_investment_cost + capital_investment
                    total_om_cost = td_om_cost + (self.capital_cost[100] * self.om_costs * installed_capacity)
                elif installed_capacity < 1000:
                    capital_investment = installed_capacity * self.capital_cost[1000]
                    total_investment_cost = td_investment_cost + capital_investment
                    total_om_cost = td_om_cost + (self.capital_cost[1000] * self.om_costs * installed_capacity)
                elif installed_capacity < 5000:
                    capital_investment = installed_capacity * self.capital_cost[5000]
                    total_investment_cost = td_investment_cost + capital_investment
                    total_om_cost = td_om_cost + (self.capital_cost[5000] * self.om_costs * installed_capacity)
                else:
                    capital_investment = installed_capacity * self.capital_cost[25000]
                    total_investment_cost = td_investment_cost + capital_investment
                    total_om_cost = td_om_cost + (self.capital_cost[25000] * self.om_costs * installed_capacity)
            elif mg_hybrid:
                capital_investment = installed_capacity * self.capital_cost
                total_investment_cost = td_investment_cost + capital_investment
                total_om_cost = td_om_cost + (self.capital_cost * self.om_costs * installed_capacity)

            # If a diesel price has been passed, the technology is diesel
            if self.diesel_price > 0 and not mg_hybrid:
                # And we apply the Szabo formula to calculate the transport cost for the diesel
                # p = (p_d + 2*p_d*consumption*time/volume)*(1/mu)*(1/LHVd)
                fuel_cost = (self.diesel_price + 2 * self.diesel_price * self.diesel_truck_consumption * travel_hours /
                             self.diesel_truck_volume) / LHV_DIESEL / self.efficiency
            # Otherwise it's hydro/wind etc with no fuel cost
            else:
                fuel_cost = 0

        # Perform the time-value LCOE calculation
        project_life = self.end_year - self.start_year
        reinvest_year = 0

        # If the technology life is less than the project life, we will have to invest twice to buy it again
        if self.tech_life < project_life:
            reinvest_year = self.tech_life

        year = np.arange(project_life)
        el_gen = generation_per_year * np.ones(project_life)
        el_gen[0] = 0
        discount_factor = (1 + self.discount_rate) ** year
        investments = np.zeros(project_life)
        investments[0] = total_investment_cost
        if reinvest_year:
            investments[reinvest_year] = total_investment_cost

        salvage = np.zeros(project_life)
        used_life = project_life
        if reinvest_year:
            # so salvage will come from the remaining life after the re-investment
            used_life = project_life - self.tech_life
        salvage[-1] = total_investment_cost * (1 - used_life / self.tech_life)

        operation_and_maintenance = total_om_cost * np.ones(project_life)
        operation_and_maintenance[0] = 0
        fuel = el_gen * fuel_cost
        fuel[0] = 0

        if mg_hybrid:
            diesel_lookup = int(round(2 * self.diesel_price * self.diesel_truck_consumption *
                                      travel_hours / self.diesel_truck_volume / LHV_DIESEL * 100))
            renewable_lookup = int(round((ghi - 1000) / 50))

            if urban == 1 and pv:
                ref_table = urban_hybrid[0]
                ref_investments = urban_hybrid[3]
                ref_capacity = urban_hybrid[1] + urban_hybrid[2]
            elif urban == 0 and pv:
                ref_table = rural_hybrid[0]
                ref_investments = rural_hybrid[3]
                ref_capacity = rural_hybrid[1] + rural_hybrid[2]

            add_lcoe = ref_table[renewable_lookup, diesel_lookup]
            add_investments = ref_investments[renewable_lookup, diesel_lookup] * people / num_people_per_hh
            add_capacity = ref_capacity[renewable_lookup, diesel_lookup] * people / num_people_per_hh

        # So we also return the total investment cost for this number of people
        if get_investment_cost:
            discounted_investments = investments / discount_factor
            if mini_grid:
                return add_investments + np.sum(discounted_investments)
            else:
                return np.sum(discounted_investments) + self.grid_capacity_investment * peak_load
            # return np.sum(discounted_investments) + self.grid_capacity_investment * peak_load
        elif get_capacity:
            return add_capacity
        else:
            discounted_costs = (investments + operation_and_maintenance + fuel - salvage) / discount_factor
            discounted_generation = el_gen / discount_factor
            if mini_grid:
                return np.sum(discounted_costs) / np.sum(discounted_generation) + add_lcoe
            else:
                return np.sum(discounted_costs) / np.sum(discounted_generation)
            # return np.sum(discounted_costs) / np.sum(discounted_generation)

    def get_grid_table(self, energy_per_hh, num_people_per_hh, max_dist):
        """
        Uses calc_lcoe to generate a 2D grid with the grid LCOEs, for faster access in teh electrification algorithm
        """

        logging.info('Creating a grid table for {} kWh/hh/year'.format(energy_per_hh))

        # Coarser resolution at the high end (just to catch the few places with exceptional population density)
        # The electrification algorithm must round off with the same scheme
        people_arr_direct = list(range(1000)) + list(range(1000, 10000, 10)) + list(range(10000, 350000, 1000))
        elec_dists = range(0, int(max_dist) + 20)  # add twenty to handle edge cases
        grid_lcoes = pd.DataFrame(index=elec_dists, columns=people_arr_direct)

        for people in people_arr_direct:
            for additional_mv_line_length in elec_dists:
                grid_lcoes[people][additional_mv_line_length] = self.get_lcoe(
                    energy_per_hh=energy_per_hh,
                    people=people,
                    num_people_per_hh=num_people_per_hh,
                    additional_mv_line_length=additional_mv_line_length)

        return grid_lcoes.to_dict()


class SettlementProcessor:
    """
    Processes the dataframe and adds all the columns to determine the cheapest option and the final costs and summaries
    """
    def __init__(self, path):
        try:
            self.df = pd.read_csv(path)
        except FileNotFoundError:
            print('Could not find the calibrated and prepped csv file')
            raise

        try:
            self.df[SET_GHI]
        except ValueError:
            self.df = pd.read_csv(path, sep=';')
            try:
                self.df[SET_GHI]
            except ValueError:
                print('Column "GHI" not found, check column names in calibrated csv-file')
                raise

    def condition_df(self):
        """
        Do any initial data conditioning that may be required.
        """

        logging.info('Ensure that columns that are supposed to be numeric are numeric')
        self.df[SET_GHI] = pd.to_numeric(self.df[SET_GHI], errors='coerce')
        self.df[SET_WINDVEL] = pd.to_numeric(self.df[SET_WINDVEL], errors='coerce')
        self.df[SET_NIGHT_LIGHTS] = pd.to_numeric(self.df[SET_NIGHT_LIGHTS], errors='coerce')
        self.df[SET_ELEVATION] = pd.to_numeric(self.df[SET_ELEVATION], errors='coerce')
        self.df[SET_SLOPE] = pd.to_numeric(self.df[SET_SLOPE], errors='coerce')
        self.df[SET_LAND_COVER] = pd.to_numeric(self.df[SET_LAND_COVER], errors='coerce')
        self.df[SET_GRID_DIST_CURRENT] = pd.to_numeric(self.df[SET_GRID_DIST_CURRENT], errors='coerce')
        self.df[SET_GRID_DIST_PLANNED] = pd.to_numeric(self.df[SET_GRID_DIST_PLANNED], errors='coerce')
        self.df[SET_SUBSTATION_DIST] = pd.to_numeric(self.df[SET_SUBSTATION_DIST], errors='coerce')
        self.df[SET_ROAD_DIST] = pd.to_numeric(self.df[SET_ROAD_DIST], errors='coerce')
        self.df[SET_HYDRO_DIST] = pd.to_numeric(self.df[SET_HYDRO_DIST], errors='coerce')
        self.df[SET_HYDRO] = pd.to_numeric(self.df[SET_HYDRO], errors='coerce')
        self.df[SET_SOLAR_RESTRICTION] = pd.to_numeric(self.df[SET_SOLAR_RESTRICTION], errors='coerce')

        logging.info('Replace null values with zero')
        self.df.fillna(0, inplace=True)

        logging.info('Sort by country, Y and X')
        self.df.sort_values(by=[SET_COUNTRY, SET_Y, SET_X], inplace=True)


    def grid_penalties(self):
        """
        Add a grid penalty factor to increase the grid cost in areas that higher road distance, higher substation
        distance, unsuitable land cover, high slope angle or high elecation
        """

        def classify_road_dist(row):
            road_dist = row[SET_ROAD_DIST]
            if road_dist <= 5:
                return 5
            elif road_dist <= 10:
                return 4
            elif road_dist <= 25:
                return 3
            elif road_dist <= 50:
                return 2
            else:
                return 1

        def classify_substation_dist(row):
            substation_dist = row[SET_SUBSTATION_DIST]
            if substation_dist <= 0.5:
                return 5
            elif substation_dist <= 1:
                return 4
            elif substation_dist <= 5:
                return 3
            elif substation_dist <= 10:
                return 2
            else:
                return 1

        def classify_land_cover(row):
            land_cover = row[SET_LAND_COVER]
            if land_cover == 0:
                return 1
            elif land_cover == 1:
                return 3
            elif land_cover == 2:
                return 4
            elif land_cover == 3:
                return 3
            elif land_cover == 4:
                return 4
            elif land_cover == 5:
                return 3
            elif land_cover == 6:
                return 2
            elif land_cover == 7:
                return 5
            elif land_cover == 8:
                return 2
            elif land_cover == 9:
                return 5
            elif land_cover == 10:
                return 5
            elif land_cover == 11:
                return 1
            elif land_cover == 12:
                return 3
            elif land_cover == 13:
                return 3
            elif land_cover == 14:
                return 5
            elif land_cover == 15:
                return 3
            elif land_cover == 16:
                return 5

        def classify_elevation(row):
            elevation = row[SET_ELEVATION]
            if elevation <= 500:
                return 5
            elif elevation <= 1000:
                return 4
            elif elevation <= 2000:
                return 3
            elif elevation <= 3000:
                return 2
            else:
                return 1

        def classify_slope(row):
            slope = row[SET_SLOPE]
            if slope <= 10:
                return 5
            elif slope <= 20:
                return 4
            elif slope <= 30:
                return 3
            elif slope <= 40:
                return 2
            else:
                return 1

        def set_penalty(row):
            classification = row[SET_COMBINED_CLASSIFICATION]
            return 1 + (exp(0.85 * abs(1 - classification)) - 1) / 100

        logging.info('Classify road dist')
        self.df[SET_ROAD_DIST_CLASSIFIED] = self.df.apply(classify_road_dist, axis=1)

        logging.info('Classify substation dist')
        self.df[SET_SUBSTATION_DIST_CLASSIFIED] = self.df.apply(classify_substation_dist, axis=1)

        logging.info('Classify land cover')
        self.df[SET_LAND_COVER_CLASSIFIED] = self.df.apply(classify_land_cover, axis=1)

        logging.info('Classify elevation')
        self.df[SET_ELEVATION_CLASSIFIED] = self.df.apply(classify_elevation, axis=1)

        logging.info('Classify slope')
        self.df[SET_SLOPE_CLASSIFIED] = self.df.apply(classify_slope, axis=1)

        logging.info('Combined classification')
        self.df[SET_COMBINED_CLASSIFICATION] = (0.05 * self.df[SET_ROAD_DIST_CLASSIFIED] +
                                                0.09 * self.df[SET_SUBSTATION_DIST_CLASSIFIED] +
                                                0.39 * self.df[SET_LAND_COVER_CLASSIFIED] +
                                                0.15 * self.df[SET_ELEVATION_CLASSIFIED] +
                                                0.32 * self.df[SET_SLOPE_CLASSIFIED])

        logging.info('Grid penalty')
        self.df[SET_GRID_PENALTY] = self.df.apply(set_penalty, axis=1)

    def calc_wind_cfs(self):
        """
        Calculate the wind capacity factor based on the average wind velocity.
        """

        mu = 0.97  # availability factor
        t = 8760
        p_rated = 600
        z = 55  # hub height
        zr = 80  # velocity measurement height
        es = 0.85  # losses in wind electricity
        u_arr = range(1, 26)
        p_curve = [0, 0, 0, 0, 30, 77, 135, 208, 287, 371, 450, 514, 558,
                   582, 594, 598, 600, 600, 600, 600, 600, 600, 600, 600, 600]

        def get_wind_cf(row):
            u_zr = row[SET_WINDVEL]
            if u_zr == 0:
                return 0

            else:
                # Adjust for the correct hub height
                alpha = (0.37 - 0.088 * log(u_zr)) / (1 - 0.088 * log(zr / 10))
                u_z = u_zr * (z / zr) ** alpha

                # Rayleigh distribution and sum of series
                rayleigh = [(pi / 2) * (u / u_z ** 2) * exp((-pi / 4) * (u / u_z) ** 2) for u in u_arr]
                energy_produced = sum([mu * es * t * p * r for p, r in zip(p_curve, rayleigh)])

                return energy_produced/(p_rated * t)

        logging.info('Calculate Wind CF')
        self.df[SET_WINDCF] = self.df.apply(get_wind_cf, axis=1)

    def calibrate_pop_and_urban(self, pop_actual, pop_future, urban, urban_future, urban_cutoff):
        """
        Calibrate the actual current population, the urban split and forecast the future population
        """

        # Calculate the ratio between the actual population and the total population from the GIS layer
        logging.info('Calibrate current population')
        pop_ratio = pop_actual/self.df[SET_POP].sum()

        # And use this ratio to calibrate the population in a new column
        self.df[SET_POP_CALIB] = self.df.apply(lambda row: row[SET_POP] * pop_ratio, axis=1)

        # Calculate the urban split, by calibrating the cutoff until the target ratio is achieved
        # Keep looping until it is satisfied or another break conditions is reached
        logging.info('Calibrate urban split')
        sorted_pop = self.df[SET_POP_CALIB].copy()
        sorted_pop.sort_values(inplace=True)
        urban_pop_break = (1-urban) * self.df[SET_POP_CALIB].sum()
        cumulative_urban_pop = 0
        ii = 0
        while cumulative_urban_pop < urban_pop_break:
            cumulative_urban_pop += sorted_pop.iloc[ii]
            ii += 1
        urban_cutoff = sorted_pop.iloc[ii-1]

        # Assign the 1 (urban)/0 (rural) values to each cell
        self.df[SET_URBAN] = self.df.apply(lambda row: 1 if row[SET_POP_CALIB] > urban_cutoff else 0, axis=1)

        # Get the calculated urban ratio, and limit it to within reasonable boundaries
        pop_urb = self.df.loc[self.df[SET_URBAN] == 1, SET_POP_CALIB].sum()
        urban_modelled = pop_urb / pop_actual

        # Project future population, with separate growth rates for urban and rural
        logging.info('Project future population')

        urban_growth = (urban_future * pop_future) / (urban * pop_actual)
        rural_growth = ((1 - urban_future) * pop_future) / ((1 - urban) * pop_actual)

        self.df[SET_POP_FUTURE] = self.df.apply(lambda row: row[SET_POP_CALIB] * urban_growth
                                                if row[SET_URBAN] == 1
                                                else row[SET_POP_CALIB] * rural_growth,
                                                axis=1)

        return urban_cutoff, urban_modelled

    def elec_current_and_future(self, elec_actual, pop_cutoff, min_night_lights, max_grid_dist,
                                max_road_dist, pop_tot, pop_cutoff2):
        """
        Calibrate the current electrification status, and future 'pre-electrification' status
        """

        urban_pop = (self.df.loc[self.df[SET_URBAN] == 1, SET_POP_CALIB].sum())  # Calibrate current electrification
        rural_pop = (self.df.loc[self.df[SET_URBAN] == 0, SET_POP_CALIB].sum())  # Calibrate current electrification
        total_pop = self.df[SET_POP_CALIB].sum()
        total_elec_ratio = elec_actual
        urban_elec_ratio = 0.708
        rural_elec_ratio = 0.180
        factor = (total_pop * total_elec_ratio) / (urban_pop * urban_elec_ratio + rural_pop * rural_elec_ratio)
        urban_elec_ratio *= factor
        rural_elec_ratio *= factor
        print('factor: ' + str(factor))
        self.df[SET_ELEC_CURRENT] = 0

        # Calibrate current electrification
        logging.info('Calibrate current electrification')
        print('1. Actual electrification rate in 2015 = {}'.format(elec_actual))
        is_round_two = False
        grid_cutoff2 = 10
        road_cutoff2 = 10
        count = 0
        prev_vals = []
        accuracy = 0.005
        max_iterations_one = 30
        max_iterations_two = 60

        urban_electrified = urban_pop * urban_elec_ratio
        rural_electrified = rural_pop * rural_elec_ratio
        self.df.loc[(self.df[SET_GRID_DIST_CURRENT] < 50) & (self.df[SET_NIGHT_LIGHTS] > 0) & (
                self.df[SET_POP_CALIB] > 100), SET_ELEC_CURRENT] = 1
        urban_elec_ratio = urban_electrified / (self.df.loc[(self.df[SET_ELEC_CURRENT] == 1) & (
                self.df[SET_URBAN] == 1), SET_POP_CALIB].sum())
        rural_elec_ratio = rural_electrified /(self.df.loc[(self.df[SET_ELEC_CURRENT] == 1) & (
                self.df[SET_URBAN] == 0), SET_POP_CALIB].sum())
        pop_elec = self.df.loc[self.df[SET_ELEC_CURRENT] == 1, SET_POP_CALIB].sum()
        elec_modelled = pop_elec / pop_tot

        print('Urban elec ratio: ' + str(urban_elec_ratio))
        print('Rural elec ratio: ' + str(rural_elec_ratio))

        logging.info('The modelled electrification rate achieved is {}. '
                     'If this is not acceptable please revise this part of the algorithm'.format(elec_modelled))

        logging.info('Calculate new connections')
        self.df.loc[(self.df[SET_ELEC_CURRENT] == 1) & (self.df[SET_URBAN] == 1), SET_NEW_CONNECTIONS] =\
            self.df[SET_POP_FUTURE] - urban_elec_ratio * self.df[SET_POP_CALIB]
        self.df.loc[(self.df[SET_ELEC_CURRENT] == 1) & (self.df[SET_URBAN] == 0), SET_NEW_CONNECTIONS] = \
            self.df[SET_POP_FUTURE] - rural_elec_ratio * self.df[SET_POP_CALIB]
        self.df.loc[self.df[SET_ELEC_CURRENT] == 0, SET_NEW_CONNECTIONS] = self.df[SET_POP_FUTURE]
        self.df.loc[self.df[SET_NEW_CONNECTIONS] < 0, SET_NEW_CONNECTIONS] = 0

        return min_night_lights, max_grid_dist, max_road_dist, elec_modelled, pop_cutoff, pop_cutoff2, urban_elec_ratio, rural_elec_ratio

    @staticmethod
    def separate_elec_status(elec_status):
        """
        Separate out the electrified and unelectrified states from list.
        """

        electrified = []
        unelectrified = []

        for i, status in enumerate(elec_status):
            if status:
                electrified.append(i)
            else:
                unelectrified.append(i)
        return electrified, unelectrified

    @staticmethod
    def get_2d_hash_table(x, y, unelectrified, distance_limit):
        """
        Generates the 2D Hash Table with the unelectrified locations hashed into the table for easy O(1) access.
        """

        hash_table = defaultdict(lambda: defaultdict(list))
        for unelec_row in unelectrified:
            hash_x = int(x[unelec_row] / distance_limit)
            hash_y = int(y[unelec_row] / distance_limit)
            hash_table[hash_x][hash_y].append(unelec_row)
        return hash_table

    @staticmethod
    def get_unelectrified_rows(hash_table, elec_row, x, y, distance_limit):
        """
        Returns all the unelectrified locations close to the electrified location
        based on the distance boundary limit specified by asking the 2D hash table.
        """

        unelec_list = []
        hash_x = int(x[elec_row] / distance_limit)
        hash_y = int(y[elec_row] / distance_limit)

        unelec_list.extend(hash_table.get(hash_x, {}).get(hash_y, []))
        unelec_list.extend(hash_table.get(hash_x, {}).get(hash_y - 1, []))
        unelec_list.extend(hash_table.get(hash_x, {}).get(hash_y + 1, []))

        unelec_list.extend(hash_table.get(hash_x + 1, {}).get(hash_y, []))
        unelec_list.extend(hash_table.get(hash_x + 1, {}).get(hash_y - 1, []))
        unelec_list.extend(hash_table.get(hash_x + 1, {}).get(hash_y + 1, []))

        unelec_list.extend(hash_table.get(hash_x - 1, {}).get(hash_y, []))
        unelec_list.extend(hash_table.get(hash_x - 1, {}).get(hash_y - 1, []))
        unelec_list.extend(hash_table.get(hash_x - 1, {}).get(hash_y + 1, []))

        return unelec_list

    def pre_elec(self, grid_lcoes_rural, grid_lcoes_urban, grid_lcoes_peri_urban, pre_elec_dist, grid_calc, grid_capacity_limit):
        """
        Determine which settlements are economically close to existing or planned grid lines, and should be
        considered electrified in the electrification algorithm
        """
        new_grid_capacity = 0
        grid_capacity_limit = 99999999  # kW during model period

        df_neargrid = self.df.loc[self.df[SET_GRID_DIST_PLANNED] < pre_elec_dist]

        pop = df_neargrid[SET_NEW_CONNECTIONS_PROD].tolist()
        # pop = df_neargrid[SET_POP_FUTURE].tolist()
        urban = df_neargrid[SET_URBAN].tolist()
        grid_penalty_ratio = df_neargrid[SET_GRID_PENALTY].tolist()
        status = df_neargrid[SET_ELEC_CURRENT].tolist()
        min_tech_lcoes = df_neargrid[SET_MIN_OFFGRID_LCOE].tolist()
        dist_planned = df_neargrid[SET_GRID_DIST_PLANNED].tolist()
        demand = df_neargrid[SET_ENERGY_PER_HH].tolist()
        new_conn = df_neargrid[SET_NEW_CONNECTIONS_PROD].tolist()
        num_ppphh = df_neargrid[SET_NUM_PEOPLE_PER_HH].tolist()

        electrified, unelectrified = self.separate_elec_status(status)

        for elec in electrified:
            consumption = new_conn[elec] / num_ppphh[elec] * demand[elec]  # kWh/year
            average_load = consumption / (1 - grid_calc.distribution_losses) / HOURS_PER_YEAR  # kW
            peak_load = average_load / grid_calc.base_to_peak_load_ratio  # kW
            new_grid_capacity += peak_load

        for unelec in unelectrified:
            consumption = pop[unelec] / num_ppphh[unelec] * demand[unelec]  # kWh/year
            average_load = consumption / (1 - grid_calc.distribution_losses) / HOURS_PER_YEAR  # kW
            peak_load = average_load / grid_calc.base_to_peak_load_ratio  # kW
            pop_index = pop[unelec]
            if pop_index < 1000:
                pop_index = int(pop_index)
            elif pop_index < 10000:
                pop_index = 10 * round(pop_index / 10)
            else:
                pop_index = 1000 * round(pop_index / 1000)

            if urban[unelec]:
                grid_lcoe = grid_lcoes_urban[pop_index][int(grid_penalty_ratio[unelec] * dist_planned[unelec])]
            elif pop[unelec] > 300:
                grid_lcoe = grid_lcoes_peri_urban[pop_index][int(grid_penalty_ratio[unelec] * dist_planned[unelec])]
            else:
                grid_lcoe = grid_lcoes_rural[pop_index][int(grid_penalty_ratio[unelec] * dist_planned[unelec])]

            if grid_lcoe < min_tech_lcoes[unelec]:
                if new_grid_capacity < grid_capacity_limit:
                    new_grid_capacity += peak_load
                    status[unelec] = 1
                else:
                    pass

        return status

    def elec_extension(self, grid_lcoes_rural, grid_lcoes_urban, grid_lcoes_peri_urban, existing_grid_cost_ratio, max_dist, coordinate_units, grid_calc, grid_capacity_limit):
        """
        Iterate through all electrified settlements and find which settlements can be economically connected to the grid
        Repeat with newly electrified settlements until no more are added
        """
        new_grid_capacity = 0
        grid_capacity_limit = 99999999  # kW during model period
        x = (self.df[SET_X]/coordinate_units).tolist()
        y = (self.df[SET_Y]/coordinate_units).tolist()
        pop = self.df[SET_NEW_CONNECTIONS_PROD].tolist()
        # pop = self.df[SET_POP_FUTURE].tolist()
        old_pop = self.df[SET_POP_CALIB].tolist()
        urban = self.df[SET_URBAN].tolist()
        grid_penalty_ratio = self.df[SET_GRID_PENALTY].tolist()
        status = self.df[SET_ELEC_FUTURE].tolist()
        min_tech_lcoes = self.df[SET_MIN_OFFGRID_LCOE].tolist()
        new_lcoes = self.df[SET_LCOE_GRID].tolist()
        num_ppphh = self.df[SET_NUM_PEOPLE_PER_HH].tolist()
        demand = self.df[SET_ENERGY_PER_HH].tolist()
        new_conn = self.df[SET_NEW_CONNECTIONS_PROD].tolist()
        #new_conn = self.df[SET_NEW_CONNECTIONS].tolist()

        cell_path_real = list(np.zeros(len(status)).tolist())
        cell_path_adjusted = list(np.zeros(len(status)).tolist())
        electrified, unelectrified = self.separate_elec_status(status)

        logging.info('Initially {} cells electrified'.format(len(electrified)))

        for elec in electrified:
            consumption = (new_conn[elec]) / num_ppphh[elec] * demand[elec]  # kWh/year
            average_load = consumption / (1 - grid_calc.distribution_losses) / HOURS_PER_YEAR  # kW
            peak_load = average_load / grid_calc.base_to_peak_load_ratio  # kW
            new_grid_capacity += peak_load

        close = []
        elec_nodes2 = []
        changes = []
        for elec in electrified:
            elec_nodes2.append((x[elec], y[elec]))
        elec_nodes2 = np.asarray(elec_nodes2)

        def closest_elec(unelec_node, elec_nodes):
            deltas = elec_nodes - unelec_node
            dist_2 = np.einsum('ij,ij->i', deltas, deltas)
            return np.argmin(dist_2)

        for unelec in unelectrified:
            consumption = pop[unelec]/num_ppphh[unelec]*demand[unelec]  # kWh/year
            average_load = consumption / (1 - grid_calc.distribution_losses) / HOURS_PER_YEAR  # kW
            peak_load = average_load / grid_calc.base_to_peak_load_ratio  # kW

            pop_index = pop[unelec]
            if pop_index < 1000:
                pop_index = int(pop_index)
            elif pop_index < 10000:
                pop_index = 10 * round(pop_index / 10)
            else:
                pop_index = 1000 * round(pop_index / 1000)

            if urban[unelec]:
                grid_lcoe = grid_lcoes_urban[pop_index][1]
            elif pop[unelec] > 300:
                grid_lcoe = grid_lcoes_peri_urban[pop_index][1]
            else:
                grid_lcoe = grid_lcoes_rural[pop_index][1]
            if grid_lcoe <= min_tech_lcoes[unelec]:
                node = (x[unelec], y[unelec])
                closest_elec_node = closest_elec(node, elec_nodes2)
                dist = sqrt((x[electrified[closest_elec_node]] - x[unelec]) ** 2
                            + (y[electrified[closest_elec_node]] - y[unelec]) ** 2)
                if dist <= max_dist:
                    dist_adjusted = grid_penalty_ratio[unelec] * dist
                    if dist_adjusted < max_dist:
                        if urban[unelec]:
                            grid_lcoe = grid_lcoes_urban[pop_index][int(dist_adjusted)]
                        else:
                            grid_lcoe = grid_lcoes_rural[pop_index][int(dist_adjusted)]

                        if grid_lcoe < min_tech_lcoes[unelec]:
                            if grid_lcoe < new_lcoes[unelec] and (new_grid_capacity + peak_load < grid_capacity_limit):
                                new_lcoes[unelec] = grid_lcoe
                                cell_path_real[unelec] = dist
                                cell_path_adjusted[unelec] = dist_adjusted
                                new_grid_capacity += peak_load
                                if unelec not in changes:
                                    changes.append(unelec)
                            else:
                                close.append(unelec)
                        else:
                            close.append(unelec)
                    else:
                        close.append(unelec)
        electrified = changes[:]
        unelectrified = close

        loops = 1
        while len(electrified) > 0 and new_grid_capacity < grid_capacity_limit:
            logging.info('Electrification loop {} with {} electrified'.format(loops, len(electrified)))
            loops += 1
            hash_table = self.get_2d_hash_table(x, y, unelectrified, max_dist)

            changes = []
            for elec in electrified:
                unelectrified_hashed = self.get_unelectrified_rows(hash_table, elec, x, y, max_dist)
                for unelec in unelectrified_hashed:
                    consumption = pop[unelec] / num_ppphh[unelec] * demand[unelec]  # kWh/year
                    average_load = consumption / (1 - grid_calc.distribution_losses) / HOURS_PER_YEAR  # kW
                    peak_load = average_load / grid_calc.base_to_peak_load_ratio  # kW
                    prev_dist = cell_path_real[elec]
                    dist = sqrt((x[elec] - x[unelec]) ** 2 + (y[elec] - y[unelec]) ** 2)
                    if prev_dist + dist < max_dist:
                        pop_index = pop[unelec]
                        if pop_index < 1000:
                            pop_index = int(pop_index)
                        elif pop_index < 10000:
                            pop_index = 10 * round(pop_index / 10)
                        else:
                            pop_index = 1000 * round(pop_index / 1000)

                        dist_adjusted = grid_penalty_ratio[unelec]*(dist + existing_grid_cost_ratio * prev_dist)

                        if urban[unelec]:
                            grid_lcoe = grid_lcoes_urban[pop_index][int(dist_adjusted)]
                        elif pop[unelec] > 300:
                            grid_lcoe = grid_lcoes_peri_urban[pop_index][int(dist_adjusted)]
                        else:
                            grid_lcoe = grid_lcoes_rural[pop_index][int(dist_adjusted)]

                        if grid_lcoe < min_tech_lcoes[unelec]:
                            if grid_lcoe < new_lcoes[unelec]:
                                if new_lcoes[unelec] == 99:
                                    new_grid_capacity += peak_load
                                new_lcoes[unelec] = grid_lcoe
                                cell_path_real[unelec] = dist + prev_dist
                                cell_path_adjusted[unelec] = dist_adjusted
                                if unelec not in changes:
                                    changes.append(unelec)

            electrified = changes[:]
            unelectrified = [x for x in unelectrified if x not in electrified]

        return new_lcoes, cell_path_adjusted

    def run_elec(self, grid_lcoes_rural, grid_lcoes_urban, grid_lcoes_peri_urban, grid_price,
                 existing_grid_cost_ratio, max_dist, coordinate_units, grid_calc):
        """
        Runs the pre-elec and grid extension algorithms
        """
        grid_capacity_limit = 9999999999  # 400000 # kW
        # Calculate 2030 pre-electrification
        logging.info('Determine future pre-electrification status')
        self.df[SET_ELEC_FUTURE] = self.df.apply(lambda row: 1 if row[SET_ELEC_CURRENT] == 1 else 0, axis=1)

        pre_elec_dist = 10  # The maximum distance from the grid in km to pre-electrifiy settlements
        self.df.loc[self.df[SET_GRID_DIST_PLANNED] < pre_elec_dist, SET_ELEC_FUTURE] = self.pre_elec(grid_lcoes_rural,
                                                                                                     grid_lcoes_urban,
                                                                                                     grid_lcoes_peri_urban,
                                                                                                     pre_elec_dist,
                                                                                                     grid_calc,
                                                                                                     grid_capacity_limit)

        self.df[SET_LCOE_GRID] = 99
        # self.df[SET_LCOE_GRID] = self.df.apply(lambda row: grid_price if row[SET_ELEC_FUTURE] == 1 else 99, axis=1)
        self.df[SET_LCOE_GRID] = self.df.apply(lambda row: 0.01 if row[SET_ELEC_FUTURE] == 1 else 99, axis=1)

        self.df[SET_LCOE_GRID], self.df[SET_MIN_GRID_DIST] = self.elec_extension(grid_lcoes_rural, grid_lcoes_urban,
                                                                                 grid_lcoes_peri_urban,
                                                                                 existing_grid_cost_ratio,
                                                                                 max_dist, coordinate_units, grid_calc,
                                                                                 grid_capacity_limit)

    def set_scenario_variables(self, energy_per_hh_rural, energy_per_hh_urban, energy_per_hh_periurban,
                               num_people_per_hh_rural, num_people_per_hh_urban):
        """
        Set the basic scenario parameters that differ based on urban/rural
        So that they are in the table and can be read directly to calculate LCOEs
        """

        logging.info('Setting electrification targets')
        self.df.loc[(self.df[SET_URBAN] == 0) & (self.df[SET_POP_CALIB] > 300), SET_ENERGY_PER_HH] = energy_per_hh_periurban
        self.df.loc[(self.df[SET_URBAN] == 0) & (self.df[SET_POP_CALIB] <= 300), SET_ENERGY_PER_HH] = energy_per_hh_rural
        self.df.loc[self.df[SET_URBAN] == 1, SET_ENERGY_PER_HH] = energy_per_hh_urban

        self.df.loc[self.df[SET_URBAN] == 0, SET_NUM_PEOPLE_PER_HH] = num_people_per_hh_rural
        self.df.loc[self.df[SET_URBAN] == 1, SET_NUM_PEOPLE_PER_HH] = num_people_per_hh_urban

    def calculate_off_grid_lcoes(self, mg_hydro_calc, mg_wind_calc, mg_pv_calc,
                                 sa_pv_calc, mg_diesel_calc, sa_diesel_calc, pv_diesel_hyb, urban_hybrid, rural_hybrid):
        """
        Calcuate the LCOEs for all off-grid technologies, and calculate the minimum, so that the electrification
        algorithm knows where the bar is before it becomes economical to electrify
        """

        # A df with all hydropower sites, to ensure that they aren't assigned more capacity than is available
        hydro_used = 'HydropowerUsed'  # the amount of the hydro potential that has been assigned
        hydro_df = self.df[[SET_HYDRO_FID, SET_HYDRO]].drop_duplicates(subset=SET_HYDRO_FID)
        hydro_df[hydro_used] = 0
        hydro_df = hydro_df.set_index(SET_HYDRO_FID)

        max_hydro_dist = 5  # the max distance in km to consider hydropower viable

        def hydro_lcoe(row):
            if row[SET_HYDRO_DIST] < max_hydro_dist:
                # calculate the capacity that would be added by the settlement
                additional_capacity = ((row[SET_NEW_CONNECTIONS_PROD] * row[SET_ENERGY_PER_HH] / row[SET_NUM_PEOPLE_PER_HH])
                                       / (HOURS_PER_YEAR * mg_hydro_calc.capacity_factor *
                                          mg_hydro_calc.base_to_peak_load_ratio))

                # and add it to the tracking df
                hydro_df.loc[row[SET_HYDRO_FID], hydro_used] += additional_capacity

                # if it exceeds the available capacity, it's not an option
                if hydro_df.loc[row[SET_HYDRO_FID], hydro_used] > hydro_df.loc[row[SET_HYDRO_FID], SET_HYDRO]:
                    return 99

                else:
                    return mg_hydro_calc.get_lcoe(energy_per_hh=row[SET_ENERGY_PER_HH],
                                                  people=row[SET_NEW_CONNECTIONS_PROD],
                                                  num_people_per_hh=row[SET_NUM_PEOPLE_PER_HH],
                                                  mv_line_length=row[SET_HYDRO_DIST])
            else:
                return 99

        logging.info('Calculate minigrid hydro LCOE')
        self.df[SET_LCOE_MG_HYDRO] = self.df.apply(hydro_lcoe, axis=1)

        num_hydro_limited = hydro_df.loc[hydro_df[hydro_used] > hydro_df[SET_HYDRO]][SET_HYDRO].count()
        logging.info('{} potential hydropower sites were utilised to maximum capacity'.format(num_hydro_limited))

        logging.info('Calculate minigrid PV LCOE')
        self.df[SET_LCOE_MG_PV] = self.df.apply(
            lambda row: mg_pv_calc.get_lcoe(energy_per_hh=row[SET_ENERGY_PER_HH],
                                            people=row[SET_NEW_CONNECTIONS_PROD],
                                            num_people_per_hh=row[SET_NUM_PEOPLE_PER_HH],
                                            capacity_factor=row[SET_GHI] / HOURS_PER_YEAR)
            if (row[SET_SOLAR_RESTRICTION] == 1 and row[SET_GHI] > 1000) else 99,
            axis=1)

        logging.info('Calculate minigrid wind LCOE')
        self.df[SET_LCOE_MG_WIND] = self.df.apply(
            lambda row: mg_wind_calc.get_lcoe(energy_per_hh=row[SET_ENERGY_PER_HH],
                                              people=row[SET_NEW_CONNECTIONS_PROD],
                                              num_people_per_hh=row[SET_NUM_PEOPLE_PER_HH],
                                              capacity_factor=row[SET_WINDCF])
            if row[SET_WINDCF] > 0.1 else 99,
            axis=1)

        logging.info('Calculate minigrid diesel LCOE')
        self.df[SET_LCOE_MG_DIESEL] = self.df.apply(
            lambda row:
            mg_diesel_calc.get_lcoe(energy_per_hh=row[SET_ENERGY_PER_HH],
                                    people=row[SET_NEW_CONNECTIONS_PROD],
                                    num_people_per_hh=row[SET_NUM_PEOPLE_PER_HH],
                                    travel_hours=row[SET_TRAVEL_HOURS]),
            axis=1)

        logging.info('Calculate standalone diesel LCOE')
        self.df[SET_LCOE_SA_DIESEL] = self.df.apply(
            lambda row:
            sa_diesel_calc.get_lcoe(energy_per_hh=row[SET_ENERGY_PER_HH],
                                    people=row[SET_NEW_CONNECTIONS_PROD],
                                    num_people_per_hh=row[SET_NUM_PEOPLE_PER_HH],
                                    travel_hours=row[SET_TRAVEL_HOURS]),
            axis=1)

        logging.info('Calculate standalone PV LCOE')
        self.df[SET_LCOE_SA_PV] = self.df.apply(
            lambda row: sa_pv_calc.get_lcoe(energy_per_hh=row[SET_ENERGY_PER_HH],
                                            people=row[SET_NEW_CONNECTIONS_PROD],
                                            num_people_per_hh=row[SET_NUM_PEOPLE_PER_HH],
                                            capacity_factor=row[SET_GHI] / HOURS_PER_YEAR)
            if row[SET_GHI] > 1000 else 99,
            axis=1)

        logging.info('Calculate PV diesel hybrid LCOE')
        self.df[SET_LCOE_MG_HYBRID] = self.df.apply(
            lambda row: pv_diesel_hyb.get_lcoe(energy_per_hh=row[SET_ENERGY_PER_HH],
                                               people=row[SET_NEW_CONNECTIONS_PROD],
                                               num_people_per_hh=row[SET_NUM_PEOPLE_PER_HH],
                                               travel_hours=row[SET_TRAVEL_HOURS],
                                               ghi=row[SET_GHI],
                                               urban=row[SET_URBAN],
                                               urban_hybrid=urban_hybrid,
                                               rural_hybrid=rural_hybrid,
                                               mg_hybrid=True,
                                               pv=True)
            if row[SET_GHI] > 9999 else 99,
            axis=1)

        logging.info('Determine minimum technology (no grid)')
        self.df[SET_MIN_OFFGRID] = self.df[[SET_LCOE_SA_DIESEL, SET_LCOE_SA_PV, SET_LCOE_MG_WIND,
                                            SET_LCOE_MG_DIESEL, SET_LCOE_MG_PV, SET_LCOE_MG_HYDRO,
                                            SET_LCOE_MG_HYBRID]].T.idxmin()

        logging.info('Determine minimum tech LCOE')
        self.df[SET_MIN_OFFGRID_LCOE] = self.df.apply(lambda row: (row[row[SET_MIN_OFFGRID]]), axis=1)

    def results_columns(self, mg_hydro_calc, mg_wind_calc, mg_pv_calc, sa_pv_calc,
                        mg_diesel_calc, sa_diesel_calc, grid_calc, pv_diesel_hyb, urban_hybrid, rural_hybrid):
        """
        Once the grid extension algorithm has been run, determine the minimum overall option, and calculate the
        capacity and investment requirements for each settlement
        """

        def res_investment_cost(row):
            min_tech = row[SET_MIN_OVERALL]
            if min_tech == SET_LCOE_SA_DIESEL:
                return sa_diesel_calc.get_lcoe(energy_per_hh=row[SET_ENERGY_PER_HH],
                                               people=row[SET_NEW_CONNECTIONS_PROD],
                                               num_people_per_hh=row[SET_NUM_PEOPLE_PER_HH],
                                               travel_hours=row[SET_TRAVEL_HOURS],
                                               get_investment_cost=True)
            elif min_tech == SET_LCOE_SA_PV:
                return sa_pv_calc.get_lcoe(energy_per_hh=row[SET_ENERGY_PER_HH],
                                           people=row[SET_NEW_CONNECTIONS_PROD],
                                           num_people_per_hh=row[SET_NUM_PEOPLE_PER_HH],
                                           capacity_factor=row[SET_GHI] / HOURS_PER_YEAR,
                                           get_investment_cost=True)
            elif min_tech == SET_LCOE_MG_WIND:
                return mg_wind_calc.get_lcoe(energy_per_hh=row[SET_ENERGY_PER_HH],
                                             people=row[SET_NEW_CONNECTIONS_PROD],
                                             num_people_per_hh=row[SET_NUM_PEOPLE_PER_HH],
                                             capacity_factor=row[SET_WINDCF],
                                             get_investment_cost=True)
            elif min_tech == SET_LCOE_MG_DIESEL:
                return mg_diesel_calc.get_lcoe(energy_per_hh=row[SET_ENERGY_PER_HH],
                                               people=row[SET_NEW_CONNECTIONS_PROD],
                                               num_people_per_hh=row[SET_NUM_PEOPLE_PER_HH],
                                               travel_hours=row[SET_TRAVEL_HOURS],
                                               get_investment_cost=True)
            elif min_tech == SET_LCOE_MG_PV:
                return mg_pv_calc.get_lcoe(energy_per_hh=row[SET_ENERGY_PER_HH],
                                           people=row[SET_NEW_CONNECTIONS_PROD],
                                           num_people_per_hh=row[SET_NUM_PEOPLE_PER_HH],
                                           capacity_factor=row[SET_GHI] / HOURS_PER_YEAR,
                                           get_investment_cost=True)
            elif min_tech == SET_LCOE_MG_HYDRO:
                return mg_hydro_calc.get_lcoe(energy_per_hh=row[SET_ENERGY_PER_HH],
                                              people=row[SET_NEW_CONNECTIONS_PROD],
                                              num_people_per_hh=row[SET_NUM_PEOPLE_PER_HH],

                                              mv_line_length=row[SET_HYDRO_DIST],
                                              get_investment_cost=True)
            elif min_tech == SET_LCOE_GRID:
                return grid_calc.get_lcoe(energy_per_hh=row[SET_ENERGY_PER_HH],
                                          people=row[SET_NEW_CONNECTIONS_PROD],
                                          num_people_per_hh=row[SET_NUM_PEOPLE_PER_HH],
                                          additional_mv_line_length=row[SET_MIN_GRID_DIST],
                                          get_investment_cost=True)
            elif min_tech == SET_LCOE_MG_HYBRID:
                return pv_diesel_hyb.get_lcoe(energy_per_hh=row[SET_ENERGY_PER_HH],
                                              people=row[SET_NEW_CONNECTIONS_PROD],
                                              num_people_per_hh=row[SET_NUM_PEOPLE_PER_HH],
                                              travel_hours=row[SET_TRAVEL_HOURS],
                                              ghi=row[SET_GHI],
                                              urban=row[SET_URBAN],
                                              urban_hybrid = urban_hybrid,
                                              rural_hybrid = rural_hybrid,
                                              pv=True,
                                              mg_hybrid=True,
                                              get_investment_cost=True)
            else:
                raise ValueError('A technology has not been accounted for in res_investment_cost()')

        logging.info('Determine minimum overall')
        self.df[SET_MIN_OVERALL] = self.df[[SET_LCOE_GRID, SET_LCOE_SA_DIESEL, SET_LCOE_SA_PV, SET_LCOE_MG_WIND,
                                            SET_LCOE_MG_DIESEL, SET_LCOE_MG_PV, SET_LCOE_MG_HYDRO, SET_LCOE_MG_HYBRID]].T.idxmin()

        logging.info('Determine minimum overall LCOE')
        self.df[SET_MIN_OVERALL_LCOE] = self.df.apply(lambda row: (row[row[SET_MIN_OVERALL]]), axis=1)

        logging.info('Add technology codes')
        codes = {SET_LCOE_GRID: 1, SET_LCOE_MG_HYDRO: 7, SET_LCOE_MG_WIND: 6, SET_LCOE_MG_PV: 5,
                 SET_LCOE_MG_DIESEL: 4, SET_LCOE_SA_DIESEL: 2, SET_LCOE_SA_PV: 3, SET_LCOE_MG_HYBRID: 8}
        self.df.loc[self.df[SET_MIN_OVERALL] == SET_LCOE_GRID, SET_MIN_OVERALL_CODE] = codes[SET_LCOE_GRID]
        self.df.loc[self.df[SET_MIN_OVERALL] == SET_LCOE_MG_HYDRO, SET_MIN_OVERALL_CODE] = codes[SET_LCOE_MG_HYDRO]
        self.df.loc[self.df[SET_MIN_OVERALL] == SET_LCOE_SA_PV, SET_MIN_OVERALL_CODE] = codes[SET_LCOE_SA_PV]
        self.df.loc[self.df[SET_MIN_OVERALL] == SET_LCOE_MG_WIND, SET_MIN_OVERALL_CODE] = codes[SET_LCOE_MG_WIND]
        self.df.loc[self.df[SET_MIN_OVERALL] == SET_LCOE_MG_PV, SET_MIN_OVERALL_CODE] = codes[SET_LCOE_MG_PV]
        self.df.loc[self.df[SET_MIN_OVERALL] == SET_LCOE_MG_DIESEL, SET_MIN_OVERALL_CODE] = codes[SET_LCOE_MG_DIESEL]
        self.df.loc[self.df[SET_MIN_OVERALL] == SET_LCOE_SA_DIESEL, SET_MIN_OVERALL_CODE] = codes[SET_LCOE_SA_DIESEL]
        self.df.loc[self.df[SET_MIN_OVERALL] == SET_LCOE_MG_HYBRID, SET_MIN_OVERALL_CODE] = codes[SET_LCOE_MG_HYBRID]

        logging.info('Determine minimum category')
        self.df[SET_MIN_CATEGORY] = self.df[SET_MIN_OVERALL].str.extract('(SA|MG|Grid)', expand=False)

        logging.info('Calculate new capacity')

        def hybrid_capacity(row):
            if row[SET_MIN_OVERALL] == SET_LCOE_MG_HYBRID:
                return pv_diesel_hyb.get_lcoe(energy_per_hh=row[SET_ENERGY_PER_HH],
                                              people=row[SET_NEW_CONNECTIONS_PROD],
                                              num_people_per_hh=row[SET_NUM_PEOPLE_PER_HH],
                                              travel_hours=row[SET_TRAVEL_HOURS],
                                              ghi=row[SET_GHI],
                                              urban=row[SET_URBAN],
                                              urban_hybrid=urban_hybrid,
                                              rural_hybrid=rural_hybrid,
                                              pv=True,
                                              mg_hybrid=True,
                                              get_capacity=True)
        self.df[SET_NEW_CAPACITY] = self.df.apply(hybrid_capacity, axis=1)


        self.df.loc[self.df[SET_MIN_OVERALL] == SET_LCOE_GRID, SET_NEW_CAPACITY] = (
                (self.df[SET_NEW_CONNECTIONS_PROD] * self.df[SET_ENERGY_PER_HH] / self.df[SET_NUM_PEOPLE_PER_HH]) /
                (HOURS_PER_YEAR * grid_calc.capacity_factor * grid_calc.base_to_peak_load_ratio
                 * (1 - grid_calc.distribution_losses)))
        self.df.loc[self.df[SET_MIN_OVERALL] == SET_LCOE_MG_HYDRO, SET_NEW_CAPACITY] = (
                (self.df[SET_NEW_CONNECTIONS_PROD] * self.df[SET_ENERGY_PER_HH] / self.df[SET_NUM_PEOPLE_PER_HH]) /
                (HOURS_PER_YEAR * mg_hydro_calc.capacity_factor * mg_hydro_calc.base_to_peak_load_ratio
                 * (1 - mg_hydro_calc.distribution_losses)))
        self.df.loc[self.df[SET_MIN_OVERALL] == SET_LCOE_MG_PV, SET_NEW_CAPACITY] = (
                (self.df[SET_NEW_CONNECTIONS_PROD] * self.df[SET_ENERGY_PER_HH] / self.df[SET_NUM_PEOPLE_PER_HH]) /
                (HOURS_PER_YEAR * (self.df[SET_GHI] / HOURS_PER_YEAR) * mg_pv_calc.base_to_peak_load_ratio
                 * (1 - mg_pv_calc.distribution_losses)))
        self.df.loc[self.df[SET_MIN_OVERALL] == SET_LCOE_MG_WIND, SET_NEW_CAPACITY] = (
                (self.df[SET_NEW_CONNECTIONS_PROD] * self.df[SET_ENERGY_PER_HH] / self.df[SET_NUM_PEOPLE_PER_HH]) /
                (HOURS_PER_YEAR * self.df[SET_WINDCF] * mg_wind_calc.base_to_peak_load_ratio
                 * (1 - mg_wind_calc.distribution_losses)))
        self.df.loc[self.df[SET_MIN_OVERALL] == SET_LCOE_MG_DIESEL, SET_NEW_CAPACITY] = (
                (self.df[SET_NEW_CONNECTIONS_PROD] * self.df[SET_ENERGY_PER_HH] / self.df[SET_NUM_PEOPLE_PER_HH]) /
                (HOURS_PER_YEAR * mg_diesel_calc.capacity_factor * mg_diesel_calc.base_to_peak_load_ratio
                 * (1 - mg_diesel_calc.distribution_losses)))
        self.df.loc[self.df[SET_MIN_OVERALL] == SET_LCOE_SA_DIESEL, SET_NEW_CAPACITY] = (
                (self.df[SET_NEW_CONNECTIONS_PROD] * self.df[SET_ENERGY_PER_HH] / self.df[SET_NUM_PEOPLE_PER_HH]) /
                (HOURS_PER_YEAR * sa_diesel_calc.capacity_factor * sa_diesel_calc.base_to_peak_load_ratio
                 * (1 - sa_diesel_calc.distribution_losses)))
        self.df.loc[self.df[SET_MIN_OVERALL] == SET_LCOE_SA_PV, SET_NEW_CAPACITY] = (
                (self.df[SET_NEW_CONNECTIONS_PROD] * self.df[SET_ENERGY_PER_HH] / self.df[SET_NUM_PEOPLE_PER_HH]) /
                (HOURS_PER_YEAR * (self.df[SET_GHI] / HOURS_PER_YEAR) * sa_pv_calc.base_to_peak_load_ratio
                 * (1 - sa_pv_calc.distribution_losses)))

        logging.info('Calculate investment cost')
        self.df[SET_INVESTMENT_COST] = self.df.apply(res_investment_cost, axis=1)

    def calc_summaries(self):
        """
        The next section calculates the summaries for technology split, consumption added and total investment cost
        """

        population_ = 'population_'
        new_connections_ = 'new_connections_'
        capacity_ = 'capacity_'
        investments_ = 'investment_'

        logging.info('Calculate summaries')
        rows = []
        techs = [SET_LCOE_GRID, SET_LCOE_SA_DIESEL, SET_LCOE_SA_PV, SET_LCOE_MG_WIND,
                 SET_LCOE_MG_DIESEL, SET_LCOE_MG_PV, SET_LCOE_MG_HYDRO, SET_LCOE_MG_HYBRID]
        rows.extend([population_ + t for t in techs])
        rows.extend([new_connections_ + t for t in techs])
        rows.extend([capacity_ + t for t in techs])
        rows.extend([investments_ + t for t in techs])
        summary = pd.Series(index=rows)

        for t in techs:
            summary.loc[population_ + t] = self.df.loc[self.df[SET_MIN_OVERALL] == t, SET_POP_FUTURE].sum()
            summary.loc[new_connections_ + t] = self.df.loc[self.df[SET_MIN_OVERALL] == t, SET_NEW_CONNECTIONS].sum()
            summary.loc[capacity_ + t] = self.df.loc[self.df[SET_MIN_OVERALL] == t, SET_NEW_CAPACITY].sum()
            summary.loc[investments_ + t] = self.df.loc[self.df[SET_MIN_OVERALL] == t, SET_INVESTMENT_COST].sum()

        return summary

    def get_health_demand(self, people, tier):
        if people >= 0:  # Set this number to 999999 to "shut off" health demand
            wb_tiers_health = {1: 10, 2: 20, 3: 30, 4: 40, 5: 50}

            hct1 = 0.25  # Elec. demand per bed (kWh/day) check corresponding excel file
            hct2 = 0.17  # Elec. demand per bed (kWh/day) check corresponding excel file
            hct3 = 0.12  # Elec. demand per bed (kWh/day) check corresponding excel file
            hct4 = 26.97  # Elec. demand per bed (kWh/day) check corresponding excel file

            # Hamlet: settlement with population below 50 ppl per sq.km\n
            # Village: settlement with population between 51 and 880 per sq.km
            # Town: settlememtn with population between 881 and 2000 per sq.km
            # City: settlement with population above 2000 ppl per sq.km

            if people <= 50:
                healthdemand = people * hct1 * (wb_tiers_health[tier] / 10000) * 365  # kWh/person/year
            elif 50 < people <= 880:
                healthdemand = people * hct2 * (wb_tiers_health[tier] / 10000) * 365  # kWh/person/year
            elif 880 < people <= 2000:
                healthdemand = people * hct3 * (wb_tiers_health[tier] / 10000) * 365  # kWh/person/year
            else:
                healthdemand = people * hct4 * (wb_tiers_health[tier] / 10000) * 365  # kWh/person/year

            return healthdemand
        else:
            return 0

    def get_education_demand(self, people, tier, Primpop15=0.132, Seconpop15=0.164, studinclass=40, sizeofclass=50):
        if people >= 0:   # Set this number to 999999 to "shut off" education demand
            wb_tiers_education = {1: 1.05, 2: 3.15, 3: 6.3, 4: 9.45, 5: 12.6}
            studentratio = (Primpop15 + Seconpop15)
            studentpop = studentratio * people

            # Settlement categorization
            # Hamlet: settlement with population below 50 ppl per sq.km\n
            # Village: settlement with population between 51 and 880 per sq.km
            # Town: settlement with population between 881 and 2000 per sq.km
            # City: settlement with population above 2000 ppl per sq.km

            schoolsize = studentpop * (sizeofclass/studinclass+1.5)
            schoolelec = schoolsize * wb_tiers_education[tier]

            return schoolelec
        else:
            return 0

    def calc_education_demand(self, wb_tier_urban, wb_tier_rural, wb_tier_periurban):
        def education_demand(row):
            if row[SET_URBAN] == 1:  #  and row[SET_POP_FUTURE] >= 20:
                return self.get_education_demand(people=row[SET_POP_FUTURE],
                                                              tier=wb_tier_urban)
            elif row[SET_POP_CALIB] > 300:
                return self.get_education_demand(people=row[SET_POP_FUTURE],
                                                 tier=wb_tier_periurban)
            else:
                #  elif row[SET_POP_FUTURE] >= 20:
                return self.get_education_demand(people=row[SET_POP_FUTURE],
                                                              tier=wb_tier_rural)


        self.df['EducationDemand'] = self.df.apply(education_demand, axis=1)
        self.df['EducationDemand'] = 0

    def calc_health_demand(self, wb_tier_urban, wb_tier_rural, wb_tier_periurban):
        def health_demand(row):
            if row[SET_URBAN] == 1:  # and row[SET_POP_FUTURE] >= 20:
                return self.get_health_demand(people=row[SET_POP_FUTURE],
                                                        tier=wb_tier_urban)
            elif row[SET_POP_CALIB] > 300:
                return self.get_health_demand(people=row[SET_POP_FUTURE],
                                              tier=wb_tier_periurban)
            else:
                #  elif row[SET_POP_FUTURE] >= 20:
                return self.get_health_demand(people=row[SET_POP_FUTURE],
                                                        tier=wb_tier_rural)


        self.df['HealthDemand'] = self.df.apply(health_demand, axis=1)
        self.df['HealthDemand'] = 0

    def new_connections_prod(self, energy_per_hh_rural, energy_per_hh_urban, energy_per_hh_periurban,
                               num_people_per_hh_rural, num_people_per_hh_urban):
        self.df.loc[self.df[SET_URBAN] == 1, SET_NEW_CONNECTIONS_PROD] = self.df[SET_NEW_CONNECTIONS] + (self.df['HealthDemand'] + self.df['EducationDemand'])/(energy_per_hh_urban/num_people_per_hh_urban)
        self.df.loc[(self.df[SET_URBAN] == 0) & (self.df[SET_POP_CALIB] > 300), SET_NEW_CONNECTIONS_PROD] = self.df[SET_NEW_CONNECTIONS] + (self.df['HealthDemand'] + self.df['EducationDemand']) / (energy_per_hh_rural / num_people_per_hh_rural)
        self.df.loc[(self.df[SET_URBAN] == 0) & (self.df[SET_POP_CALIB] <= 300), SET_NEW_CONNECTIONS_PROD] = self.df[SET_NEW_CONNECTIONS] + (self.df['HealthDemand'] + self.df['EducationDemand']) / (energy_per_hh_periurban / num_people_per_hh_rural)