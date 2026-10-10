from dataclasses import replace
from netmap.core.models import Location
from netmap.core.statistics import map_points, statistics
from netmap.ui.table import matches


def test_real_counts_not_bandwidth(connection):
    other=replace(connection,pid=456,process='other.exe',local_port=52000)
    udp=replace(connection,protocol='UDP',remote_ip='',remote_port=0,local_port=5353,location=Location())
    stats=statistics([connection,other,udp])
    assert stats['total']==3 and stats['unique_ips']==1
    assert stats['protocols']=={'TCP':2,'UDP':1}
    assert stats['countries']=={'США':1}
    points=map_points([connection,other,udp])
    assert len(points)==1 and len(points[0]['connections'])==2
    assert {r['pid'] for r in points[0]['connections']}=={123,456}


def test_filter_literal_case_insensitive(connection):
    assert matches(connection,'BROWSER')
    assert matches(connection,'8.8.8.8','TCP',connection.app_key)
    assert not matches(connection,protocol='UDP')
    assert not matches(connection,app='another.exe')
    assert not matches(connection,"%")


def test_no_coordinates_no_marker(connection):
    assert map_points([replace(connection,location=Location())])==[]
    assert map_points([replace(connection,remote_ip='127.0.0.1')])==[]
