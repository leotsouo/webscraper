import pandas as pd
from src.pipeline.clean import normalize_date, to_number

def test_date_normalization():
    assert normalize_date("2024-01-02") == "20240102"
    assert normalize_date("20240102") == "20240102"
    assert normalize_date("not-a-date") == ""

def test_to_number():
    assert to_number("$1,234.56") == 1234.56
    assert to_number("N/A") is None
    assert to_number("-99.5") == -99.5
