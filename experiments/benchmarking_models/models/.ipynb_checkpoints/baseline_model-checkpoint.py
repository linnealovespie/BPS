import pandas as pd
import numpy as np

class BaselineBEPSModel:
    def __init__(self, emissions_path, timeline_path, building_data_path, fine_years, fine_per_sqft):
        '''
        emissions_path: file path to table of energy emissions factors for each year
        timeline_path: file path for proposed timeline of emissions reduction
        building_data_path: file path for buildings data
        fine_years: array of years where building owners can be fined for not being compliant
        '''
        self.emissions_path = emissions_path
        self.timeline_path = timeline_path
        self.building_data_path = building_data_path
        self.fine_years = fine_years
        self.fine_per_sqft = fine_per_sqft

    def _load_timeline_data(self):
        self.timeline = pd.read_csv(self.timeline_path)

    def _load_building_data(self):
        self.building_data = pd.read_csv(self.building_data_path)

    def _load_emissions_data(self):
        emissions = pd.read_csv(self.emissions_path)
        emissions.set_index('Year', inplace=True)
        self.energy_emissions = emissions

    def _load_input_data(self):
        self._load_timeline_data()
        self._load_building_data()
        self._load_emissions_data()

    def _find_ghgi_standard(self, year, building_type, sq_ft_class):
        '''
        Find the GHGI standard in the model's timeline for a given year, building type, and building size.
        '''
        # building types listed as NAN don't count towards the policy, so their emissions and sq ft are calculated as zero
        if pd.isna(building_type) or building_type == 'nan':
            return 0
        row = self.timeline[(self.timeline['year'] == year) & (self.timeline['sq_ft_classification'] == sq_ft_class) & (self.timeline['building_type'] == building_type)]
        return row.iloc[0]['ghgi'] 
    
    def _get_expected_baseline(self, building, year):
        '''
        Find the expected baseline GHGE for a given year if the building makes no changes
        '''
        electric_emissions = building['Electricity(kBtu)'] * self.energy_emissions.loc[year]['Electricity emission factor (kgCO2e/kBtu)']
        steam_emissions = building['Steam(kBtu)'] * self.energy_emissions.loc[year]['Steam emission factor (kgCO2e/kBtu)']
        gas_emissions = building['NaturalGas(kBtu)'] * self.energy_emissions.loc[year]['Gas emission factor (kgCO2e/kBtu)']
        return electric_emissions + steam_emissions + gas_emissions
    
    def _get_expected_baseline_ghgi(self, building):
        '''
        Return the expected GHGI for a bulding if the building makes no changes
        '''
        if building['Total_sqft'] == 0:
            return 0

        return building['expected_baseline'] / building['Total_sqft']
    
    def _fill_in_expected_baselines(self, year_low, year_high, input_df, output_df):
        '''
        input_df: dataframe without any calculations, only building data
        output_df: df with OSE ID, building name, total sq ft, sq ft classification, year, and expected baseline for each year in between year_low and year_high
        '''
        for year in range(year_low, year_high + 1):
            temp_df = input_df[['OSEBuildingID', 'BuildingName', 'Total_sqft', 'sq_ft_classification', 'LargestPropertyUseType OSE', 'SecondLargestPropertyUseType OSE', 'ThirdLargestPropertyUseType OSE']]
            temp_df['year'] = pd.Series([year]*len(temp_df))
            temp_df['expected_baseline'] = input_df.apply(lambda building: self._get_expected_baseline(building, year), axis=1)

            output_df = pd.concat([output_df, temp_df])


        return output_df
    
    def _get_city_ghgi(self, building):
        year = building['year']
        baseline_ghgi = building['expected_baseline_ghgi']
        orig_building_row = self.building_data[self.building_data['OSEBuildingID'] == building['OSEBuildingID']].iloc[0]

        first_use_ghgi = self._find_ghgi_standard(year, orig_building_row['LargestPropertyUseType OSE'], building['sq_ft_classification'])
        second_use_ghgi = self._find_ghgi_standard(year, orig_building_row['SecondLargestPropertyUseType OSE'], building['sq_ft_classification'])
        third_use_ghgi = self._find_ghgi_standard(year, orig_building_row['ThirdLargestPropertyUseType OSE'], building['sq_ft_classification'])

        return (orig_building_row['percent_sqft_1st'] * (baseline_ghgi if pd.isna(first_use_ghgi) else first_use_ghgi)) + (orig_building_row['percent_sqft_2nd'] * (baseline_ghgi if pd.isna(second_use_ghgi) else second_use_ghgi)) + (orig_building_row['percent_sqft_3rd'] * (baseline_ghgi if pd.isna(third_use_ghgi) else third_use_ghgi))

    def _get_compliant_ghgi(self, building):
        '''
        Return the lower of: the city's benchmark and the expected emissions for a building
        '''
        return min(building['expected_baseline_ghgi'], building['city_ghgi_target'])

    def _get_compliant_emissions(self, building):
        return building['compliant_ghgi'] * building['Total_sqft']

    def _get_compliance_status(self, building):
        year = building['year']
        sqft_class = building['sq_ft_classification']
        if pd.isna(self._find_ghgi_standard(year, building['LargestPropertyUseType OSE'], sqft_class)) and pd.isna(self._find_ghgi_standard(year, building['SecondLargestPropertyUseType OSE'], sqft_class)) and pd.isna(self._find_ghgi_standard(year, building['ThirdLargestPropertyUseType OSE'], sqft_class)): 
            return 'Not due yet'
        elif building['expected_baseline_ghgi'] < building['city_ghgi_target']:
            return 'Yes'
        else:
            return 'No'
        
    def _get_noncompliance_fines(self, building):
        if building['year'] in self.fine_years:
            return building['Total_sqft'] * self.fine_per_sqft
        else:
            return 0
    
    def calculate_baseline_model(self, start_year, end_year):
        self._load_input_data()
        
        baseline_building_info = pd.DataFrame(columns=['OSEBuildingID', 'BuildingName', 'Total_sqft', 'sq_ft_classification'])
        scen_calcs = self._fill_in_expected_baselines(start_year, end_year, self.building_data, baseline_building_info)
        
        scen_calcs['expected_baseline_ghgi'] = scen_calcs.apply(lambda building: self._get_expected_baseline_ghgi(building), axis=1)
        scen_calcs['city_ghgi_target'] = scen_calcs.apply(lambda building: self._get_city_ghgi(building), axis=1)
        scen_calcs['compliant_ghgi'] = scen_calcs.apply(lambda building: self._get_compliant_ghgi(building), axis=1)
        scen_calcs['compliant_emissions'] = scen_calcs.apply(lambda building: self._get_compliant_emissions(building), axis=1)
        scen_calcs['compliance_status'] = scen_calcs.apply(lambda building: self._get_compliance_status(building), axis=1)
        scen_calcs['compliance_fees'] = scen_calcs.apply(lambda building: self._get_noncompliance_fines(building), axis=1)

        self.scenario_results = scen_calcs

        print('Model calculations complete. Access the model dataframe as model_name.scenario_results')