"""Command dispatch for the NSP-Grok shell."""

from __future__ import annotations

import shlex
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from rich.console import Group, RenderableType
from rich.text import Text

from nsp_grok import RELEASE
from nsp_grok.auth import can, change_password
from nsp_grok.lab import Store
from nsp_grok.models import Lsp, Task, User
from nsp_grok.nsp_api import NspApiError, NspClient, UserCancelled
from nsp_grok import render
from nsp_grok.tree import Node, build_tree, cli_prompt, pwd, resolve

DEFAULT_NSP_HOST = "172.24.80.28"


SLASH = {
    "help": "esta ayuda",
    "customers": "lista de clientes (subscr.Subscriber)",
    "customer": "muestra un cliente",
    "services": "VPRN / VPLS / Epipe",
    "status": "resumen de sesión",
    "whoami": "usuario, rol, span of control",
    "ne": "elementos de red",
    "mpls": "objetos MPLS",
    "alarms": "fallas",
    "stats": "estadísticas de performance",
    "topology": "topología ASCII",
    "tasks": "gestor de tareas",
    "users": "usuarios locales (admin)",
    "resync": "resincroniza NE(s)",
    "passwd": "cambia la contraseña",
    "clear": "limpia la pantalla",
    "quit": "cierra la sesión",
    "logout": "cierra la sesión",
    "debug": "imprime las peticiones HTTP",
}


@dataclass
class Ctx:
    store: Store
    user: User
    cwd: list[str]
    root: Node
    session_id: str
    started: datetime
    nsp_host: str = DEFAULT_NSP_HOST
    theme: str = "dark"
    last_task: int = 0
    debug: bool = False
    live: bool = False
    client: NspClient | None = None

    def node(self) -> Node:
        found = resolve(self.root, self.cwd, ".")
        assert found is not None
        return found[1]

    def rebuild(self) -> None:
        self.root = build_tree(self.store, self.user)
        found = resolve(self.root, [], pwd(self.cwd) if self.cwd else "/")
        if found is None:
            self.cwd = []
        else:
            self.cwd = found[0]


@dataclass
class Outcome:
    renderable: RenderableType | None = None
    clear: bool = False
    quit: bool = False
    error: str = ""


def _handlers():
    return {
        "ls": _ls,
        "?": _ls,
        "cd": _cd,
        "pwd": _pwd,
        "tree": _tree,
        "show": _show,
        "info": _show,
        "cat": _show,
        "find": _find,
        "help": lambda c, a: Outcome(renderable=render.help_text()),
        "mpls": _mpls,
        "alarm": _alarm,
        "alarms": _alarm,
        "ne": _ne,
        "customer": _customer,
        "customers": _customer,
        "service": _service,
        "services": _service,
        "stats": _stats,
        "resync": _resync,
        "topology": lambda c, a: Outcome(renderable=render.topology_ascii()),
        "clear": lambda c, a: Outcome(clear=True),
        "quit": lambda c, a: Outcome(quit=True),
        "logout": lambda c, a: Outcome(quit=True),
        "exit": _exit_ctx,
        "top": lambda c, a: _exit_ctx(c, ["all"]),
        "whoami": _whoami,
        "status": _status,
        "passwd": _passwd,
        "users": _users,
        "tasks": _tasks,
        "debug": _debug,
    }


def _child_name(node: Node, token: str) -> str | None:
    raw = token.rstrip("/")
    if raw in node.children:
        return raw
    lower = {name.lower(): name for name in node.children}
    return lower.get(raw.lower())


def _walk_fire(ctx: Ctx, parts: list[str]) -> int:
    """Consume nested object names (Python Fire / SR OS context). Return index of first non-child."""
    handlers = _handlers()
    i = 0
    while i < len(parts):
        node = ctx.node()
        child = _child_name(node, parts[i])
        if child is None:
            break
        token = parts[i].rstrip("/").lower()
        if i == 0 and token in handlers and i + 1 < len(parts):
            nxt = parts[i + 1].rstrip("/")
            next_is_child = _child_name(node.children[child], nxt) is not None
            if not next_is_child:
                break
        ctx.cwd.append(child)
        i += 1
    return i


def _inspect(ctx: Ctx) -> Outcome:
    node = ctx.node()
    if node.payload is not None:
        shown = render.show_object(node.payload, node.kind)
        if node.children:
            return Outcome(renderable=Group(shown, render.ls_table(node, ctx.cwd)))
        return Outcome(renderable=shown)
    return _ls(ctx, [])


def _debug(ctx: Ctx, args: list[str]) -> Outcome:
    if args and args[0].lower() in ("on", "1", "true"):
        ctx.debug = True
    elif args and args[0].lower() in ("off", "0", "false"):
        ctx.debug = False
    else:
        ctx.debug = not ctx.debug
    if ctx.client is not None:
        ctx.client.debug.enabled = ctx.debug
    state = "on" if ctx.debug else "off"
    live = "NSP en vivo" if ctx.live else "lab (sin HTTP)"
    return Outcome(renderable=Text(f"debug {state}  ·  backend {live}", style="yellow"))


def _sync_live(ctx: Ctx) -> Outcome | None:
    if not ctx.live or ctx.client is None:
        return None
    path = ctx.cwd
    try:
        if path[:1] != ["customers"]:
            return None
        ctx.store.apply_cpaa(ctx.client.load_cpaa())
        if len(path) == 1:
            ctx.store.apply_customers(ctx.client.load_customers())
            ctx.rebuild()
            return None
        cid = int(path[1])
        cust = ctx.store.customers.get(cid)
        name = cust.displayed_name if cust else ""
        ctx.store.apply_services(cid, ctx.client.load_services(cid), name)
        if len(path) >= 4:
            sid = int(path[3])
            svc = ctx.store.services.get(sid)
            if svc is not None:
                sites = ctx.client.load_sites(svc)
                saps = ctx.client.load_saps(svc, sites)
                if svc.svc_type == "vprn":
                    saps = ctx.client.apply_vr_masks(svc, sites, saps)
                    rts = ctx.client.load_route_targets(svc)
                    ctx.store.apply_vprn_related(
                        sid,
                        static_routes=ctx.client.load_static_routes(svc, sites),
                        bgp_peers=ctx.client.load_bgp_sites(svc, sites),
                        route_targets=rts,
                    )
                    ctx.store.apply_route_next_hops(
                        sid, ctx.client.load_route_next_hops(svc, rts)
                    )
                    ctx.store.apply_bgp_rib(
                        sid, ctx.client.load_bgp_rib(svc, rts)
                    )
                    ctx.store.apply_bgp_rib_info(
                        sid, ctx.client.load_bgp_rib_info(svc, rts)
                    )
                ctx.store.apply_sites_saps(sid, sites, saps)
                bindings = ctx.client.load_sdp_bindings(svc)
                ctx.store.apply_bindings(sid, bindings)
                tunnels = ctx.client.load_tunnels(bindings)
                ctx.store.apply_tunnels(tunnels)
                ctx.store.apply_lsps(ctx.client.load_lsps(tunnels))
                ctx.store.apply_service_alarms(svc, ctx.client.load_service_alarms(svc))
                if svc.svc_type == "vpls":
                    ctx.store.apply_macs(sid, ctx.client.load_macs(svc))
        ctx.rebuild()
    except UserCancelled:
        raise
    except KeyboardInterrupt as exc:
        raise UserCancelled("Cancelado con Ctrl-C.") from exc
    except NspApiError as exc:
        return Outcome(error=str(exc), quit=True)
    except Exception as exc:
        return Outcome(error=_unexpected(exc), quit=True)
    return None


def _exit_ctx(ctx: Ctx, args: list[str]) -> Outcome:
    if args and args[0].lower() in ("all", "top"):
        ctx.cwd = []
        return Outcome()
    if not ctx.cwd:
        return Outcome(quit=True)
    ctx.cwd.pop()
    return Outcome()


def _unexpected(exc: BaseException) -> str:
    return f"Error inesperado ({type(exc).__name__}): {exc}"


def dispatch(ctx: Ctx, line: str) -> Outcome:
    raw = line.strip()
    if not raw:
        return Outcome()
    try:
        if raw.startswith("/"):
            return _slash(ctx, raw[1:])
        try:
            parts = shlex.split(raw)
        except ValueError as exc:
            return Outcome(error=f"línea inválida: {exc}")
        walked = _walk_fire(ctx, parts)
        rest = parts[walked:]
        sync_err = _sync_live(ctx)
        if sync_err is not None:
            return sync_err
        if not rest:
            return _inspect(ctx) if walked else Outcome()
        verb = rest[0].lower()
        args = rest[1:]
        handlers = _handlers()
        fn = handlers.get(verb)
        if fn is None:
            hint = "  (probá ? o help)" if not ctx.cwd else "  (probá ?  ·  exit para subir)"
            return Outcome(error=f"comando desconocido: {verb}{hint}")
        return fn(ctx, args)
    except UserCancelled:
        raise
    except KeyboardInterrupt as exc:
        raise UserCancelled("Cancelado con Ctrl-C.") from exc
    except NspApiError as exc:
        return Outcome(error=str(exc), quit=True)
    except Exception as exc:
        return Outcome(error=_unexpected(exc), quit=True)


def _slash(ctx: Ctx, rest: str) -> Outcome:
    rest = rest.strip()
    if not rest:
        lines = Text()
        for name, desc in SLASH.items():
            if name == "exit":
                continue
            lines.append(f"/{name:<12}", style="bold cyan")
            lines.append(f" {desc}\n", style="dim")
        return Outcome(renderable=lines)
    parts = rest.split()
    name = parts[0].lower()
    args = parts[1:]
    aliases = {"h": "help", "q": "quit", "logout": "quit", "info": "status"}
    name = aliases.get(name, name)
    mapping = {
        "help": lambda: Outcome(renderable=render.help_text()),
        "status": lambda: _status(ctx, args),
        "whoami": lambda: _whoami(ctx, args),
        "ne": lambda: _ne(ctx, args),
        "mpls": lambda: _mpls(ctx, args),
        "customers": lambda: _customer(ctx, args),
        "customer": lambda: _customer(ctx, args),
        "services": lambda: _service(ctx, args),
        "alarms": lambda: _alarm(ctx, args),
        "stats": lambda: _stats(ctx, args),
        "topology": lambda: Outcome(renderable=render.topology_ascii()),
        "tasks": lambda: _tasks(ctx, args),
        "users": lambda: _users(ctx, args),
        "resync": lambda: _resync(ctx, args),
        "passwd": lambda: _passwd(ctx, args),
        "clear": lambda: Outcome(clear=True),
        "quit": lambda: Outcome(quit=True),
        "logout": lambda: Outcome(quit=True),
        "exit": lambda: _exit_ctx(ctx, args),
        "debug": lambda: _debug(ctx, args),
    }
    fn = mapping.get(name)
    if fn is None:
        return Outcome(error=f"comando desconocido: /{name}  (probá /help)")
    return fn()


def _ls(ctx: Ctx, args: list[str]) -> Outcome:
    spec = args[0] if args else "."
    found = resolve(ctx.root, ctx.cwd, spec)
    if found is None:
        return Outcome(error=f"no existe el objeto: {spec}")
    path, node = found
    return Outcome(renderable=render.ls_table(node, path))


def _cd(ctx: Ctx, args: list[str]) -> Outcome:
    spec = args[0] if args else "/"
    found = resolve(ctx.root, ctx.cwd, spec)
    if found is None:
        return Outcome(error=f"no existe el objeto: {spec}")
    ctx.cwd = found[0]
    return Outcome()


def _pwd(ctx: Ctx, args: list[str]) -> Outcome:
    return Outcome(renderable=Text(cli_prompt(ctx.user.username, ctx.nsp_host, ctx.cwd), style="cyan"))


def _tree(ctx: Ctx, args: list[str]) -> Outcome:
    depth = 2
    spec = "."
    for a in args:
        if a.isdigit():
            depth = max(1, min(int(a), 6))
        else:
            spec = a
    found = resolve(ctx.root, ctx.cwd, spec)
    if found is None:
        return Outcome(error=f"no existe el objeto: {spec}")
    path, node = found
    return Outcome(renderable=render.tree_view(node, path, depth))


def _show(ctx: Ctx, args: list[str]) -> Outcome:
    spec = args[0] if args else "."
    found = resolve(ctx.root, ctx.cwd, spec)
    if found is None:
        obj = _lookup_anywhere(ctx, spec)
        if obj is None:
            return Outcome(error=f"no existe el objeto: {spec}")
        kind, payload = obj
        return Outcome(renderable=render.show_object(payload, kind))
    _path, node = found
    if node.payload is not None:
        return Outcome(renderable=render.show_object(node.payload, node.kind))
    return Outcome(renderable=render.ls_table(node, _path))


def _find(ctx: Ctx, args: list[str]) -> Outcome:
    if not args:
        return Outcome(error="uso: find <texto>")
    needle = " ".join(args).lower()
    hits: list[tuple[str, str, str]] = []

    def walk(node: Node, path: list[str]) -> None:
        blob = " ".join(
            [
                node.name,
                node.kind,
                node.label,
                str(getattr(node.payload, "system_ip", "")),
                str(getattr(node.payload, "name", "")),
            ]
        ).lower()
        if needle in blob:
            hits.append((pwd(path), node.kind, node.label))
        for name, child in node.children.items():
            walk(child, path + [name])

    walk(ctx.root, [])
    if not hits:
        return Outcome(renderable=Text("sin coincidencias", style="dim"))
    from rich.table import Table

    t = Table(title=f"find  {needle!r}  ({len(hits)})", border_style="grey37")
    t.add_column("ruta", style="cyan")
    t.add_column("tipo")
    t.add_column("etiqueta")
    for row in hits[:80]:
        t.add_row(*row)
    if len(hits) > 80:
        t.caption = f"mostrando 80 de {len(hits)}"
    return Outcome(renderable=t)


def _ne(ctx: Ctx, args: list[str]) -> Outcome:
    visible = ctx.store.visible_nes(ctx.user)
    if not args:
        return Outcome(renderable=render.ne_table(visible.values()))
    name = args[0]
    ne = visible.get(name) or next(
        (n for n in visible.values() if n.system_ip == name), None
    )
    if ne is None:
        return Outcome(error=f"NE fuera del span of control: {name}")
    return Outcome(renderable=render.show_ne(ne))


def _mpls(ctx: Ctx, args: list[str]) -> Outcome:
    sub = args[0].lower() if args else "lsps"
    rest = args[1:]
    if sub in ("lsps", "lsp"):
        return _mpls_lsp(ctx, rest)
    if sub in ("paths", "path"):
        if rest:
            path = ctx.store.paths.get(rest[0])
            if path is None:
                return Outcome(error=f"path desconocido: {rest[0]}")
            return Outcome(renderable=render.show_path(path))
        from rich.table import Table

        t = Table(title="Paths MPLS", border_style="grey37")
        t.add_column("nombre", style="bold")
        t.add_column("tipo")
        t.add_column("hops")
        for p in ctx.store.paths.values():
            t.add_row(p.name, p.hop_type, " → ".join(p.hops) or "(loose)")
        return Outcome(renderable=t)
    if sub in ("tunnels", "tunnel", "sdp"):
        from rich.table import Table

        t = Table(title="Túneles de servicio (SDP)", border_style="grey37")
        t.add_column("id", justify="right")
        t.add_column("nombre")
        t.add_column("from")
        t.add_column("to")
        t.add_column("sig")
        t.add_column("lsp")
        t.add_column("oper")
        for sdp in ctx.store.tunnels.values():
            t.add_row(
                str(sdp.sdp_id),
                sdp.name,
                sdp.from_ne,
                sdp.to_ne,
                sdp.signaling,
                sdp.lsp,
                render.state(sdp.oper),
            )
        return Outcome(renderable=t)
    if sub in ("interfaces", "interface", "if"):
        from rich.table import Table

        t = Table(title="Interfaces MPLS", border_style="grey37")
        t.add_column("NE")
        t.add_column("nombre")
        t.add_column("if asociada")
        t.add_column("TE")
        t.add_column("SRLG")
        t.add_column("oper")
        visible = ctx.store.visible_nes(ctx.user)
        for iface in ctx.store.mpls_ifs:
            if iface.ne not in visible:
                continue
            t.add_row(
                iface.ne,
                iface.name,
                iface.interface,
                str(iface.te_metric),
                ",".join(iface.srlgs) or "—",
                render.state(iface.oper),
            )
        return Outcome(renderable=t)
    return Outcome(error="uso: mpls [lsps|paths|tunnels|interfaces]")


def _mpls_lsp(ctx: Ctx, args: list[str]) -> Outcome:
    if not args or args[0] in ("list", "ls"):
        return Outcome(renderable=render.lsp_table(ctx.store.lsps.values()))
    action = args[0].lower()
    if action == "show" and len(args) >= 2:
        lsp = ctx.store.lsps.get(args[1])
        if lsp is None:
            return Outcome(error=f"LSP desconocido: {args[1]}")
        return Outcome(renderable=render.show_lsp(lsp))
    if action == "create":
        return _lsp_create(ctx, args[1:])
    if action in ("shutdown", "shut") and len(args) >= 2:
        return _lsp_admin(ctx, args[1], "down")
    if action in ("turnup", "no-shutdown") and len(args) >= 2:
        return _lsp_admin(ctx, args[1], "up")
    if action == "delete" and len(args) >= 2:
        if not can(ctx.user, "write"):
            return Outcome(error="permiso denegado (write)")
        name = args[1]
        if name not in ctx.store.lsps:
            return Outcome(error=f"LSP desconocido: {name}")
        del ctx.store.lsps[name]
        _task(ctx, f"delete LSP {name}", f"lsp:{name}")
        ctx.rebuild()
        return Outcome(renderable=Text(f"eliminado {name}", style="green"))
    # treat first arg as name
    lsp = ctx.store.lsps.get(args[0])
    if lsp:
        return Outcome(renderable=render.show_lsp(lsp))
    return Outcome(
        error="uso: mpls lsp [list|show <n>|create ...|shutdown <n>|turnup <n>|delete <n>]"
    )


def _parse_kv(args: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for a in args:
        if "=" in a:
            k, v = a.split("=", 1)
            out[k.lower()] = v
    return out


def _lsp_create(ctx: Ctx, args: list[str]) -> Outcome:
    if not can(ctx.user, "write"):
        return Outcome(error="permiso denegado (write)")
    kv = _parse_kv(args)
    name = kv.get("name")
    src = kv.get("from")
    dst = kv.get("to")
    if not name or not src or not dst:
        return Outcome(
            error="uso: mpls lsp create name=X from=NE to=NE [type=dynamic] [sig=rsvp] [path=P]"
        )
    if name in ctx.store.lsps:
        return Outcome(error=f"el LSP ya existe: {name}")
    visible = ctx.store.visible_nes(ctx.user)
    if src not in visible or dst not in visible:
        return Outcome(error="NE origen/destino fuera del span of control")
    path_name = kv.get("path", "loose-any")
    path = ctx.store.paths.get(path_name)
    hops = path.hops if path else [src, dst]
    lsp = Lsp(
        name=name,
        lsp_type=kv.get("type", "dynamic"),
        signaling=kv.get("sig", "rsvp"),
        from_ne=src,
        to_ne=dst,
        path=path_name,
        hops=hops,
        bandwidth_mbps=int(kv.get("bw", "0")),
        protection=kv.get("prot", "none"),
    )
    ctx.store.lsps[name] = lsp
    _task(ctx, f"create LSP {name}", f"lsp:{name}")
    ctx.rebuild()
    return Outcome(renderable=Group(Text("creado", style="green"), render.show_lsp(lsp)))


def _lsp_admin(ctx: Ctx, name: str, admin: str) -> Outcome:
    if not can(ctx.user, "write"):
        return Outcome(error="permiso denegado (write)")
    lsp = ctx.store.lsps.get(name)
    if lsp is None:
        return Outcome(error=f"LSP desconocido: {name}")
    lsp.admin = admin  # type: ignore[assignment]
    lsp.oper = admin  # type: ignore[assignment]
    verb = "apagado (shutdown)" if admin == "down" else "levantado (no-shutdown)"
    _task(ctx, f"{verb} LSP {name}", f"lsp:{name}")
    return Outcome(renderable=Text(f"{name} {verb}", style="green"))


def _customer(ctx: Ctx, args: list[str]) -> Outcome:
    if ctx.live and ctx.client is not None:
        ctx.store.apply_customers(ctx.client.load_customers())
        ctx.rebuild()
    customers = ctx.store.visible_customers(ctx.user)
    if not args:
        return Outcome(renderable=render.customer_table(customers.values(), ctx.store, ctx.user))
    key = args[0]
    cust = customers.get(int(key)) if key.isdigit() else next(
        (c for c in customers.values() if c.displayed_name.lower() == key.lower() or str(c.subscriber_id) == key),
        None,
    )
    if cust is None:
        return Outcome(error=f"cliente desconocido: {key}")
    ctx.cwd = ["customers", str(cust.subscriber_id)]
    err = _sync_live(ctx)
    if err is not None:
        return err
    svcs = ctx.store.services_of(cust.subscriber_id, ctx.user)
    return Outcome(
        renderable=Group(
            render.show_customer(cust),
            render.service_table(svcs),
        )
    )


def _service(ctx: Ctx, args: list[str]) -> Outcome:
    svcs = list(ctx.store.visible_services(ctx.user).values())
    if not args:
        return Outcome(renderable=render.service_table(svcs))
    if args[0].isdigit() and int(args[0]) in ctx.store.customers:
        # /services 12 → services of customer 12
        cid = int(args[0])
        if cid not in ctx.store.visible_customers(ctx.user):
            return Outcome(error=f"cliente fuera del span: {cid}")
        return Outcome(renderable=render.service_table(ctx.store.services_of(cid, ctx.user)))
    key = args[0]
    svc = next((s for s in svcs if str(s.svc_id) == key or s.name == key), None)
    if svc is None:
        return Outcome(error=f"servicio desconocido: {key}")
    ctx.cwd = ["customers", str(svc.customer_id), svc.svc_type, str(svc.svc_id)]
    return Outcome(renderable=render.show_service(svc))


def _alarm(ctx: Ctx, args: list[str]) -> Outcome:
    visible = ctx.store.visible_nes(ctx.user)
    alarms = [a for a in ctx.store.alarms if a.ne in visible or not a.ne]
    if not args:
        return Outcome(renderable=render.alarm_table(alarms))
    action = args[0].lower()
    if action in ("list", "ls"):
        sev = args[1].lower() if len(args) > 1 else ""
        if sev:
            alarms = [a for a in alarms if a.severity == sev]
        return Outcome(renderable=render.alarm_table(alarms))
    if action in ("ack", "acknowledge") and len(args) >= 2:
        if not can(ctx.user, "execute"):
            return Outcome(error="permiso denegado (execute) — no se puede reconocer la alarma")
        return _alarm_mutate(ctx, args[1], ack=True)
    if action == "clear" and len(args) >= 2:
        if not can(ctx.user, "execute"):
            return Outcome(error="permiso denegado (execute) — no se puede limpiar la alarma")
        return _alarm_mutate(ctx, args[1], clear=True)
    if action in ("critical", "major", "minor", "warning"):
        alarms = [a for a in alarms if a.severity == action]
        return Outcome(renderable=render.alarm_table(alarms))
    alarm = next((a for a in alarms if a.id == args[0]), None)
    if alarm:
        return Outcome(renderable=render.show_alarm(alarm))
    return Outcome(error="uso: alarm [list|ack <id>|clear <id>|<id>|<severity>]")


def _alarm_mutate(ctx: Ctx, alarm_id: str, ack: bool = False, clear: bool = False) -> Outcome:
    alarm = next((a for a in ctx.store.alarms if a.id == alarm_id), None)
    if alarm is None:
        return Outcome(error=f"alarma desconocida: {alarm_id}")
    if ack:
        alarm.acked = True
        alarm.acked_by = ctx.user.username
        _task(ctx, f"acknowledge {alarm_id}", alarm.object_fdn)
        return Outcome(renderable=Text(f"{alarm_id} reconocida", style="green"))
    if clear:
        alarm.cleared = True
        alarm.severity = "cleared"
        _task(ctx, f"clear {alarm_id}", alarm.object_fdn)
        ctx.rebuild()
        return Outcome(renderable=Text(f"{alarm_id} limpiada", style="green"))
    return Outcome()


def _stats(ctx: Ctx, args: list[str]) -> Outcome:
    if not args:
        return Outcome(
            error=(
                "uso: stats <fdn>   ej. stats ne:PE-BAIRES-01:port:1/1/1  "
                "o  stats lsp:lsp-ba-cba  o  stats network:<NE>:...:port-3"
            )
        )
    fdn = args[0]
    if ctx.live and ctx.client is not None:
        pointer = _stats_pointer(ctx, fdn)
        samples = ctx.client.load_stats(pointer)
        if samples:
            return Outcome(renderable=render.stats_table(samples, pointer))
        lab = render.stats_table(ctx.store.stats, fdn)
        note = (
            "Live: sin log records (hace falta política MIB y timeCaptured reciente). "
            f"Puntero {pointer}. children=\"\" + filtro and/equal/between."
        )
        return Outcome(renderable=Group(render.stats_table(samples, pointer), Text(note, style="yellow"), lab))
    return Outcome(renderable=render.stats_table(ctx.store.stats, fdn))


def _stats_pointer(ctx: Ctx, fdn: str) -> str:
    if fdn.startswith(("network:", "svc-mgr:", "svt:")):
        return fdn
    if fdn.startswith("lsp:"):
        name = fdn.split(":", 1)[1]
        lsp = ctx.store.lsps.get(name)
        if lsp:
            return f"network:{lsp.from_ne}:dynamicLsp-{lsp.name}"
        return fdn
    if fdn.startswith("ne:") and ":port:" in fdn:
        parts = fdn.split(":")
        # ne:NAME:port:1/1/1
        name = parts[1] if len(parts) > 1 else ""
        port = fdn.split(":port:", 1)[-1]
        ne = ctx.store.nes.get(name)
        if ne:
            return f"network:{ne.system_ip}:{port}"
    return fdn


def _resync(ctx: Ctx, args: list[str]) -> Outcome:
    if not can(ctx.user, "write"):
        return Outcome(error="permiso denegado (write)")
    visible = ctx.store.visible_nes(ctx.user)
    names = args or list(visible)
    done = []
    for name in names:
        ne = visible.get(name)
        if ne is None:
            return Outcome(error=f"NE fuera del span: {name}")
        ne.management = "managed"
        _task(ctx, f"resync {name}", f"ne:{name}")
        done.append(name)
    return Outcome(renderable=Text("resincronizado: " + ", ".join(done), style="green"))


def _whoami(ctx: Ctx, args: list[str]) -> Outcome:
    return Outcome(renderable=render.show_user(ctx.user))


def _status(ctx: Ctx, args: list[str]) -> Outcome:
    visible = ctx.store.visible_nes(ctx.user)
    alarms = [a for a in ctx.store.alarms if not a.cleared and a.ne in visible]
    counts: dict[str, int] = {}
    for a in alarms:
        counts[a.severity] = counts.get(a.severity, 0) + 1
    up = sum(1 for n in visible.values() if n.oper == "up")
    lsp_up = sum(1 for l in ctx.store.lsps.values() if l.oper == "up")
    vis_svc = ctx.store.visible_services(ctx.user)
    vis_cust = ctx.store.visible_customers(ctx.user)
    svc_up = sum(1 for s in vis_svc.values() if s.oper == "up")
    rows = [
        ("Producto", f"NSP-Grok {RELEASE}  shell clásica NFM-P"),
        ("Sesión", ctx.session_id),
        ("Usuario", f"{ctx.user.username}  ({ctx.user.role} / {ctx.user.group})"),
        ("Span of Control", ", ".join(ctx.user.span) or "ALL"),
        ("Contexto", pwd(ctx.cwd)),
        ("Clientes", str(len(vis_cust))),
        ("Servicios", f"{svc_up}/{len(vis_svc)} operativos  (VPRN/VPLS/Epipe)"),
        ("NEs", f"{up}/{len(visible)} operativos"),
        ("LSPs", f"{lsp_up}/{len(ctx.store.lsps)} operativos"),
        (
            "Alarmas",
            "  ".join(f"{k}={v}" for k, v in counts.items()) or "sin pendientes",
        ),
        ("Inicio", ctx.started.strftime("%Y-%m-%d %H:%M:%SZ")),
        ("Backend", "NSP en vivo" if ctx.live else "lab local"),
        ("Debug HTTP", "on" if ctx.debug else "off"),
    ]
    for cpaa in ctx.store.cpaa:
        rec = cpaa.protocol_record or "—"
        rows.append(
            (
                "CPAA",
                f"{cpaa.fdn}  record={rec}  RIB={cpaa.rib_retrieve}  RT={cpaa.rt_retrieve}",
            )
        )
    return Outcome(renderable=render.kv_table(rows, title="Sesión"))


def _passwd(ctx: Ctx, args: list[str]) -> Outcome:
    if len(args) < 2:
        return Outcome(error="uso: passwd <actual> <nueva>     (o /passwd)")
    errors = change_password(ctx.user, args[0], args[1])
    if errors:
        return Outcome(error="; ".join(errors))
    return Outcome(renderable=Text("contraseña actualizada", style="green"))


def _users(ctx: Ctx, args: list[str]) -> Outcome:
    if ctx.user.role != "administrator":
        return Outcome(error="permiso denegado (se requiere rol administrator)")
    from rich.table import Table

    t = Table(title="Usuarios locales", border_style="grey37")
    t.add_column("usuario")
    t.add_column("grupo")
    t.add_column("rol")
    t.add_column("acceso")
    t.add_column("span")
    t.add_column("estado")
    t.add_column("último login")
    for u in ctx.store.users.values():
        t.add_row(
            u.username,
            u.group,
            u.role,
            u.access,
            ",".join(u.span) or "ALL",
            render.state(u.state),
            u.last_login.strftime("%H:%M:%SZ") if u.last_login else "—",
        )
    return Outcome(renderable=t)


def _tasks(ctx: Ctx, args: list[str]) -> Outcome:
    from rich.table import Table

    t = Table(title="Gestor de tareas", border_style="grey37")
    t.add_column("id", justify="right")
    t.add_column("usuario")
    t.add_column("operación")
    t.add_column("objeto")
    t.add_column("estado")
    t.add_column("inicio")
    if not ctx.store.tasks:
        t.add_row("—", "—", "sin tareas en esta sesión", "", "", "")
        return Outcome(renderable=t)
    for task in ctx.store.tasks[-20:]:
        t.add_row(
            str(task.id),
            task.user,
            task.operation,
            task.object_fdn,
            task.state,
            task.started.strftime("%H:%M:%SZ"),
        )
    return Outcome(renderable=t)


def _task(ctx: Ctx, operation: str, fdn: str) -> None:
    task = Task(
        id=ctx.store.task_seq,
        user=ctx.user.username,
        operation=operation,
        object_fdn=fdn,
        state="success",
        started=datetime.now(timezone.utc),
        finished=datetime.now(timezone.utc),
    )
    ctx.store.task_seq += 1
    ctx.store.tasks.append(task)
    ctx.last_task = task.id


def _lookup_anywhere(ctx: Ctx, spec: str) -> tuple[str, Any] | None:
    if spec.isdigit() and int(spec) in ctx.store.visible_customers(ctx.user):
        return "customer", ctx.store.customers[int(spec)]
    if spec in ctx.store.nes:
        ne = ctx.store.visible_nes(ctx.user).get(spec)
        return ("ne", ne) if ne else None
    if spec in ctx.store.lsps:
        return "lsp", ctx.store.lsps[spec]
    if spec in ctx.store.paths:
        return "path", ctx.store.paths[spec]
    if spec.isdigit() and int(spec) in ctx.store.services:
        return "service", ctx.store.services[int(spec)]
    if spec.isdigit() and int(spec) in ctx.store.tunnels:
        return "sdp", ctx.store.tunnels[int(spec)]
    alarm = next((a for a in ctx.store.alarms if a.id == spec), None)
    if alarm:
        return "alarm", alarm
    return None
