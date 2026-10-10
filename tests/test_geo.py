from types import SimpleNamespace as NS
import pytest
import geoip2.errors
from netmap.geo.resolver import GeoResolver, public_ip


@pytest.mark.parametrize('ip',['127.0.0.1','10.0.0.1','192.168.1.1','169.254.1.1','::1','fe80::1%2','fc00::1','224.0.0.1','ff02::1','192.0.2.1','bad','','::ffff:192.168.1.1'])
def test_non_public(ip): assert not public_ip(ip)


@pytest.mark.parametrize('ip',['8.8.8.8','2606:4700:4700::1111','::ffff:8.8.8.8'])
def test_public(ip): assert public_ip(ip)


def test_no_database_does_not_invent_coordinates():
    loc=GeoResolver().lookup('8.8.8.8')
    assert not loc.mapped and loc.reason


def test_lookup_cache_and_russian_names():
    class Reader:
        calls=0
        def city(self,ip):
            self.calls+=1
            return NS(country=NS(names={'ru':'США'},name='US'),city=NS(names={'ru':'Город'},name='City'),
                      location=NS(latitude=40,longitude=-70,accuracy_radius=50))
        def close(self): pass
    reader=Reader()
    resolver=GeoResolver('fixture.mmdb',lambda _:reader)
    assert resolver.lookup('8.8.8.8').country=='США'
    assert resolver.lookup('8.8.8.8').accuracy_km==50
    assert reader.calls==1
    assert not resolver.lookup('10.0.0.1').mapped
    assert reader.calls==1
    resolver.close()


def test_bad_database(tmp_path):
    path=tmp_path/'bad.mmdb'; path.write_text('invalid database')
    resolver=GeoResolver(str(path))
    assert resolver.reader is None and not resolver.lookup('8.8.8.8').mapped


def test_missing_address_and_bounded_cache():
    class Reader:
        def city(self,ip): raise geoip2.errors.AddressNotFoundError('not found')
        def close(self): pass
    resolver=GeoResolver('fixture',lambda _:Reader(),cache_size=2)
    for ip in ['8.8.8.8','1.1.1.1','9.9.9.9']: assert not resolver.lookup(ip).mapped
    assert len(resolver.cache)==2 and '8.8.8.8' not in resolver.cache
