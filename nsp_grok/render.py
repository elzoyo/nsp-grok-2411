"""Rich renderers for list forms, property forms, and the status line."""

from __future__ import annotations

from typing import Any, Iterable

from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.tree import Tree as RichTree

from nsp_grok.models import (
    SEVERITY_ORDER,
    AccessInterface,
    Alarm,
    BgpPeer,
    Card,
    Customer,
    Lsp,
    MacEntry,
    MplsInterface,
    MplsPath,
    NetworkElement,
    Port,
    RouteTarget,
    Service,
    ServiceSite,
    ServiceTunnel,
    SdpBinding,
    StaticRoute,
    StatSample,
    User,
)
from nsp_grok.tree import Node, pwd

SEV_STYLE = {
    "critical": "bold red",
    "major": "bold dark_orange",
    "minor": "yellow",
    "warning": "cyan",
    "cleared": "green",
    "up": "green",
    "down": "red",
    "degraded": "yellow",
    "managed": "green",
    "suspended": "magenta",
    "unmanaged": "grey50",
}


def state(value: str) -> Text:
    return Text(str(value), style=SEV_STYLE.get(str(value), ""))


def banner() -> RenderableType:
    body = Text.assemble(
        ("NSP-Grok", "bold cyan"),
        ("  ", ""),
        ("24.11", "bold white"),
        ("\n", ""),
        ("Network Functions Manager — Packet", "dim"),
        ("\n", ""),
        ("Classic management shell  ·  IP/MPLS", "dim"),
    )
    return Panel(body, border_style="cyan", padding=(0, 2))


def kv_table(rows: Iterable[tuple[str, Any]], title: str = "") -> Table:
    table = Table(show_header=False, box=None, padding=(0, 2, 0, 0), title=title)
    table.add_column("k", style="dim", min_width=18)
    table.add_column("v")
    for key, value in rows:
        if isinstance(value, Text):
            table.add_row(key, value)
        else:
            table.add_row(key, str(value) if value is not None else "")
    return table


def ls_table(node: Node, path: list[str]) -> RenderableType:
    if not node.children:
        return Text(f"(empty)  {pwd(path)}", style="dim")
    table = Table(
        title=f"{pwd(path)}  [{node.kind}]",
        expand=False,
        border_style="grey37",
    )
    table.add_column("name", style="bold")
    table.add_column("kind", style="cyan")
    table.add_column("label")
    table.add_column("state")
    for name, child in node.children.items():
        st = _object_state(child.payload)
        suffix = "/" if child.children else ""
        table.add_row(name + suffix, child.kind, child.label, state(st) if st else Text(""))
    return table


def tree_view(node: Node, path: list[str], depth: int = 2) -> RenderableType:
    rich = RichTree(f"[bold cyan]{pwd(path)}[/]  [dim]{node.kind}[/]")
    _walk_tree(rich, node, depth)
    return rich


def _walk_tree(rich: RichTree, node: Node, depth: int) -> None:
    if depth <= 0:
        return
    for name, child in node.children.items():
        mark = "/" if child.children else ""
        st = _object_state(child.payload)
        extra = f"  [dim]{child.label}[/]" if child.label else ""
        if st:
            extra += f"  [{SEV_STYLE.get(st, 'white')}]{st}[/]"
        branch = rich.add(f"{name}{mark}{extra}")
        _walk_tree(branch, child, depth - 1)


def show_object(payload: Any, kind: str) -> RenderableType:
    if isinstance(payload, NetworkElement):
        return show_ne(payload)
    if isinstance(payload, Card):
        return show_card(payload)
    if isinstance(payload, Port):
        return show_port(payload)
    if isinstance(payload, Lsp):
        return show_lsp(payload)
    if isinstance(payload, MplsPath):
        return show_path(payload)
    if isinstance(payload, MplsInterface):
        return show_mpls_if(payload)
    if isinstance(payload, ServiceTunnel):
        return show_sdp(payload)
    if isinstance(payload, Customer):
        return show_customer(payload)
    if isinstance(payload, Service):
        return show_service(payload)
    if isinstance(payload, ServiceSite):
        return show_site(payload)
    if isinstance(payload, AccessInterface):
        return show_sap(payload)
    if isinstance(payload, SdpBinding):
        return show_binding(payload)
    if isinstance(payload, RouteTarget):
        return kv_table([("Direction", payload.direction), ("Route Target", payload.value), ("Service", payload.svc_id)])
    if isinstance(payload, StaticRoute):
        return kv_table(
            [
                ("Prefix", payload.prefix),
                ("Next hop", payload.next_hop),
                ("Site", payload.site_id),
                ("Admin", state(payload.admin)),
            ]
        )
    if isinstance(payload, BgpPeer):
        return kv_table(
            [
                ("Peer", payload.peer_ip),
                ("AS", payload.peer_as),
                ("Site", payload.site_id),
                ("Admin", state(payload.admin)),
                ("Oper", state(payload.oper)),
            ]
        )
    if isinstance(payload, MacEntry):
        return kv_table(
            [
                ("MAC", payload.mac),
                ("Port", payload.port),
                ("Site", payload.site_id),
                ("Source", payload.source),
            ]
        )
    if isinstance(payload, Alarm):
        return show_alarm(payload)
    if isinstance(payload, User):
        return show_user(payload)
    return Text(repr(payload))


def show_ne(ne: NetworkElement) -> RenderableType:
    ports = sum(len(c.ports) for c in ne.cards)
    general = kv_table(
        [
            ("Displayed Name", ne.name),
            ("System IP", ne.system_ip),
            ("Chassis Type", ne.ne_type),
            ("Software Version", ne.version),
            ("Site", ne.site),
            ("Equipment Group", ne.group),
            ("Chassis MAC", ne.chassis_mac),
            ("Administrative State", state(ne.admin)),
            ("Operational State", state(ne.oper)),
            ("Management State", state(ne.management)),
            ("Protocols", ", ".join(p.upper() for p in ne.protocols)),
            ("Cards / Ports", f"{len(ne.cards)} / {ports}"),
        ]
    )
    cards = Table(title="Cards", border_style="grey37")
    cards.add_column("slot")
    cards.add_column("type")
    cards.add_column("admin")
    cards.add_column("oper")
    cards.add_column("ports")
    for c in ne.cards:
        cards.add_row(c.slot, c.card_type, state(c.admin), state(c.oper), str(len(c.ports)))
    return Panel(Group(general, cards), title=f"NE properties  {ne.name}", border_style="cyan")


def show_card(card: Card) -> RenderableType:
    t = Table(title=f"Card slot {card.slot}", border_style="grey37")
    t.add_column("port")
    t.add_column("mode")
    t.add_column("encap")
    t.add_column("speed")
    t.add_column("admin")
    t.add_column("oper")
    for p in card.ports:
        t.add_row(p.name, p.mode, p.encap, p.speed, state(p.admin), state(p.oper))
    head = kv_table(
        [
            ("Slot", card.slot),
            ("Card Type", card.card_type),
            ("Equipped", card.equipped),
            ("Administrative State", state(card.admin)),
            ("Operational State", state(card.oper)),
        ]
    )
    return Group(head, t)


def show_port(port: Port) -> RenderableType:
    return Panel(
        kv_table(
            [
                ("Port", port.name),
                ("Mode", port.mode),
                ("Encap", port.encap),
                ("Speed", port.speed),
                ("LAG", port.lag or "—"),
                ("Description", port.description),
                ("Administrative State", state(port.admin)),
                ("Operational State", state(port.oper)),
            ]
        ),
        title="Port properties",
        border_style="cyan",
    )


def show_lsp(lsp: Lsp) -> RenderableType:
    hops = " → ".join(lsp.hops) if lsp.hops else "(loose)"
    return Panel(
        kv_table(
            [
                ("Name", lsp.name),
                ("Type", lsp.lsp_type),
                ("Signaling", lsp.signaling.upper()),
                ("From", lsp.from_ne),
                ("To", lsp.to_ne),
                ("Path", lsp.path),
                ("Hops", hops),
                ("Metric", lsp.metric),
                ("Bandwidth", f"{lsp.bandwidth_mbps} Mbps"),
                ("Setup / Hold", f"{lsp.setup_priority} / {lsp.hold_priority}"),
                ("Protection", lsp.protection),
                ("Administrative State", state(lsp.admin)),
                ("Operational State", state(lsp.oper)),
            ]
        ),
        title=f"LSP  {lsp.name}",
        border_style="cyan",
    )


def show_path(path: MplsPath) -> RenderableType:
    hops = " → ".join(path.hops) if path.hops else "(none)"
    return kv_table(
        [("Name", path.name), ("Hop type", path.hop_type), ("Hops", hops)],
        title="MPLS Path",
    )


def show_mpls_if(iface: MplsInterface) -> RenderableType:
    return kv_table(
        [
            ("NE", iface.ne),
            ("MPLS Interface", iface.name),
            ("Bound L3 Interface", iface.interface),
            ("TE Metric", iface.te_metric),
            ("SRLGs", ", ".join(iface.srlgs) or "—"),
            ("Administrative State", state(iface.admin)),
            ("Operational State", state(iface.oper)),
        ]
    )


def show_sdp(sdp: ServiceTunnel) -> RenderableType:
    return kv_table(
        [
            ("SDP ID", sdp.sdp_id),
            ("Name", sdp.name),
            ("From", sdp.from_ne),
            ("To", sdp.to_ne),
            ("Far End", sdp.far_end),
            ("Signaling", sdp.signaling),
            ("LSP", sdp.lsp),
            ("Administrative State", state(sdp.admin)),
            ("Operational State", state(sdp.oper)),
        ],
        title="Service tunnel (SDP)",
    )


def show_customer(cust: Customer) -> RenderableType:
    return Panel(
        kv_table(
            [
                ("Class", "subscr.Subscriber"),
                ("objectFullName", cust.fdn),
                ("subscriberId", cust.subscriber_id),
                ("displayedName", cust.displayed_name),
                ("Description", cust.description),
                ("Contact", cust.contact),
            ]
        ),
        title=f"Customer  {cust.subscriber_id}",
        border_style="cyan",
    )


def show_service(svc: Service) -> RenderableType:
    nsp_name = {"vprn": "L3 VPN", "vpls": "E-LAN", "epipe": "E-Line"}.get(svc.svc_type, svc.svc_type)
    return Panel(
        kv_table(
            [
                ("Class", f"{svc.svc_type}.{svc.svc_type.capitalize()}"),
                ("objectFullName", svc.fdn),
                ("id", svc.mgr_id),
                ("serviceId", svc.svc_id),
                ("displayedName", svc.name),
                ("Type (NFM-P / NSP)", f"{svc.svc_type.upper()} / {nsp_name}"),
                ("subscriberPointer", svc.subscriber_pointer),
                ("Customer", f"{svc.customer} ({svc.customer_id})"),
                ("Sites", ", ".join(svc.sites)),
                ("SDP IDs", ", ".join(str(i) for i in svc.sdp_ids) or "—"),
                ("Route Distinguisher", svc.route_distinguisher or "—"),
                ("MTU", svc.mtu),
                ("oosReasons", svc.oos_reasons or "—"),
                ("Description", svc.description),
                ("Administrative State", state(svc.admin)),
                ("Operational State", state(svc.oper)),
            ]
        ),
        title=f"Service  {svc.svc_id}",
        border_style="cyan",
    )


def show_site(site: ServiceSite) -> RenderableType:
    return kv_table(
        [
            ("Class", "service.Site"),
            ("objectFullName", site.fdn),
            ("siteId", site.site_id),
            ("NE", site.ne),
            ("MTU", site.mtu),
            ("Administrative State", state(site.admin)),
            ("Operational State", state(site.oper)),
        ],
        title="Service site",
    )


def show_sap(sap: AccessInterface) -> RenderableType:
    rows = [
        ("Class", "vprn.L3AccessInterface" if sap.layer == "l3" else "vpls.L2AccessInterface"),
        ("objectFullName", sap.fdn),
        ("SAP", sap.name),
        ("Port", sap.port),
        ("Site", sap.site_id),
        ("Layer", sap.layer),
        ("Encap", sap.encap),
        ("Outer tag", sap.outer_tag),
        ("primaryIPv4Address", sap.primary_ipv4 or "—"),
        ("Administrative State", state(sap.admin)),
        ("Operational State", state(sap.oper)),
    ]
    return Panel(kv_table(rows), title="Access interface (SAP)", border_style="cyan")


def show_binding(b: SdpBinding) -> RenderableType:
    return kv_table(
        [
            ("objectFullName", b.fdn),
            ("SDP ID", b.sdp_id),
            ("VC ID", b.vc_id),
            ("Type", b.binding_type),
            ("Site", b.site_id),
            ("Administrative State", state(b.admin)),
            ("Operational State", state(b.oper)),
        ],
        title="SDP binding",
    )


def show_alarm(alarm: Alarm) -> RenderableType:
    return Panel(
        kv_table(
            [
                ("Alarm ID", alarm.id),
                ("Severity", state(alarm.severity)),
                ("Probable Cause", alarm.probable_cause),
                ("Object", alarm.object_fdn),
                ("NE", alarm.ne),
                ("Raised", alarm.raised.strftime("%Y-%m-%d %H:%M:%SZ")),
                ("Acknowledged", "yes" if alarm.acked else "no"),
                ("Acked by", alarm.acked_by or "—"),
                ("Cleared", "yes" if alarm.cleared else "no"),
                ("Additional Text", alarm.additional_text),
            ]
        ),
        title="Alarm",
        border_style=SEV_STYLE.get(alarm.severity, "cyan"),
    )


def show_user(user: User) -> RenderableType:
    return kv_table(
        [
            ("Username", user.username),
            ("Display Name", user.display_name),
            ("User Group", user.group),
            ("Role", user.role),
            ("Account State", user.state),
            ("Access", user.access),
            ("Span of Control", ", ".join(user.span) or "ALL"),
            ("E-mail", user.email),
            ("Last Login", user.last_login.strftime("%Y-%m-%d %H:%M:%SZ") if user.last_login else "—"),
        ],
        title="User account",
    )


def ne_table(nes: Iterable[NetworkElement]) -> Table:
    t = Table(title="Network Elements", border_style="grey37")
    t.add_column("name", style="bold")
    t.add_column("system IP")
    t.add_column("type")
    t.add_column("version")
    t.add_column("group")
    t.add_column("site")
    t.add_column("mgmt")
    t.add_column("oper")
    for ne in nes:
        t.add_row(
            ne.name,
            ne.system_ip,
            ne.ne_type,
            ne.version,
            ne.group,
            ne.site,
            state(ne.management),
            state(ne.oper),
        )
    return t


def lsp_table(lsps: Iterable[Lsp]) -> Table:
    t = Table(title="MPLS LSPs", border_style="grey37")
    t.add_column("name", style="bold")
    t.add_column("type")
    t.add_column("sig")
    t.add_column("from")
    t.add_column("to")
    t.add_column("path")
    t.add_column("bw")
    t.add_column("prot")
    t.add_column("admin")
    t.add_column("oper")
    for lsp in lsps:
        t.add_row(
            lsp.name,
            lsp.lsp_type,
            lsp.signaling,
            lsp.from_ne,
            lsp.to_ne,
            lsp.path,
            str(lsp.bandwidth_mbps),
            lsp.protection,
            state(lsp.admin),
            state(lsp.oper),
        )
    return t


def customer_table(customers: Iterable[Customer], store: Any = None, user: Any = None) -> Table:
    t = Table(title="Customers  (subscr.Subscriber)", border_style="grey37")
    t.add_column("id", justify="right", style="bold")
    t.add_column("displayedName")
    t.add_column("objectFullName", style="dim")
    t.add_column("vprn")
    t.add_column("vpls")
    t.add_column("epipe")
    t.add_column("description")
    for c in customers:
        vprn = vpls = epipe = 0
        if store is not None and user is not None:
            for s in store.services_of(c.subscriber_id, user):
                if s.svc_type == "vprn":
                    vprn += 1
                elif s.svc_type == "vpls":
                    vpls += 1
                elif s.svc_type == "epipe":
                    epipe += 1
        t.add_row(
            str(c.subscriber_id),
            c.displayed_name,
            c.fdn,
            str(vprn),
            str(vpls),
            str(epipe),
            c.description,
        )
    return t


def service_table(svcs: Iterable[Service]) -> Table:
    t = Table(title="Services", border_style="grey37")
    t.add_column("serviceId", justify="right", style="bold")
    t.add_column("id", justify="right", style="dim")
    t.add_column("name", style="bold")
    t.add_column("type")
    t.add_column("customer")
    t.add_column("subscriberPointer", style="dim")
    t.add_column("sites")
    t.add_column("admin")
    t.add_column("oper")
    for s in svcs:
        t.add_row(
            str(s.svc_id),
            str(s.mgr_id),
            s.name,
            s.svc_type,
            f"{s.customer} ({s.customer_id})",
            s.subscriber_pointer,
            ",".join(s.sites),
            state(s.admin),
            state(s.oper),
        )
    return t


def alarm_table(alarms: Iterable[Alarm]) -> Table:
    t = Table(title="Alarms", border_style="grey37")
    t.add_column("id")
    t.add_column("sev")
    t.add_column("cause")
    t.add_column("object")
    t.add_column("NE")
    t.add_column("acked")
    t.add_column("raised")
    ordered = sorted(
        (a for a in alarms if not a.cleared),
        key=lambda a: (-SEVERITY_ORDER.get(a.severity, 0), a.raised),
    )
    for a in ordered:
        t.add_row(
            a.id,
            state(a.severity),
            a.probable_cause,
            a.object_fdn,
            a.ne,
            "yes" if a.acked else "no",
            a.raised.strftime("%H:%M:%SZ"),
        )
    if not ordered:
        t.add_row("—", "cleared", "no outstanding alarms", "", "", "", "")
    return t


def stats_table(samples: Iterable[StatSample], fdn: str) -> Table:
    t = Table(title=f"Performance statistics  {fdn}", border_style="grey37")
    t.add_column("counter")
    t.add_column("value", justify="right")
    t.add_column("unit")
    t.add_column("collected")
    rows = [s for s in samples if s.object_fdn == fdn]
    for s in rows:
        val = f"{s.value:,.0f}" if s.value >= 100 else f"{s.value:.1f}"
        t.add_row(s.counter, val, s.unit, s.collected.strftime("%H:%M:%SZ"))
    if not rows:
        t.add_row("(none)", "", "", "no MIB policy match")
    return t


def topology_ascii() -> RenderableType:
    art = Text.from_markup(
        """
[bold cyan]Physical / IGP topology[/]  (lab ARGENTINA)

                    [green]PE-SALTA-01[/]
                         |
                    [green]P-CORE-01[/]────────[green]P-CORE-02[/]
                    /    |    \\              \\
         [green]PE-BAIRES-01[/]  [yellow]PE-MENDOZA-01[/]     [green]PE-CORDOBA-01[/]
                |
         [green]PE-BAIRES-02[/]
                |
         [green]PE-ROSARIO-01[/]

  [green]green[/] oper-up    [yellow]yellow[/] degraded    [red]red[/] oper-down
  RSVP-TE: lsp-ba-cba, lsp-core-p2p, lsp-ba-sal [red](down)[/]
  SR-TE:   lsp-ba-mza-sr
  LDP:     lsp-ba-ros
"""
    )
    return Panel(art, border_style="cyan", title="Application → Topology")


def help_text() -> RenderableType:
    flow = Table(title="Shell  user@NSP  ·  nested like Fire / SR OS", border_style="grey37")
    flow.add_column("you type", style="bold cyan")
    flow.add_column("prompt becomes")
    for cmd, desc in [
        ("(login)", "admin@172.24.80.28> "),
        ("customers", "admin@172.24.80.28>customers> "),
        ("12", "admin@172.24.80.28>customers>12> "),
        ("vprn 100", "admin@172.24.80.28>customers>12>vprn>100> "),
        ("sites", "…>100>sites>   (or one-liner: customers 12 vprn 100 sites)"),
        ("exit", "up one level   ·   exit all / top = root"),
        ("logout", "end session"),
    ]:
        flow.add_row(cmd, desc)

    nav = Table(title="At any context", border_style="grey37")
    nav.add_column("command", style="bold cyan")
    nav.add_column("what it does")
    for cmd, desc in [
        ("?  or  ls", "list children of this context"),
        ("info  or  show", "property form of current object"),
        ("<name>", "enter that child (Fire-style)"),
        ("exit", "go up (like a router CLI)"),
        ("find <text>", "search customers, services, IPs, MACs"),
    ]:
        nav.add_row(cmd, desc)

    slash = Table(title="Slash commands  (type /  ·  Tab completes)", border_style="grey37")
    slash.add_column("command", style="bold cyan")
    slash.add_column("what it does")
    for cmd, desc in [
        ("/customers", "list subscr.Subscriber"),
        ("/customer <id>", "open customer (VPRN/VPLS/Epipe counts)"),
        ("/services [id]", "services, optionally of one customer"),
        ("/help", "this help"),
        ("/status", "session summary"),
        ("/alarms", "faults"),
        ("/ne", "network elements"),
        ("/mpls", "transport LSPs / tunnels"),
        ("/quit", "end session"),
    ]:
        slash.add_row(cmd, desc)

    related = Table(title="Related objects under a service", border_style="grey37")
    related.add_column("folder", style="bold cyan")
    related.add_column("NFM-P class / API")
    for cmd, desc in [
        ("sites", "vprn.Site / vpls.Site / epipe.Site  svc-mgr:service-<id>:<ip>  (id NFM-P ≠ serviceId)"),
        ("saps", "L3AccessInterface or L2AccessInterface (SAP)"),
        ("sdp-bindings", "spoke/mesh SDP binding"),
        ("tunnels", "svt.Tunnel (SDP)"),
        ("lsps", "mpls.DynamicLsp under those SDPs"),
        ("alarms", "fm.AlarmObject on the service"),
        ("route-targets / static-routes / bgp-peers", "VPRN only"),
        ("mac-table", "VPLS FIB / ProxyArpNdMacAddress"),
    ]:
        related.add_row(cmd, desc)

    return Group(flow, nav, slash, related)


def _object_state(payload: Any) -> str:
    if payload is None:
        return ""
    if isinstance(payload, Alarm):
        return payload.severity if not payload.cleared else "cleared"
    for attr in ("oper", "management", "state"):
        if hasattr(payload, attr):
            return str(getattr(payload, attr))
    return ""
