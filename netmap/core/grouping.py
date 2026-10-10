from collections import defaultdict
from netmap.geo.resolver import public_ip

def group_apps(connections):
    groups=defaultdict(list)
    for c in connections: groups[c.app_key].append(c)
    return [{'key':key,'name':rows[0].process,'executable':rows[0].executable,'count':len(rows),
             'public_ips':sorted({c.remote_ip for c in rows if public_ip(c.remote_ip)}),
             'remote_ips':sorted({c.remote_ip for c in rows if c.remote_ip}),
             'local_count':sum(not public_ip(c.remote_ip) for c in rows),
             'last':max(c.observed for c in rows),'connections':rows} for key,rows in groups.items()]
