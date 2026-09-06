"""Tab completion for navigation paths and slash commands."""

from __future__ import annotations

from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document

from nsp_grok.commands import SLASH, Ctx
from nsp_grok.tree import resolve

VERBS = [
    "ls",
    "?",
    "cd",
    "pwd",
    "tree",
    "show",
    "info",
    "cat",
    "find",
    "help",
    "mpls",
    "alarm",
    "ne",
    "customer",
    "customers",
    "service",
    "services",
    "create",
    "sap",
    "saps",
    "sdp",
    "binding",
    "stats",
    "resync",
    "topology",
    "clear",
    "exit",
    "top",
    "logout",
    "quit",
    "whoami",
    "status",
    "passwd",
    "users",
    "tasks",
    "debug",
    "cpaa",
    "tunnel",
    "tunnels",
]

CREATE_KEYS = {
    "service": ["type=", "customer=", "id=", "name=", "sites=", "desc=", "confirm="],
    "sap": ["service=", "site=", "port=", "vlan=", "ip=", "inner=", "name=", "confirm="],
    "sdp": ["service=", "site=", "far=", "sdp=", "vc=", "type=", "confirm="],
    "tunnel": ["from=", "to=", "id=", "lsp=", "sig=", "name=", "confirm="],
    "lsp": ["name=", "from=", "to=", "type=", "sig=", "path=", "id=", "confirm="],
}


def detect_create_kind(parts: list[str], cwd: list[str]) -> str | None:
    p = [x.lower() for x in parts]
    if not p:
        return None
    if p[0] == "create":
        if len(p) >= 2:
            if p[1] in {"sap", "saps"}:
                return "sap"
            if p[1] in {"sdp", "binding"}:
                return "sdp"
            if p[1] in {"tunnel", "tunnels"}:
                return "tunnel"
            if p[1] in {"lsp", "lsps"}:
                return "lsp"
        if cwd:
            if cwd[-1] == "saps":
                return "sap"
            if cwd[-1] in {"sdp-bindings", "bindings"}:
                return "sdp"
            if cwd[-1] == "tunnels" or cwd[:2] == ["mpls", "tunnels"]:
                return "tunnel"
            if cwd[:1] == ["mpls"]:
                return "lsp"
        return "service"
    if p[0] in {"service", "services"} and len(p) >= 2 and p[1] == "create":
        return "service"
    if p[0] in {"sap", "saps"} and len(p) >= 2 and p[1] == "create":
        return "sap"
    if p[0] in {"sdp", "binding", "bindings"} and len(p) >= 2 and p[1] == "create":
        return "sdp"
    if p[0] in {"tunnel", "tunnels"} and len(p) >= 2 and p[1] == "create":
        return "tunnel"
    if p[0] == "mpls" and len(p) >= 3 and p[1] in {"lsp", "lsps"} and p[2] == "create":
        return "lsp"
    if p[0] == "mpls" and len(p) >= 3 and p[1] in {"tunnel", "tunnels"} and p[2] == "create":
        return "tunnel"
    return None


def _assigned_kv(parts: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for part in parts:
        if "=" in part:
            key, val = part.split("=", 1)
            out[key.lower()] = val
    return out


def _ne_by_token(ctx: Ctx, token: str):
    if not token:
        return None
    nes = ctx.store.visible_nes(ctx.user)
    if token in nes:
        return nes[token]
    for ne in nes.values():
        if ne.system_ip == token:
            return ne
    return None


def _svc_from_assigned(ctx: Ctx, assigned: dict[str, str], kind: str = ""):
    key = assigned.get("service") or assigned.get("svc") or ""
    if not key and kind in {"sap", "sdp"}:
        key = assigned.get("id") or ""
    if key.isdigit():
        return ctx.store.visible_services(ctx.user).get(int(key))
    cwd = ctx.cwd
    if len(cwd) >= 4 and cwd[0] == "customers" and cwd[3].isdigit():
        return ctx.store.services.get(int(cwd[3]))
    return None


def create_value_choices(ctx: Ctx, kind: str, assigned: dict[str, str], key: str) -> list[tuple[str, str]]:
    """(value, meta) filtered by customer/service/site and network direction."""
    nes = ctx.store.visible_nes(ctx.user)
    if key == "confirm":
        return [("yes", "confirmar"), ("no", "cancelar")]
    if key == "type" and kind == "service":
        return [("vprn", "L3 VPN"), ("vpls", "E-LAN"), ("epipe", "E-Line")]
    if key == "type" and kind == "sdp":
        svc = _svc_from_assigned(ctx, assigned, kind)
        if svc and svc.svc_type != "vpls":
            return [("spoke", "VPRN/Epipe")]
        return [("spoke", "spoke"), ("mesh", "VPLS")]
    if key == "type" and kind == "lsp":
        return [("dynamic", "RSVP"), ("static", ""), ("sr-te", "SR-TE"), ("bypass", "")]
    if key == "sig" and kind in {"lsp", "tunnel"}:
        return [("rsvp", ""), ("tldp", ""), ("ldp", ""), ("sr", ""), ("mpls", ""), ("gre", "")]
    if key == "customer":
        return [
            (str(c.subscriber_id), c.displayed_name)
            for c in ctx.store.visible_customers(ctx.user).values()
        ]
    if key == "service":
        cid = assigned.get("customer")
        svcs = ctx.store.visible_services(ctx.user)
        if cid and cid.isdigit():
            wanted = int(cid)
            svcs = {i: s for i, s in svcs.items() if s.customer_id == wanted}
        elif ctx.cwd[:1] == ["customers"] and len(ctx.cwd) >= 2 and ctx.cwd[1].isdigit():
            wanted = int(ctx.cwd[1])
            svcs = {i: s for i, s in svcs.items() if s.customer_id == wanted}
        return [(str(s.svc_id), f"{s.svc_type} {s.name}") for s in svcs.values()]
    if key == "sites":
        taken = {t.strip() for t in assigned.get("sites", "").split(",") if t.strip()}
        return [(n, ne.system_ip) for n, ne in nes.items() if n not in taken]
    if key in {"from", "site"} and kind in {"lsp", "tunnel", "sap", "sdp"}:
        svc = _svc_from_assigned(ctx, assigned, kind)
        if kind in {"sap", "sdp"} and svc:
            sites = ctx.store.sites_of(svc.svc_id, ctx.user)
            if sites:
                return [(s.ne, s.site_id) for s in sites] + [
                    (n, "NE (nuevo site)") for n in nes if n not in {s.ne for s in sites}
                ]
        return [(n, ne.system_ip) for n, ne in nes.items()]
    if key in {"to", "far"}:
        src_tok = assigned.get("from") or assigned.get("site") or ""
        src = _ne_by_token(ctx, src_tok)
        out: list[tuple[str, str]] = []
        for n, ne in nes.items():
            if src and (n == src.name or ne.system_ip == src.system_ip):
                continue
            meta = ne.system_ip
            if src:
                tuns = [
                    t
                    for t in ctx.store.tunnels.values()
                    if t.from_ne in {src.name, src.system_ip} and t.to_ne in {n, ne.system_ip}
                ]
                if tuns:
                    meta = f"túnel {','.join(str(t.sdp_id) for t in tuns)}"
            out.append((n, meta))
        return out
    if key == "sdp" and kind == "sdp":
        src = _ne_by_token(ctx, assigned.get("site") or "")
        dst = _ne_by_token(ctx, assigned.get("far") or assigned.get("to") or "")
        out = []
        for t in ctx.store.tunnels.values():
            if src and t.from_ne not in {src.name, src.system_ip}:
                continue
            if dst and t.to_ne not in {dst.name, dst.system_ip} and t.far_end not in {
                dst.system_ip,
                dst.name,
            }:
                continue
            out.append((str(t.sdp_id), f"{t.from_ne}→{t.to_ne} {t.name}"))
        return out
    if key == "lsp":
        src = _ne_by_token(ctx, assigned.get("from") or assigned.get("site") or "")
        dst = _ne_by_token(ctx, assigned.get("to") or assigned.get("far") or "")
        out = []
        for lsp in ctx.store.lsps.values():
            if src and lsp.from_ne not in {src.name, src.system_ip}:
                continue
            if dst and lsp.to_ne not in {dst.name, dst.system_ip}:
                continue
            out.append((lsp.name, f"{lsp.from_ne}→{lsp.to_ne}"))
        return out
    if key == "path":
        return [(p, f"{len(path.hops)} hops") for p, path in ctx.store.paths.items()]
    if key == "port":
        site = _ne_by_token(ctx, assigned.get("site") or "")
        if site is None:
            return []
        vals: list[tuple[str, str]] = []
        for card in site.cards:
            for port in card.ports:
                if port.mode == "network":
                    continue
                vals.append((port.name, f"{port.mode} {port.encap}"))
        return vals
    if key == "vlan":
        return []
    if key == "ip":
        svc = _svc_from_assigned(ctx, assigned, kind)
        if svc and svc.svc_type != "vprn":
            return []
        return []
    return []


def create_key_choices(kind: str, assigned: dict[str, str], svc_type: str = "") -> list[str]:
    keys = list(CREATE_KEYS.get(kind, []))
    if kind == "sap" and svc_type and svc_type != "vprn":
        keys = [k for k in keys if k != "ip="]
    if kind == "sdp" and svc_type and svc_type != "vpls":
        pass
    skip = set()
    for k in assigned:
        if k != "sites":
            skip.add(k + "=")
    return [k for k in keys if k not in skip]


class NspCompleter(Completer):
    def __init__(self, ctx: Ctx) -> None:
        self.ctx = ctx

    def get_completions(self, document: Document, complete_event):
        text = document.text_before_cursor
        if text.startswith("/"):
            yield from self._slash(text)
            return
        parts = text.split()
        if not parts or (len(parts) == 1 and not text.endswith(" ")):
            prefix = parts[0] if parts else ""
            node = self.ctx.node()
            for name, child in node.children.items():
                if name.startswith(prefix):
                    yield Completion(
                        name,
                        start_position=-len(prefix),
                        display_meta=child.kind,
                    )
            for v in VERBS:
                if v.startswith(prefix):
                    yield Completion(v, start_position=-len(prefix))
            return
        verb = parts[0]
        current = parts[-1] if not text.endswith(" ") else ""
        yield from self._complete_create(parts, current, text.endswith(" "))
        if verb in ("cd", "ls", "show", "cat", "tree"):
            yield from self._paths(current)
        elif verb in ("customer", "customers"):
            for cid, cust in self.ctx.store.visible_customers(self.ctx.user).items():
                token = str(cid)
                if token.startswith(current) or cust.displayed_name.lower().startswith(current.lower()):
                    yield Completion(token, start_position=-len(current), display_meta=cust.displayed_name)
        elif verb in ("service", "services"):
            if len(parts) == 1 or (len(parts) == 2 and not text.endswith(" ")):
                for w in ("create", "shutdown", "turnup", "delete"):
                    if w.startswith(current):
                        yield Completion(w, start_position=-len(current))
            for sid, svc in self.ctx.store.visible_services(self.ctx.user).items():
                token = str(sid)
                if token.startswith(current) or svc.name.startswith(current):
                    yield Completion(token, start_position=-len(current), display_meta=svc.name)
        elif verb in ("sap", "saps"):
            if len(parts) == 1 or (len(parts) == 2 and not text.endswith(" ")):
                for w in ("create", "shutdown", "turnup", "delete", "list"):
                    if w.startswith(current):
                        yield Completion(w, start_position=-len(current))
            svc = None
            if len(self.ctx.cwd) >= 4 and self.ctx.cwd[3].isdigit():
                svc = self.ctx.store.services.get(int(self.ctx.cwd[3]))
            saps = (
                self.ctx.store.saps_of(svc.svc_id, self.ctx.user)
                if svc
                else [
                    sap
                    for sid in self.ctx.store.visible_services(self.ctx.user)
                    for sap in self.ctx.store.saps_of(sid, self.ctx.user)
                ]
            )
            for sap in saps:
                if sap.name.startswith(current):
                    yield Completion(sap.name, start_position=-len(current), display_meta=str(sap.svc_id))
        elif verb in ("sdp", "binding", "bindings"):
            if len(parts) == 1 or (len(parts) == 2 and not text.endswith(" ")):
                for w in ("create", "shutdown", "turnup", "delete", "list"):
                    if w.startswith(current):
                        yield Completion(w, start_position=-len(current))
        elif verb in ("ne", "resync"):
            for name in self.ctx.store.visible_nes(self.ctx.user):
                if name.startswith(current):
                    yield Completion(name, start_position=-len(current))
        elif verb in ("mpls",):
            if len(parts) == 1 or (len(parts) == 2 and not text.endswith(" ")):
                for w in ("lsps", "lsp", "paths", "tunnels", "interfaces"):
                    if w.startswith(current):
                        yield Completion(w, start_position=-len(current))
            elif len(parts) == 2 or (len(parts) == 3 and not text.endswith(" ")):
                if parts[1] in ("lsp", "lsps"):
                    for w in ("list", "show", "create", "shutdown", "turnup", "delete"):
                        if w.startswith(current):
                            yield Completion(w, start_position=-len(current))
                    for name in self.ctx.store.lsps:
                        if name.startswith(current):
                            yield Completion(name, start_position=-len(current))
            elif len(parts) >= 3 and parts[1] in ("lsp", "lsps") and parts[2] in (
                "show",
                "shutdown",
                "turnup",
                "delete",
            ):
                for name in self.ctx.store.lsps:
                    if name.startswith(current):
                        yield Completion(name, start_position=-len(current))
        elif verb in ("alarm", "alarms"):
            if current.startswith("A-") or not current:
                for a in self.ctx.store.alarms:
                    if a.id.startswith(current):
                        yield Completion(a.id, start_position=-len(current))
            for w in ("list", "ack", "clear", "critical", "major", "minor", "warning"):
                if w.startswith(current):
                    yield Completion(w, start_position=-len(current))

    def _complete_create(self, parts: list[str], current: str, trailing_space: bool):
        kind = detect_create_kind(parts, self.ctx.cwd)
        if kind is None:
            return
        assigned = _assigned_kv(parts if trailing_space else parts[:-1])
        svc = _svc_from_assigned(self.ctx, assigned, kind)
        svc_type = svc.svc_type if svc else assigned.get("type", "")
        if not trailing_space and "=" in current:
            key, val = current.split("=", 1)
            key_l = key.lower()
            head, piece = "", val
            if key_l == "sites" and "," in val:
                head, piece = val.rsplit(",", 1)
                head += ","
            for choice, meta in create_value_choices(self.ctx, kind, assigned, key_l):
                if str(choice).startswith(piece):
                    yield Completion(
                        f"{key}={head}{choice}",
                        start_position=-len(current),
                        display_meta=meta,
                    )
            return
        prefix = "" if trailing_space else current
        for key in create_key_choices(kind, assigned, svc_type):
            if key.startswith(prefix):
                yield Completion(key, start_position=-len(prefix), display_meta=kind)

    def _slash(self, text: str):
        prefix = text[1:]
        word = prefix.split()[0] if prefix else ""
        if " " not in prefix:
            for name, desc in SLASH.items():
                if name.startswith(word):
                    yield Completion(
                        name,
                        start_position=-len(word),
                        display=f"/{name}",
                        display_meta=desc,
                    )
            return
        parts = prefix.split()
        current = "" if prefix.endswith(" ") else parts[-1]
        yield from self._complete_create(parts, current, prefix.endswith(" "))

    def _paths(self, current: str):
        if current.startswith("/"):
            parent_spec = "/".join(current.split("/")[:-1]) or "/"
            prefix = current.rsplit("/", 1)[-1]
            found = resolve(self.ctx.root, self.ctx.cwd, parent_spec)
        elif "/" in current:
            parent_spec, prefix = current.rsplit("/", 1)
            found = resolve(self.ctx.root, self.ctx.cwd, parent_spec)
        else:
            prefix = current
            found = resolve(self.ctx.root, self.ctx.cwd, ".")
        if found is None:
            return
        _path, node = found
        for name, child in node.children.items():
            if name.startswith(prefix):
                suffix = "/" if child.children else ""
                yield Completion(name + suffix, start_position=-len(prefix))
