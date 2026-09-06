"""SSH al CE Cisco por OPE. Nunca persiste passwords."""

from __future__ import annotations

import getpass
import os

from relevar.errors import RelevarError


def credentials(user: str) -> str:
    env = os.environ.get("SSH_PASS") or os.environ.get("RELEVAR_SSH_PASS")
    if env:
        return env
    try:
        return getpass.getpass(f"password SSH {user}: ")
    except (EOFError, KeyboardInterrupt) as exc:
        raise RelevarError("no se obtuvo password SSH", code=2) from exc


def connect(host: str, user: str, password: str, timeout: int = 30):
    try:
        from netmiko import ConnectHandler
    except ImportError as exc:
        raise RelevarError(
            "hace falta netmiko: pip install -e '.[relevar]'",
            code=2,
        ) from exc
    try:
        conn = ConnectHandler(
            device_type="cisco_ios",
            host=host,
            username=user,
            password=password,
            timeout=timeout,
            conn_timeout=timeout,
            auth_timeout=timeout,
            banner_timeout=timeout,
        )
        conn.find_prompt()
        return conn
    except Exception as exc:
        raise RelevarError(f"SSH falló a {user}@{host}: {exc}", code=2) from exc


def send(conn, command: str) -> str:
    try:
        return conn.send_command(command, read_timeout=60) or ""
    except Exception as exc:
        raise RelevarError(f"comando falló ({command}): {exc}", code=2) from exc


def close(conn) -> None:
    try:
        conn.disconnect()
    except Exception:
        pass
