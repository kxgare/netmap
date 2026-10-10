from collections import OrderedDict
import ipaddress
from pathlib import Path
import geoip2.database
import geoip2.errors
import maxminddb.errors
from netmap.core.models import Location


def public_ip(value: str) -> bool:
    try:
        ip = ipaddress.ip_address(value.split("%")[0])
        if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
            ip = ip.ipv4_mapped
        return ip.is_global and not ip.is_multicast
    except ValueError:
        return False


class GeoResolver:
    def __init__(self, path: str = "", reader_factory=geoip2.database.Reader, cache_size=8192):
        self.reader = None
        self.cache = OrderedDict()
        self.cache_size = cache_size
        self.message = "База GeoLite2 не выбрана. IP без координат остаются в таблице."
        if path:
            try:
                self.reader = reader_factory(str(Path(path)))
                self.message = "Локальная геолокация включена · координаты приблизительные"
            except (OSError, ValueError, maxminddb.errors.InvalidDatabaseError) as exc:
                self.message = f"Не удалось открыть базу геолокации: {exc}"

    def lookup(self, ip: str) -> Location:
        if not public_ip(ip):
            return Location(reason="Локальный, служебный или некорректный адрес")
        if ip in self.cache:
            self.cache.move_to_end(ip)
            return self.cache[ip]
        if self.reader is None:
            return Location(reason="Локальная база геолокации недоступна")
        try:
            record = self.reader.city(ip.split("%")[0])
            lat, lon = record.location.latitude, record.location.longitude
            if lat is not None and lon is not None and not (-90 <= lat <= 90 and -180 <= lon <= 180):
                lat = lon = None
            result = Location(record.country.names.get("ru") or record.country.name or "",
                              record.city.names.get("ru") or record.city.name or "",
                              lat, lon, record.location.accuracy_radius,
                              "" if lat is not None and lon is not None else "Координаты не найдены")
        except geoip2.errors.AddressNotFoundError:
            result = Location(reason="Адрес отсутствует в базе")
        except (ValueError, OSError, maxminddb.errors.InvalidDatabaseError) as exc:
            result = Location(reason=f"Ошибка чтения базы: {exc}")
        self.cache[ip] = result
        if len(self.cache) > self.cache_size:
            self.cache.popitem(last=False)
        return result

    def close(self):
        if self.reader:
            self.reader.close()
            self.reader = None
