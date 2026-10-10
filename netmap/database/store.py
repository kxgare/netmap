from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
from netmap.core.models import Connection, utc_now

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
 id INTEGER PRIMARY KEY, connection_key TEXT NOT NULL, pid INTEGER,
 process TEXT NOT NULL, executable TEXT NOT NULL, protocol TEXT NOT NULL,
 local_ip TEXT NOT NULL, local_port INTEGER NOT NULL, remote_ip TEXT NOT NULL,
 remote_port INTEGER NOT NULL, status TEXT NOT NULL, first_seen TEXT NOT NULL,
 last_seen TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1,
 country TEXT NOT NULL, city TEXT NOT NULL, latitude REAL, longitude REAL, accuracy_km INTEGER
);
CREATE INDEX IF NOT EXISTS session_time ON sessions(last_seen);
CREATE INDEX IF NOT EXISTS session_ip ON sessions(remote_ip);
CREATE INDEX IF NOT EXISTS session_active ON sessions(active);
CREATE TABLE IF NOT EXISTS samples (
 time TEXT PRIMARY KEY, total INTEGER NOT NULL, new INTEGER NOT NULL, unique_ips INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS diagnostics (
 id INTEGER PRIMARY KEY, time TEXT NOT NULL, host TEXT NOT NULL, port INTEGER NOT NULL, result TEXT NOT NULL
);
PRAGMA user_version=1;
"""


def search_clause(search="", since="", until="", app="", pid=None, protocol="", ip=""):
    clauses, params = [], []
    if search:
        # Literal search: '%' and '_' entered by a user are not wildcards.
        escaped = search.casefold().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        clauses.append("(CASEFOLD(process) LIKE ? ESCAPE '\\' OR remote_ip LIKE ? ESCAPE '\\' OR local_ip LIKE ? ESCAPE '\\')")
        params += [f"%{escaped}%"] * 3
    if since:
        clauses.append("last_seen >= ?")
        params.append(since)
    if until:
        clauses.append("first_seen <= ?")
        params.append(until)
    if app:
        clauses.append("(executable = ? OR (executable = '' AND process = ?))")
        params += [app, app]
    for column,value in (("pid",pid),("protocol",protocol),("remote_ip",ip)):
        if value is not None and value != "":
            clauses.append(column+" = ?"); params.append(value)
    return (" WHERE " + " AND ".join(clauses) if clauses else ""), params


class HistoryStore:
    def __init__(self, path: Path | str):
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, timeout=5)
        self.db.row_factory = sqlite3.Row
        from netmap.geo.resolver import public_ip
        self.db.create_function("IS_PUBLIC",1,public_ip,deterministic=True)
        self.db.create_function("CASEFOLD",1,lambda value: value.casefold() if value else "",deterministic=True)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=NORMAL")
        version = self.db.execute("PRAGMA user_version").fetchone()[0]
        if version > 1:
            self.db.close()
            raise RuntimeError("База создана более новой версией NetMap")
        self.db.executescript(SCHEMA)
        # Live processes do not persist across app restarts. Preserve their last observed timestamp.
        with self.db:
            self.db.execute("UPDATE sessions SET active=0 WHERE active=1")
        self.active = {}  # connection key -> (session id, first seen)

    def observe(self, connections: list[Connection], timestamp: str):
        next_active = {}
        enriched = []
        new = 0
        with self.db:
            for c in connections:
                old = self.active.get(c.key)
                loc = c.location
                if old:
                    sid, first = old
                    self.db.execute("""UPDATE sessions SET last_seen=?, status=?, country=?, city=?,
                        latitude=?, longitude=?, accuracy_km=? WHERE id=?""",
                        (timestamp, c.status, loc.country, loc.city, loc.latitude, loc.longitude, loc.accuracy_km, sid))
                else:
                    first = timestamp
                    cur = self.db.execute("""INSERT INTO sessions
                        (connection_key,pid,process,executable,protocol,local_ip,local_port,remote_ip,remote_port,
                         status,first_seen,last_seen,country,city,latitude,longitude,accuracy_km)
                         VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                         (c.key,c.pid,c.process,c.executable,c.protocol,c.local_ip,c.local_port,c.remote_ip,
                          c.remote_port,c.status,first,timestamp,loc.country,loc.city,loc.latitude,loc.longitude,loc.accuracy_km))
                    sid = cur.lastrowid
                    new += 1
                next_active[c.key] = sid, first
                enriched.append(replace(c, first_seen=first))
            for key, (sid, _) in self.active.items():
                if key not in next_active:
                    self.db.execute("UPDATE sessions SET active=0 WHERE id=?", (sid,))
            unique = len({c.remote_ip for c in connections if c.remote_ip})
            self.db.execute("INSERT OR REPLACE INTO samples VALUES (?,?,?,?)", (timestamp,len(connections),new,unique))
        self.active = next_active
        return enriched, new

    def end_observation(self):
        with self.db:
            self.db.execute("UPDATE sessions SET active=0 WHERE active=1")
        self.active.clear()

    SORT_COLUMNS={'last_seen','first_seen','process','pid','remote_ip','remote_port','protocol','country'}

    def history(self, search="", since="", until="", app="", limit=1000, offset=0,
                pid=None, protocol="", ip="", sort="last_seen", descending=True):
        clause,params=search_clause(search,since,until,app,pid,protocol,ip)
        if sort not in self.SORT_COLUMNS: raise ValueError('Недопустимая сортировка')
        query="SELECT * FROM sessions"+clause+" ORDER BY "+sort+(" DESC" if descending else " ASC")+", id DESC LIMIT ? OFFSET ?"
        return [dict(r) for r in self.db.execute(query,[*params,min(max(limit,1),5000),max(0,offset)])]

    def history_count(self, **query):
        keys={k:v for k,v in query.items() if k in {'search','since','until','app','pid','protocol','ip'}}
        clause,params=search_clause(**keys)
        return self.db.execute('SELECT COUNT(*) FROM sessions'+clause,params).fetchone()[0]

    def export_rows(self, **query):
        keys={k:v for k,v in query.items() if k in {'search','since','until','app','pid','protocol','ip'}}
        clause,params=search_clause(**keys)
        cursor=self.db.execute('SELECT * FROM sessions'+clause+' ORDER BY last_seen DESC,id DESC',params)
        for r in cursor: yield dict(r)

    def analytics(self, seconds=900, now=None):
        now=now or datetime.now(timezone.utc)
        since=(now-timedelta(seconds=seconds)).isoformat(timespec='milliseconds') if seconds else ''
        count=self.db.execute('SELECT COUNT(*) FROM samples WHERE time >= ?',(since,)).fetchone()[0]
        stride=max(1,(count+359)//360)
        samples=[dict(r) for r in self.db.execute("""WITH numbered AS
            (SELECT *,row_number() OVER (ORDER BY time) AS n FROM samples WHERE time >= ?)
            SELECT time,total,new,unique_ips FROM numbered WHERE (n-1) % ? = 0 OR n = ? ORDER BY time""",(since,stride,count))]
        args=(since,)
        apps=dict(self.db.execute('SELECT process,COUNT(*) FROM sessions WHERE last_seen >= ? GROUP BY process ORDER BY COUNT(*) DESC LIMIT 10',args))
        protocols=dict(self.db.execute('SELECT protocol,COUNT(*) FROM sessions WHERE last_seen >= ? GROUP BY protocol',args))
        countries=dict(self.db.execute("SELECT CASE WHEN country='' THEN 'Не определена' ELSE country END,COUNT(DISTINCT remote_ip) FROM sessions WHERE last_seen >= ? AND IS_PUBLIC(remote_ip) GROUP BY country ORDER BY COUNT(DISTINCT remote_ip) DESC LIMIT 10",args))
        new_ips=self.db.execute('SELECT COUNT(*) FROM (SELECT remote_ip,MIN(first_seen) AS first FROM sessions WHERE IS_PUBLIC(remote_ip) GROUP BY remote_ip HAVING first >= ?)',args).fetchone()[0]
        unique=self.db.execute('SELECT COUNT(DISTINCT remote_ip) FROM sessions WHERE last_seen >= ? AND remote_ip != ?',(since,'' )).fetchone()[0]
        return {'seconds':seconds,'samples':samples,'apps':apps,'protocols':protocols,'countries':countries,
                'new_ips':new_ips,'unique_ips':unique,'sample_count':count,'available':bool(count)}

    def recent_map(self, limit=1000):
        return [dict(r) for r in self.db.execute("""SELECT * FROM sessions WHERE latitude IS NOT NULL
            AND longitude IS NOT NULL ORDER BY last_seen DESC LIMIT ?""", (limit,))]

    def samples(self, limit=180):
        return [dict(r) for r in reversed(list(self.db.execute("SELECT * FROM samples ORDER BY time DESC LIMIT ?",(limit,))))]

    def prune(self, days, now=None):
        now = now or datetime.now(timezone.utc)
        cutoff = (now - timedelta(days=days)).isoformat(timespec="milliseconds")
        with self.db:
            self.db.execute("DELETE FROM sessions WHERE active=0 AND last_seen < ?", (cutoff,))
            self.db.execute("DELETE FROM samples WHERE time < ?", (cutoff,))
            self.db.execute("DELETE FROM diagnostics WHERE time < ?", (cutoff,))
        # Release unused pages without long blocking VACUUM during monitoring.
        self.db.execute("PRAGMA wal_checkpoint(PASSIVE)")

    def clear(self):
        with self.db:
            for table in ("sessions", "samples", "diagnostics"):
                self.db.execute(f"DELETE FROM {table}")
        self.active.clear()
        self.db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        self.db.execute("VACUUM")

    def add_diagnostic(self, result):
        with self.db:
            self.db.execute("INSERT INTO diagnostics(time,host,port,result) VALUES (?,?,?,?)",
                            (result["time"],result["host"],result["port"],json.dumps(result,ensure_ascii=False)))

    def diagnostic_history(self):
        return [json.loads(r[0]) for r in self.db.execute("SELECT result FROM diagnostics ORDER BY id DESC LIMIT 50")]

    def close(self):
        self.end_observation()
        self.db.close()
