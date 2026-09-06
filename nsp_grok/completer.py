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
]


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

    def _slash(self, text: str):
        prefix = text[1:]
        word = prefix.split()[0] if prefix else ""
        if " " in prefix:
            return
        for name, desc in SLASH.items():
            if name.startswith(word):
                yield Completion(
                    name,
                    start_position=-len(word),
                    display=f"/{name}",
                    display_meta=desc,
                )

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
