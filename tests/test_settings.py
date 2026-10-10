from dataclasses import replace
import pytest
from netmap.core.settings import Settings


def test_settings_roundtrip(tmp_path):
    path=tmp_path/'settings.json'
    s=replace(Settings(),interval=.5,origin_enabled=True,origin_lat=55.75,origin_lon=37.62)
    s.save(path)
    assert Settings.load(path)==s
    assert not path.with_suffix('.tmp').exists()


@pytest.mark.parametrize('change',[{'interval':0},{'interval':float('nan')},{'origin_lat':91},{'retention_days':0},
                                 {'map_limit':42},{'diagnostic_count':100},{'online_tiles':'false'}])
def test_invalid_settings(change):
    with pytest.raises(ValueError): replace(Settings(),**change).validate()
