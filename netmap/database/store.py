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


def search_clause(search="", since="", until="", app=""):
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
    return (" WHERE " + " AND ".join(clauses) if clauses else ""), params


class HistoryStore:
    def __init__(self, path: Path | str):
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, timeout=5)
        self.db.row_factory = sqlite3.Row
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

    def history(self, search="", since="", until="", app="", limit=1000):
        clause, params = search_clause(search, since, until, app)
        query = "SELECT * FROM sessions" + clause + " ORDER BY last_seen DESC, id DESC LIMIT ?"
        return [dict(r) for r in self.db.execute(query, [*params, min(max(limit,1),5000)])]

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
