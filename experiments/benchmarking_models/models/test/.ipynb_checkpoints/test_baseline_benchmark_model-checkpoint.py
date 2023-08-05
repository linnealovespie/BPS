import pandas as pd
import pytest

from .. import baseline_model

# constants
FAKE_EMISSIONS_CSV = 'fake_data/emissions.csv'
FAKE_TIMELINE_CSV = 'fake_data/timeline.csv'
FAKE_BUILDING_DATA_CSV = 'fake_data/building_data.csv'

STANDARD_FINE_YEARS = [2030, 2035, 2040, 2045, 2050]

# util methods and fixtures
@pytest.fixture
def emissions_df():
    return pd.read_csv(FAKE_EMISSIONS_CSV)

@pytest.fixture
def timeline_df():
    return pd.read_csv(FAKE_TIMELINE_CSV)

@pytest.fixture
def building_data_df():
    return pd.read_csv(FAKE_BUILDING_DATA_CSV)

# method to make instance w/ one or more user-chosen dataset
def make_test_model_intance(emissions = FAKE_EMISSIONS_CSV, timeline = FAKE_TIMELINE_CSV, building_data = FAKE_BUILDING_DATA_CSV, fine_years = STANDARD_FINE_YEARS):
    return baseline_model.BaselineBEPSModel(emissions, timeline, building_data, fine_years)

def test_init():
    model = baseline_model.BaselineBEPSModel('fake.csv', 'fake2.csv', 'fake3.csv', STANDARD_FINE_YEARS)
    assert model.emissions_path == 'fake.csv'
    assert model.timeline_path == 'fake2.csv'
    assert model.building_data_path == 'fake3.csv'
    assert model.fine_years == [2030, 2035, 2040]

# data loading tests
def test_all_data_loading():


def test_timeline_loading():


def test_emissions_loading():


def test_building_data_loading():


# calculation methods tests