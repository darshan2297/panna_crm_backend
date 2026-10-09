"""
Panna Biryani CRM — one-file launcher.

    python manage.py                # start the API + Socket.IO on :8000
    python manage.py run --reload   # same, with auto-reload
    python manage.py run --port 8080
    python manage.py migrate        # apply pending Alembic migrations
    python manage.py check          # dependency + schema health check

Socket.IO note: the server MUST be started as `app.main:application`, never
`app.main:app`. `app` is the bare FastAPI instance and has no realtime
transport mounted — live orders / shop status would silently 404 on
`/socket.io/`. `application` is the socketio.ASGIApp wrapper around it.

Run this file from anywhere; it fixes up sys.path and the working directory
itself (the app resolves `media/` and the SQLite file relative to cwd).
"""

from __future__ import annotations

import argparse
import os
import socket
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# The app reads .env and stores ./panna_crm.db + ./media relative to cwd, so pin
# both to the project root. Without this, `python ../manage.py` writes a stray
# SQLite file and fails to find .env.
os.chdir(BASE_DIR)
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

DEFAULT_HOST = "0.0.0.0"  # noqa: S104 - dev server; CRM and website run on the LAN
DEFAULT_PORT = 8000
ASGI_TARGET = "app.main:application"  # NOT app.main:app — see module docstring


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _port_in_use(host: str, port: int) -> bool:
    probe = "127.0.0.1" if host in ("0.0.0.0", "::") else host  # noqa: S104
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((probe, port)) == 0


def _banner(host: str, port: int, reload_enabled: bool) -> str:
    shown = "127.0.0.1" if host in ("0.0.0.0", "::") else host  # noqa: S104
    mode = "reload" if reload_enabled else "single process"
    width = 50
    edge = f"  +{'-' * (width + 2)}+"

    def row(text: str = "") -> str:
        return f"  | {text.ljust(width)} |"

    lines = [
        edge,
        row("Panna Biryani CRM API"),
        edge,
        row(f"mode       {mode}"),
        row(f"REST API   http://{shown}:{port}/api/v1"),
        row(f"Socket.IO  ws://{shown}:{port}/socket.io/"),
        row(f"Docs       http://{shown}:{port}/docs"),
        edge,
        row("Ctrl+C to stop"),
        edge,
    ]
    return "\n" + "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- #
# commands
# --------------------------------------------------------------------------- #
def cmd_run(args: argparse.Namespace) -> int:
    host, port = args.host, args.port

    if _port_in_use(host, port):
        print(f"\n[ERROR] Port {port} is already in use.", file=sys.stderr)
        print("        Close the other process, or run: python manage.py run --port 8080\n", file=sys.stderr)
        return 1

    try:
        import uvicorn
    except ImportError:
        print("\n[ERROR] uvicorn is not installed. Run: pip install -r requirements.txt\n", file=sys.stderr)
        return 1

    # Fail fast with a clear message instead of a wall of ImportErrors.
    try:
        import app.main  # noqa: F401
    except Exception as exc:  # pragma: no cover - developer convenience
        print(f"\n[ERROR] Could not import the application: {exc}", file=sys.stderr)
        print("        Did you install dependencies? pip install -r requirements.txt\n", file=sys.stderr)
        return 1

    print(_banner(host, port, args.reload))

    uvicorn.run(
        ASGI_TARGET,
        host=host,
        port=port,
        reload=args.reload,
        log_level=args.log_level,
        # Multiple workers are deliberately not offered: socketio.ASGIApp keeps
        # per-process state, so broadcasts would only reach clients attached to
        # the worker that raised them.
        workers=1,
    )
    return 0


def cmd_migrate(args: argparse.Namespace) -> int:  # noqa: ARG001
    try:
        from alembic import command
        from alembic.config import Config
    except ImportError:
        print("\n[ERROR] alembic is not installed. Run: pip install -r requirements.txt\n", file=sys.stderr)
        return 1

    cfg = Config(str(BASE_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BASE_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", _database_url())

    print("Applying migrations...")
    command.upgrade(cfg, args.revision)
    return 0


def cmd_check(args: argparse.Namespace) -> int:  # noqa: ARG001
    ok = True

    print("Dependencies:")
    for module in ("fastapi", "uvicorn", "sqlalchemy", "socketio", "alembic"):
        try:
            mod = __import__(module)
            version = getattr(mod, "__version__", "installed")
            print(f"  [ok]   {module:<12} {version}")
        except ImportError:
            print(f"  [MISS] {module}")
            ok = False

    print("\nDatabase:")
    try:
        from app.core.database import Base, engine
        import app.models  # noqa: F401  (registers every model on Base)

        Base.metadata.create_all(bind=engine)
        print(f"  [ok]   reachable — {_database_url()}")
    except Exception as exc:
        print(f"  [FAIL] {_database_url()}\n         {exc}")
        ok = False

    print("\nPending migrations:")
    try:
        from alembic.config import Config
        from alembic.runtime.migration import MigrationContext
        from alembic.script import ScriptDirectory
        from sqlalchemy import create_engine

        cfg = Config(str(BASE_DIR / "alembic.ini"))
        cfg.set_main_option("script_location", str(BASE_DIR / "alembic"))
        cfg.set_main_option("sqlalchemy.url", _database_url())

        head = ScriptDirectory.from_config(cfg).get_current_head()
        with create_engine(_database_url()).connect() as conn:
            current = MigrationContext.configure(conn).get_current_revision()
        if current == head:
            print(f"  [ok]   database at {head or 'base'}")
        else:
            print(f"  [WARN] database at {current}, code expects {head}")
            print("         Run: python manage.py migrate")
    except Exception as exc:
        print(f"  [skip] {exc}")

    print("\n" + ("All good." if ok else "Problems found — see [MISS]/[FAIL] above."))
    return 0 if ok else 1


def _database_url() -> str:
    from app.core.config import settings

    return settings.DATABASE_URL


# --------------------------------------------------------------------------- #
# cli
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="manage.py",
        description="Panna Biryani CRM launcher (API + Socket.IO).",
    )
    sub = parser.add_subparsers(dest="command")

    run = sub.add_parser("run", help="start the API server (default)")
    run.add_argument("--host", default=DEFAULT_HOST, help=f"default: {DEFAULT_HOST}")
    run.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"default: {DEFAULT_PORT}")
    run.add_argument("--reload", action="store_true", help="auto-reload on code changes")
    run.add_argument(
        "--log-level",
        default="info",
        choices=["critical", "error", "warning", "info", "debug", "trace"],
    )
    run.set_defaults(func=cmd_run)

    migrate = sub.add_parser("migrate", help="apply pending Alembic migrations")
    migrate.add_argument("--revision", default="head", help="default: head")
    migrate.set_defaults(func=cmd_migrate)

    check = sub.add_parser("check", help="verify dependencies and database")
    check.set_defaults(func=cmd_check)

    return parser


def main() -> int:
    parser = build_parser()
    # Bare `python manage.py` behaves like `python manage.py run`.
    argv = sys.argv[1:] or ["run"]
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 1
    try:
        return int(args.func(args))
    except KeyboardInterrupt:
        print("\nStopped.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
