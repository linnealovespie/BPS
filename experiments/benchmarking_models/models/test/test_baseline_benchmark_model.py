import pytest
import pandas as pd
import os

print(os.getcwd())

#from benchmarking_models.models import baseline_model

from ..models import baseline_model

def test_init():
    model = BaselineBEPSModel('fake.csv', 'fake2.csv', 'fake3.csv', [2030, 2035, 2040])
    assertIsInstance(model, BaselineBEPSModel)
