import yaml

def test_sources_yaml_loaded():
    with open("config/sources.yaml","r",encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    assert "sources" in cfg and len(cfg["sources"]) == 2
    for s in cfg["sources"]:
        assert "name" in s and "type" in s and "list_url" in s and "item_selector" in s
