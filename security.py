"""SQLite identities and request-time role enforcement for TimeBeacon."""

import base64
import hashlib
import hmac
import json
import secrets
import time
from urllib.parse import urlsplit
from fastapi import HTTPException

PERMISSIONS = {
    "dashboard.view": "Dashboard Access (View)",
    "server.view": "Server Status (View)",
    "server.history": "Server Status History (View)",
    "time.view": "Time Server Status (View)",
    "time.history": "Time Server Status History (View)",
    "clocks.view": "World Clocks (View)",
    "clocks.amend": "World Clocks (Amend)",
    "clients.summary": "Time Clients Summary (View)",
    "clients.view": "Time Clients (View)",
    "api.view": "API Access (View)",
    "admin": "Administration",
}
USER_PERMISSIONS = [
    "dashboard.view",
    "server.view",
    "server.history",
    "time.view",
    "time.history",
    "clocks.view",
    "clients.summary",
]


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def password_hash(password):
    salt = secrets.token_hex(16)
    return (
        salt
        + ":"
        + hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 600000).hex()
    )


def password_ok(password, stored):
    salt, expected = stored.split(":")
    return hmac.compare_digest(
        hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 600000).hex(),
        expected,
    )


class IdentityStore:
    def __init__(self, monitor):
        self.monitor = monitor

    def initialise(self):
        with self.monitor.connect() as db:
            db.executescript(
                """CREATE TABLE IF NOT EXISTS roles(name TEXT PRIMARY KEY,permissions TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,username TEXT UNIQUE NOT NULL,password TEXT NOT NULL,roles TEXT NOT NULL,enabled INTEGER NOT NULL DEFAULT 1,clocks TEXT NOT NULL,version INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user_id INTEGER NOT NULL,expires INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS api_keys(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL,name TEXT NOT NULL,token TEXT UNIQUE NOT NULL,created INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS login_attempts(address TEXT NOT NULL,stamp INTEGER NOT NULL);"""
            )
            db.execute("BEGIN IMMEDIATE")
            db.execute(
                "INSERT OR IGNORE INTO roles VALUES (?,?)",
                ("Administrator", json.dumps(list(PERMISSIONS))),
            )
            db.execute(
                "INSERT OR IGNORE INTO roles VALUES (?,?)",
                ("User", json.dumps(USER_PERMISSIONS)),
            )
            if not db.execute("SELECT 1 FROM users LIMIT 1").fetchone():
                clocks = self.monitor.get_settings()["settings"].get("clocks", [])
                db.execute(
                    "INSERT INTO users(username,password,roles,clocks) VALUES (?,?,?,?)",
                    (
                        "admin",
                        password_hash("admin"),
                        '["Administrator"]',
                        json.dumps(clocks),
                    ),
                )
            settings_row = db.execute(
                "SELECT payload FROM settings WHERE id=1"
            ).fetchone()
            settings = json.loads(settings_row[0])
            if "clocks" in settings:
                settings.pop("clocks")
                db.execute(
                    "UPDATE settings SET payload=?,version=version+1 WHERE id=1",
                    (json.dumps(settings),),
                )

    def identity(self, db, user_id):
        row = db.execute(
            "SELECT id,username,roles,enabled,clocks,version FROM users WHERE id=?",
            (user_id,),
        ).fetchone()
        if not row or not row[3]:
            raise HTTPException(401, "Account unavailable")
        roles = json.loads(row[2])
        permissions = set()
        for role in roles:
            match = db.execute(
                "SELECT permissions FROM roles WHERE name=?", (role,)
            ).fetchone()
            if match:
                permissions.update(json.loads(match[0]))
        return {
            "id": row[0],
            "username": row[1],
            "roles": roles,
            "permissions": sorted(permissions),
            "clocks": json.loads(row[4]),
            "version": row[5],
        }

    def credential(self, username, password, address):
        now = int(time.time())
        with self.monitor.connect() as db:
            db.execute("DELETE FROM login_attempts WHERE stamp<?", (now - 300,))
            if (
                db.execute(
                    "SELECT COUNT(*) FROM login_attempts WHERE address=?", (address,)
                ).fetchone()[0]
                >= 10
            ):
                raise HTTPException(
                    429, "Too many attempts. Try again in five minutes."
                )
            db.execute("INSERT INTO login_attempts VALUES (?,?)", (address, now))
        with self.monitor.connect() as db:
            row = db.execute(
                "SELECT id,password FROM users WHERE username=?", (username,)
            ).fetchone()
            valid = password_ok(password, row[1] if row else "0" * 32 + ":" + "0" * 64)
            if not row or not valid:
                raise HTTPException(401, "Invalid credentials")
            user = self.identity(db, row[0])
            db.execute("DELETE FROM login_attempts WHERE address=?", (address,))
            return user

    def authenticate(self, request, api=False):
        authorization = request.headers.get("authorization", "")
        user = None
        if authorization.startswith("Basic "):
            try:
                username, password = (
                    base64.b64decode(authorization[6:], validate=True)
                    .decode()
                    .split(":", 1)
                )
            except Exception:
                raise HTTPException(401, "Invalid credentials")
            user = self.credential(
                username, password, request.client.host if request.client else "unknown"
            )
        elif authorization.startswith("Bearer "):
            with self.monitor.connect() as db:
                row = db.execute(
                    "SELECT user_id FROM api_keys WHERE token=?",
                    (digest(authorization[7:]),),
                ).fetchone()
                if row:
                    user = self.identity(db, row[0])
        else:
            with self.monitor.connect() as db:
                row = db.execute(
                    "SELECT user_id FROM sessions WHERE token=? AND expires>?",
                    (
                        digest(request.cookies.get("timebeacon_session", "")),
                        time.time(),
                    ),
                ).fetchone()
                if row:
                    user = self.identity(db, row[0])
        if user is None:
            raise HTTPException(
                401,
                "Authentication required",
                headers={"WWW-Authenticate": 'Basic realm="TimeBeacon"'},
            )
        if api or authorization:
            self.require(user, "api.view")
        return user

    @staticmethod
    def require(user, *permissions):
        if any(p not in user["permissions"] for p in permissions):
            raise HTTPException(403, "Permission denied")

    @staticmethod
    def same_origin(request):
        if (
            urlsplit(request.headers.get("origin", "")).netloc
            != request.headers.get("host")
            or request.headers.get("sec-fetch-site") == "cross-site"
        ):
            raise HTTPException(403, "Same-origin request required")

    def mutation(self, request):
        if not request.headers.get("authorization"):
            self.same_origin(request)

    def save_clocks(self, user, clocks, version=None):
        with self.monitor.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT version FROM users WHERE id=?", (user["id"],)
            ).fetchone()
            if version is not None and row[0] != version:
                raise HTTPException(409, "Settings changed. Reload and retry.")
            db.execute(
                "UPDATE users SET clocks=?,version=version+1 WHERE id=?",
                (json.dumps(clocks), user["id"]),
            )
            return self.identity(db, user["id"])

    def keep_admin(self, db):
        for row in db.execute("SELECT id FROM users WHERE enabled=1"):
            if "admin" in self.identity(db, row[0])["permissions"]:
                return
        raise HTTPException(422, "At least one enabled administrator is required")
