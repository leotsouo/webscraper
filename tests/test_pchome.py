from pipelines.pchome_fetch import normalize_item

def test_normalize_item_minimal():
    raw = {
        "Id": "DYARL9-A900AZTJT",
        "Name": "測試商品",
        "Price": {"P": 9990},
        "Brand": "TEST",
        "CateName": "手機",
    }
    out = normalize_item(raw)
    assert out["id"] == "DYARL9-A900AZTJT"
    assert out["title"] == "測試商品"
    assert out["price"] == 9990
    assert out["vendor"] == "TEST"
    assert out["category"] == "手機"
    assert out["url"].endswith("/DYARL9-A900AZTJT")
