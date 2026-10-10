from collections import Counter
from dataclasses import asdict
from netmap.geo.resolver import public_ip


def statistics(connections):
    protocols = Counter(c.protocol for c in connections)
    apps = Counter(c.process for c in connections)
    ips = {c.remote_ip for c in connections if c.remote_ip}
    public = {c.remote_ip: c.location for c in connections if public_ip(c.remote_ip)}
    countries = Counter(loc.country or "Не определена" for loc in public.values())
    return {"total": len(connections), "protocols": dict(protocols),
            "apps": dict(apps.most_common(10)), "unique_ips": len(ips),
            "public_ips": len(public), "countries": dict(countries.most_common(10)),"countries_count":len([name for name in countries if name!="Не определена"]),
            "mapped": sum(loc.mapped for loc in public.values())}


def map_points(connections, historical=(), app=""):
    grouped = {}
    current = set()
    for c in connections:
        if app and c.app_key != app:
            continue
        if not c.location.mapped or not public_ip(c.remote_ip):
            continue
        current.add(c.remote_ip)
        point = grouped.setdefault(c.remote_ip, {"ip": c.remote_ip, **asdict(c.location),
                                    "active": True, "new": (c.first_seen or c.observed)==c.observed, "connections": [], "first": c.first_seen or c.observed,
                                    "last": c.observed})
        point["connections"].append({"process": c.process, "pid": c.pid, "protocol": c.protocol,
                                     "port": c.remote_port, "status": c.status})
        point["first"] = min(point["first"], c.first_seen or c.observed)
    for row in historical:
        if row["remote_ip"] in current or row["remote_ip"] in grouped:
            continue
        if app and (row["executable"] or row["process"]) != app:
            continue
        if row["latitude"] is None or row["longitude"] is None or not public_ip(row["remote_ip"]):
            continue
        grouped[row["remote_ip"]] = {"ip": row["remote_ip"], "latitude": row["latitude"],
             "longitude": row["longitude"], "country": row["country"], "city": row["city"],
             "accuracy_km": row["accuracy_km"], "active": False, "connections": [],
             "first": row["first_seen"], "last": row["last_seen"]}
    return list(grouped.values())
