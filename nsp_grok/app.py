"""Interactive NSP-Grok shell — login, then a Grok-like REPL."""

from __future__ import annotations

import argparse
import getpass
import os
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.formatted_text import HTML, StyleAndTextTuples
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.text import Text

from nsp_grok import PRODUCT, RELEASE
from nsp_grok.auth import authenticate, hash_password
from nsp_grok.commands import DEFAULT_NSP_HOST, Ctx, Outcome, dispatch
from nsp_grok.completer import NspCompleter
from nsp_grok.lab import Store
from nsp_grok.models import User
from nsp_grok.nsp_api import (
    REQUEST_TIMEOUT_S,
    DebugSink,
    NspApiError,
    NspClient,
    UserCancelled,
)
from nsp_grok.render import SEV_STYLE, banner
from nsp_grok.tree import build_tree, cli_prompt, pwd

console = Console()

HISTORY_FILE = Path.home() / ".nsp-grok-history"

PROMPT_STYLE = Style.from_dict(
    {
        "prompt": "ansicyan bold",
        "path": "ansibrightblack",
        "user": "ansigreen",
        "host": "ansicyan",
        "bottom-toolbar": "noreverse bg:#0b1f33 #c8d6e5",
        "bt-key": "bold #6ee7ff",
        "bt-bad": "bold #ff6b6b",
        "bt-ok": "#7dcea0",
    }
)


def _toolbar(ctx: Ctx) -> StyleAndTextTuples:
    visible = ctx.store.visible_nes(ctx.user)
    alarms = [a for a in ctx.store.alarms if not a.cleared and a.ne in visible]
    crit = sum(1 for a in alarms if a.severity == "critical")
    major = sum(1 for a in alarms if a.severity == "major")
    alarm_style = "class:bt-bad" if crit else ("class:bt-key" if major else "class:bt-ok")
    alarm_txt = f"{crit} crit · {major} maj"
    return [
        ("class:bt-key", f" {ctx.user.username} "),
        ("class:bottom-toolbar", "│"),
        ("class:bottom-toolbar", f" {ctx.user.role} "),
        ("class:bottom-toolbar", "│"),
        ("class:bottom-toolbar", f" {pwd(ctx.cwd)} "),
        ("class:bottom-toolbar", "│"),
        (alarm_style, f" {alarm_txt} "),
        ("class:bottom-toolbar", "│"),
        ("class:bottom-toolbar", f" {len(visible)} NEs "),
        ("class:bottom-toolbar", "│"),
        ("class:bt-key", f" NSP {RELEASE} "),
    ]


def _prompt(ctx: Ctx) -> HTML:
    host = ctx.nsp_host
    user = ctx.user.username
    if not ctx.cwd:
        return HTML(f"<user>{user}</user><prompt>@</prompt><host>{host}</host><prompt>&gt; </prompt>")
    path = "&gt;".join(ctx.cwd)
    return HTML(
        f"<user>{user}</user><prompt>@</prompt><host>{host}</host>"
        f"<prompt>&gt;</prompt><path>{path}</path><prompt>&gt; </prompt>"
    )


def _debug_print(text: str) -> None:
    console.print(Text(text, style="yellow"))


def _connect_nsp(
    host: str, username: str, password: str, debug: bool, offline: bool
) -> tuple[NspClient | None, bool, str]:
    if offline:
        return None, False, "offline: inventario local (lab)"
    sink = DebugSink(enabled=debug, printer=_debug_print)
    client = NspClient(host, username, password, debug=sink, timeout=REQUEST_TIMEOUT_S)
    try:
        client.login()
    except UserCancelled:
        raise
    except KeyboardInterrupt as exc:
        raise UserCancelled("Cancelado con Ctrl-C.") from exc
    except NspApiError as exc:
        return client, False, f"NSP no alcanzó ({exc}); usando lab local"
    return client, True, f"conectado a https://{host}"


def _user_for_session(store: Store, username: str, password: str, live: bool) -> tuple[User | None, str]:
    if live:
        existing = store.users.get(username.strip().lower())
        if existing is not None:
            if existing.state != "active":
                return None, "Account is suspended."
            existing.last_login = datetime.now(timezone.utc)
            return existing, ""
        digest, salt = hash_password(password)
        user = User(
            username=username.strip().lower(),
            password_hash=digest,
            salt=salt,
            group="nsp",
            role="operator",
            display_name=username,
            access="execute",
        )
        store.users[user.username] = user
        return user, ""
    return authenticate(store.users, username, password)


def login_interactive(
    store: Store, host: str, debug: bool, offline: bool
) -> tuple[User | None, NspClient | None, bool]:
    console.print(banner())
    console.print(
        Text.from_markup(
            "[dim]Usuario NSP (OAuth2 contra --host). Lab local: [bold]admin[/] / [bold]Nokia1234![/][/]\n"
        )
    )
    for _ in range(5):
        try:
            username = console.input("[cyan]user[/] › ").strip()
            if not username:
                continue
            password = getpass.getpass("password › ")
        except EOFError as exc:
            raise UserCancelled("Login cancelado (EOF).") from exc
        except KeyboardInterrupt as exc:
            raise UserCancelled("Login cancelado con Ctrl-C.") from exc
        client, live, status = _connect_nsp(host, username, password, debug, offline)
        console.print(Text(status, style="green" if live else "yellow"))
        user, err = _user_for_session(store, username, password, live)
        if user:
            return user, client if live else None, live
        console.print(Text(err, style="bold red"))
    console.print("[red]too many failed login attempts[/]")
    return None, None, False


def login_direct(
    store: Store, username: str, password: str, host: str, debug: bool, offline: bool
) -> tuple[User | None, NspClient | None, bool]:
    client, live, status = _connect_nsp(host, username, password, debug, offline)
    console.print(Text(status, style="green" if live else "yellow"))
    user, err = _user_for_session(store, username, password, live)
    if user is None:
        console.print(Text(err, style="bold red"))
        return None, None, False
    return user, client if live else None, live


def session_intro(ctx: Ctx) -> None:
    visible = ctx.store.visible_nes(ctx.user)
    alarms = [a for a in ctx.store.alarms if not a.cleared and a.ne in visible]
    crit = sum(1 for a in alarms if a.severity == "critical")
    console.print()
    console.print(
        Text.assemble(
            ("session  ", "dim"),
            (ctx.session_id, "bold cyan"),
            ("  ·  ", "dim"),
            (ctx.user.username, "bold"),
            ("  ·  ", "dim"),
            (ctx.user.role, ""),
            ("  ·  span ", "dim"),
            (", ".join(ctx.user.span) or "ALL", "cyan"),
        )
    )
    customers = ctx.store.visible_customers(ctx.user)
    services = ctx.store.visible_services(ctx.user)
    console.print(
        Text.assemble(
            (f"{len(customers)} customers", ""),
            ("  ·  ", "dim"),
            (f"{len(services)} services (VPRN/VPLS/Epipe)", ""),
            ("  ·  ", "dim"),
            (f"{len(visible)} NEs", ""),
            ("  ·  ", "dim"),
            (f"{len(alarms)} alarms", SEV_STYLE["critical"] if crit else ""),
        )
    )
    backend = "NSP live" if ctx.live else "lab local"
    console.print(
        Text.from_markup(
            f"[dim]Prompt [bold cyan]{ctx.user.username}@{ctx.nsp_host}>[/]  "
            f"backend [bold]{backend}[/].  "
            "type [bold cyan]customers[/] then [bold cyan]12[/].  "
            "[bold cyan]--debug[/] imprime cada HTTP request.[/]\n"
        )
    )


def apply_outcome(out: Outcome) -> bool:
    """Return False if the session should end."""
    if out.error:
        console.print(Text(out.error, style="bold red"))
    if out.clear:
        console.clear()
        console.print(banner())
    if out.renderable is not None:
        console.print(out.renderable)
    return not out.quit


def run_repl(ctx: Ctx) -> int:
    history: FileHistory | None = None
    try:
        HISTORY_FILE.touch(exist_ok=True)
        history = FileHistory(str(HISTORY_FILE))
    except OSError:
        history = None
    session: PromptSession = PromptSession(
        history=history,
        auto_suggest=AutoSuggestFromHistory(),
        completer=NspCompleter(ctx),
        complete_while_typing=True,
        style=PROMPT_STYLE,
        bottom_toolbar=lambda: _toolbar(ctx),
    )
    while True:
        try:
            line = session.prompt(_prompt(ctx))
            out = dispatch(ctx, line)
            if not apply_outcome(out):
                if out.error:
                    console.print("[dim]Cerrando.[/]")
                else:
                    console.print("[dim]Sesión cerrada.[/]")
                return 1 if out.error else 0
        except EOFError:
            console.print("\nSesión cerrada.")
            return 0
        except UserCancelled:
            raise
        except KeyboardInterrupt as exc:
            raise UserCancelled("Cancelado con Ctrl-C.") from exc
        except NspApiError as exc:
            console.print(Text(str(exc), style="bold red"))
            console.print("[dim]Cerrando.[/]")
            return 1
        except Exception as exc:
            console.print(
                Text(f"Error inesperado ({type(exc).__name__}): {exc}", style="bold red")
            )
            console.print("[dim]Cerrando.[/]")
            return 1
    return 0


def run_batch(ctx: Ctx, commands: list[str]) -> int:
    rc = 0
    for line in commands:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        console.print(Text(f"{cli_prompt(ctx.user.username, ctx.nsp_host, ctx.cwd)}{line}", style="dim"))
        try:
            out = dispatch(ctx, line)
        except UserCancelled:
            raise
        except KeyboardInterrupt as exc:
            raise UserCancelled("Cancelado con Ctrl-C.") from exc
        except NspApiError as exc:
            console.print(Text(str(exc), style="bold red"))
            console.print("[dim]Cerrando.[/]")
            return 1
        except Exception as exc:
            console.print(
                Text(f"Error inesperado ({type(exc).__name__}): {exc}", style="bold red")
            )
            console.print("[dim]Cerrando.[/]")
            return 1
        apply_outcome(out)
        if out.error:
            rc = 1
        if out.quit:
            if out.error:
                console.print("[dim]Cerrando.[/]")
            break
    return rc


def build_ctx(
    store: Store,
    user: User,
    nsp_host: str | None = None,
    debug: bool = False,
    live: bool = False,
    client: NspClient | None = None,
) -> Ctx:
    return Ctx(
        store=store,
        user=user,
        cwd=[],
        root=build_tree(store, user),
        session_id=secrets.token_hex(4),
        started=datetime.now(timezone.utc),
        nsp_host=nsp_host or os.environ.get("NSP_HOST", DEFAULT_NSP_HOST),
        debug=debug,
        live=live,
        client=client,
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="nsp-grok",
        description=f"{PRODUCT} {RELEASE} — NFM-P classic management shell",
    )
    p.add_argument("--user", "-u", help="username (skip interactive login)")
    p.add_argument("--password", "-p", help="password (or NSP_GROK_PASSWORD env)")
    p.add_argument(
        "--host",
        default=os.environ.get("NSP_HOST", DEFAULT_NSP_HOST),
        help="NSP IP/host shown in the prompt (user@host>)",
    )
    p.add_argument(
        "--batch",
        "-c",
        action="append",
        default=[],
        help="run a command non-interactively (repeatable)",
    )
    p.add_argument(
        "--script",
        help="file with one command per line",
    )
    p.add_argument(
        "--debug",
        action="store_true",
        help="imprime cada HTTP request (método, URL, headers redactados, body)",
    )
    p.add_argument(
        "--offline",
        action="store_true",
        help="no contactar el NSP; usar inventario local",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        return _main(argv)
    except UserCancelled as exc:
        console.print(f"[yellow]{exc} Cerrando.[/]")
        return 130
    except KeyboardInterrupt:
        console.print("[yellow]Cancelado con Ctrl-C. Cerrando.[/]")
        return 130
    except NspApiError as exc:
        console.print(f"[red]Error de red/NSP: {exc}[/]")
        console.print("[dim]Cerrando.[/]")
        return 1
    except Exception as exc:
        console.print(f"[red]Error inesperado ({type(exc).__name__}): {exc}[/]")
        console.print("[dim]Cerrando.[/]")
        return 1


def _main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    store = Store()
    password = args.password or os.environ.get("NSP_GROK_PASSWORD", "")
    if args.user:
        user, client, live = login_direct(
            store, args.user, password, args.host, args.debug, args.offline
        )
        if user is None:
            return 2
    else:
        user, client, live = login_interactive(store, args.host, args.debug, args.offline)
        if user is None:
            return 2

    ctx = build_ctx(
        store, user, nsp_host=args.host, debug=args.debug, live=live, client=client
    )
    batch: list[str] = list(args.batch)
    if args.script:
        try:
            batch.extend(Path(args.script).read_text(encoding="utf-8").splitlines())
        except OSError as exc:
            console.print(f"[red]No se pudo leer {args.script}: {exc}[/]")
            console.print("[dim]Cerrando.[/]")
            return 1

    if batch or not sys.stdin.isatty():
        if not batch and not sys.stdin.isatty():
            batch = sys.stdin.read().splitlines()
        if not args.user:
            console.print(banner())
        session_intro(ctx)
        return run_batch(ctx, batch)

    console.clear()
    console.print(banner())
    session_intro(ctx)
    return run_repl(ctx)


if __name__ == "__main__":
    raise SystemExit(main())
