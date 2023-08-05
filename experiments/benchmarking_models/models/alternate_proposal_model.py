# This class expands the BaselineBEPSModel to allow for alternative scenarios

from baseline_model import BaselineBEPSModel

class AlternativeBEPSModel(BaselineBEPSModel):
    def __init__(self, emissions_path, timeline_path, building_data_path, fine_years, fine_per_sqft, alternative_calculation_function, baseline_model = None):
        '''
        emissions_path: file path to table of energy emissions factors for each year
        timeline_path: file path for proposed timeline of emissions reduction
        building_data_path: file path for buildings data
        fine_years: array of years where building owners can be fined for not being compliant
        alternative_calculations_function: takes a building as input and calculates the compliant emissions and compliance status
        baseline_model: baseline calculations from BaselineBEPSModel. If not provided, the instance will run the calculate_baseline_model method before running the alternative function
        '''
        super().__init__(emissions_path, timeline_path, building_data_path, fine_years, fine_per_sqft)
        self.alternative_calculation_function = alternative_calculation_function
        self.baseline_model = baseline_model

    def calculate_alternative_model(self):
        self._load_input_data()
        if not self.baseline_model:
            self.calculate_baseline_model()

        alternative = self.alternative_calculation_function(self.emissions, self.timeline, self.baseline_model)
        self.alternative_scenario = alternative
        print('You can now access your alternative scenario calculations at instance_name.alternative_scenario')
    