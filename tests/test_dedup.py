import pandas as pd
from src.pipeline.clean import clean_df

def test_dedup_pk():
    df = pd.DataFrame([
        {"source": "s1", "id": "1", "title": "A"},
        {"source": "s1", "id": "1", "title": "A-dup"},
        {"source": "s1", "id": "2", "title": "B"},
    ])
    out = clean_df(df)
    assert len(out) == 2
    assert "pk" in out.columns
