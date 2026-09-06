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
    BgpRibInfo,
    BgpRibPrefix,
    Cpaa,
    RouteNextHop,
    TopologyAs,
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
        ("Shell de gestión clásica  ·  IP/MPLS", "dim"),
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
        return Text(f"(vacío)  {pwd(path)}", style="dim")
    table = Table(
        title=f"{pwd(path)}  [{node.kind}]",
        expand=False,
        border_style="grey37",
    )
    table.add_column("nombre", style="bold")
    table.add_column("tipo", style="cyan")
    table.add_column("etiqueta")
    table.add_column("estado")
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
    if isinstance(payload, TopologyAs):
        return kv_table(
            [
                (
                    "Clase",
                    "topology.AutonomousSystem"
                    if payload.kind == "igp"
                    else "topology.BgpAutonomousSystem",
                ),
                ("objectFullName", payload.fdn),
                ("displayedName", payload.displayed_name),
                ("asNumber", payload.as_number),
                ("asType", payload.as_type or "—"),
                ("description", payload.description or "—"),
                ("bgpTopologyEnabled", payload.bgp_topology_enabled or "—"),
                ("igpAdminDomain", payload.igp_admin_domain or "—"),
                ("cpaaPointers", payload.cpaa_pointers or "—"),
            ],
            title="AS IGP (query 11)" if payload.kind == "igp" else "AS BGP (query 12)",
        )
    if isinstance(payload, Cpaa):
        return kv_table(
            [
                ("Clase", "topology.Cpaa"),
                ("objectFullName", payload.fdn),
                ("displayedName", payload.displayed_name),
                ("routerId", payload.router_id),
                ("bgpAsPointer", payload.bgp_as),
                ("protocolRecord", payload.protocol_record or "—"),
                ("protocolEventTypes", payload.protocol_events or "—"),
                ("bgpRibInfoLastRetrieveTime", payload.rib_retrieve),
                ("bgpVpnv4RoutTargetLastRetrieveTime", payload.rt_retrieve),
                ("Estado administrativo", state(payload.admin)),
                ("Estado operacional", state(payload.oper)),
            ],
            title="CPAA (query 10)",
        )
    if isinstance(payload, BgpRibInfo):
        return kv_table(
            [
                ("Clase", "topology.BgpRibInfo"),
                ("objectFullName", payload.fdn),
                ("Tipo", payload.kind),
                ("Clave", payload.key),
                ("asNumber", payload.as_number or "—"),
                ("numRoutes", payload.num_routes),
                ("Servicio", payload.svc_id),
            ],
            title="RIB-IN agrupado (query 13)",
        )
    if isinstance(payload, BgpRibPrefix):
        return kv_table(
            [
                ("Clase", payload.source),
                ("prefType", payload.pref_type),
                ("prefRD", payload.rd),
                ("Prefijo", payload.prefix),
                ("Next hop", payload.next_hop or "—"),
                ("MED", payload.med or "—"),
                ("LOCAL-PREF", payload.local_pref or "—"),
                ("AS_PATH", payload.as_path or "—"),
                ("PEER", payload.peer or "—"),
                ("ORIGINATOR-ID", payload.originator_id or "—"),
                ("Servicio", payload.svc_id),
            ],
            title="Prefijo BGP (CPAM)",
        )
    if isinstance(payload, RouteTarget):
        return kv_table(
            [
                ("Dirección", payload.direction),
                ("Route Target", payload.value),
                ("Next-hops (CPAM)", payload.num_next_hops),
                ("Servicio", payload.svc_id),
            ]
        )
    if isinstance(payload, RouteNextHop):
        return kv_table(
            [
                ("Clase", "topology.BgpRoutesNextHop"),
                ("Route Target", payload.route_target),
                ("nextHop (PE)", payload.next_hop),
                ("nextHopAddrType", payload.addr_type),
                ("siteId (CPAA, no el PE)", payload.cpaa_site_id or "—"),
                ("Servicio", payload.svc_id),
            ],
            title="Next-hop VPN (CPAM)",
        )
    if isinstance(payload, StaticRoute):
        return kv_table(
            [
                ("Prefijo", payload.prefix),
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
                ("Puerto", payload.port),
                ("Site", payload.site_id),
                ("Origen", payload.source),
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
            ("Nombre", ne.name),
            ("IP de sistema", ne.system_ip),
            ("Tipo de chasis", ne.ne_type),
            ("Versión de software", ne.version),
            ("Sitio", ne.site),
            ("Grupo de equipo", ne.group),
            ("MAC del chasis", ne.chassis_mac),
            ("Estado administrativo", state(ne.admin)),
            ("Estado operacional", state(ne.oper)),
            ("Estado de gestión", state(ne.management)),
            ("Protocolos", ", ".join(p.upper() for p in ne.protocols)),
            ("Tarjetas / puertos", f"{len(ne.cards)} / {ports}"),
        ]
    )
    cards = Table(title="Tarjetas", border_style="grey37")
    cards.add_column("slot")
    cards.add_column("tipo")
    cards.add_column("admin")
    cards.add_column("oper")
    cards.add_column("puertos")
    for c in ne.cards:
        cards.add_row(c.slot, c.card_type, state(c.admin), state(c.oper), str(len(c.ports)))
    return Panel(Group(general, cards), title=f"Propiedades del NE  {ne.name}", border_style="cyan")


def show_card(card: Card) -> RenderableType:
    t = Table(title=f"Tarjeta slot {card.slot}", border_style="grey37")
    t.add_column("puerto")
    t.add_column("modo")
    t.add_column("encap")
    t.add_column("velocidad")
    t.add_column("admin")
    t.add_column("oper")
    for p in card.ports:
        t.add_row(p.name, p.mode, p.encap, p.speed, state(p.admin), state(p.oper))
    head = kv_table(
        [
            ("Slot", card.slot),
            ("Tipo de tarjeta", card.card_type),
            ("Equipada", card.equipped),
            ("Estado administrativo", state(card.admin)),
            ("Estado operacional", state(card.oper)),
        ]
    )
    return Group(head, t)


def show_port(port: Port) -> RenderableType:
    return Panel(
        kv_table(
            [
                ("Puerto", port.name),
                ("Modo", port.mode),
                ("Encap", port.encap),
                ("Velocidad", port.speed),
                ("LAG", port.lag or "—"),
                ("Descripción", port.description),
                ("Estado administrativo", state(port.admin)),
                ("Estado operacional", state(port.oper)),
            ]
        ),
        title="Propiedades del puerto",
        border_style="cyan",
    )


def show_lsp(lsp: Lsp) -> RenderableType:
    hops = " → ".join(lsp.hops) if lsp.hops else "(loose)"
    return Panel(
        kv_table(
            [
                ("Nombre", lsp.name),
                ("Tipo", lsp.lsp_type),
                ("Señalización", lsp.signaling.upper()),
                ("From", lsp.from_ne),
                ("To", lsp.to_ne),
                ("Path", lsp.path),
                ("Hops", hops),
                ("Métrica", lsp.metric),
                ("Ancho de banda", f"{lsp.bandwidth_mbps} Mbps"),
                ("Setup / Hold", f"{lsp.setup_priority} / {lsp.hold_priority}"),
                ("Protección", lsp.protection),
                ("Estado administrativo", state(lsp.admin)),
                ("Estado operacional", state(lsp.oper)),
                ("FDN", lsp.fdn or "—"),
            ]
        ),
        title=f"LSP  {lsp.name}",
        border_style="cyan",
    )


def show_path(path: MplsPath) -> RenderableType:
    hops = " → ".join(path.hops) if path.hops else "(ninguno)"
    return kv_table(
        [("Nombre", path.name), ("Tipo de hop", path.hop_type), ("Hops", hops)],
        title="Path MPLS",
    )


def show_mpls_if(iface: MplsInterface) -> RenderableType:
    return kv_table(
        [
            ("NE", iface.ne),
            ("Interfaz MPLS", iface.name),
            ("Interfaz L3 asociada", iface.interface),
            ("Métrica TE", iface.te_metric),
            ("SRLG", ", ".join(iface.srlgs) or "—"),
            ("Estado administrativo", state(iface.admin)),
            ("Estado operacional", state(iface.oper)),
        ]
    )


def show_sdp(sdp: ServiceTunnel) -> RenderableType:
    return kv_table(
        [
            ("SDP ID", sdp.sdp_id),
            ("Nombre", sdp.name),
            ("From", sdp.from_ne),
            ("To", sdp.to_ne),
            ("Far End", sdp.far_end),
            ("Señalización", sdp.signaling),
            ("LSP", sdp.lsp),
            ("Estado administrativo", state(sdp.admin)),
            ("Estado operacional", state(sdp.oper)),
        ],
        title="Túnel de servicio (SDP)",
    )


def show_customer(cust: Customer) -> RenderableType:
    return Panel(
        kv_table(
            [
                ("Clase", "subscr.Subscriber"),
                ("objectFullName", cust.fdn),
                ("subscriberId", cust.subscriber_id),
                ("displayedName", cust.displayed_name),
                ("Descripción", cust.description),
                ("Contacto", cust.contact),
            ]
        ),
        title=f"Cliente  {cust.subscriber_id}",
        border_style="cyan",
    )


def show_service(svc: Service) -> RenderableType:
    nsp_name = {"vprn": "L3 VPN", "vpls": "E-LAN", "epipe": "E-Line"}.get(svc.svc_type, svc.svc_type)
    return Panel(
        kv_table(
            [
                ("Clase", f"{svc.svc_type}.{svc.svc_type.capitalize()}"),
                ("objectFullName", svc.fdn),
                ("id (NFM-P)", svc.mgr_id),
                ("serviceId (NE)", svc.svc_id),
                ("displayedName", svc.name),
                ("Tipo (NFM-P / NSP)", f"{svc.svc_type.upper()} / {nsp_name}"),
                ("subscriberPointer", svc.subscriber_pointer),
                ("Cliente", f"{svc.customer} ({svc.customer_id})"),
                ("Sites", ", ".join(svc.sites)),
                ("SDP IDs", ", ".join(str(i) for i in svc.sdp_ids) or "—"),
                ("Route Distinguisher", svc.route_distinguisher or "—"),
                ("MTU", svc.mtu),
                ("oosReasons", svc.oos_reasons or "—"),
                ("Descripción", svc.description),
                ("Estado administrativo", state(svc.admin)),
                ("Estado operacional", state(svc.oper)),
            ]
        ),
        title=f"Servicio  {svc.svc_id}",
        border_style="cyan",
    )


def show_site(site: ServiceSite) -> RenderableType:
    return kv_table(
        [
            ("Clase", "service.Site"),
            ("objectFullName", site.fdn),
            ("siteId", site.site_id),
            ("NE", site.ne),
            ("MTU", site.mtu),
            ("Estado administrativo", state(site.admin)),
            ("Estado operacional", state(site.oper)),
        ],
        title="Site del servicio",
    )


def show_sap(sap: AccessInterface) -> RenderableType:
    rows = [
        ("Clase", "vprn.L3AccessInterface" if sap.layer == "l3" else "vpls.L2AccessInterface"),
        ("objectFullName", sap.fdn),
        ("SAP", sap.name),
        ("Puerto", sap.port),
        ("portPointer", sap.port_pointer or "—"),
        ("Site", sap.site_id),
        ("Capa", sap.layer),
        ("Encap", sap.encap),
        ("Tag externo", sap.outer_tag),
        ("primaryIPv4Address", sap.primary_ipv4 or "—"),
        ("Estado administrativo", state(sap.admin)),
        ("Estado operacional", state(sap.oper)),
    ]
    return Panel(kv_table(rows), title="Interfaz de acceso (SAP)", border_style="cyan")


def show_binding(b: SdpBinding) -> RenderableType:
    return kv_table(
        [
            ("objectFullName", b.fdn),
            ("SDP ID", b.sdp_id),
            ("VC ID", b.vc_id),
            ("Tipo", b.binding_type),
            ("Site", b.site_id),
            ("Far-end", b.far_end or "—"),
            ("Estado administrativo", state(b.admin)),
            ("Estado operacional", state(b.oper)),
        ],
        title="SDP binding",
    )


def show_alarm(alarm: Alarm) -> RenderableType:
    return Panel(
        kv_table(
            [
                ("ID de alarma", alarm.id),
                ("Severidad", state(alarm.severity)),
                ("Causa probable", alarm.probable_cause),
                ("Objeto", alarm.object_fdn),
                ("NE", alarm.ne),
                ("Levantada", alarm.raised.strftime("%Y-%m-%d %H:%M:%SZ")),
                ("Reconocida", "sí" if alarm.acked else "no"),
                ("Reconocida por", alarm.acked_by or "—"),
                ("Limpiada", "sí" if alarm.cleared else "no"),
                ("Texto adicional", alarm.additional_text),
            ]
        ),
        title="Alarma",
        border_style=SEV_STYLE.get(alarm.severity, "cyan"),
    )


def show_user(user: User) -> RenderableType:
    return kv_table(
        [
            ("Usuario", user.username),
            ("Nombre", user.display_name),
            ("Grupo", user.group),
            ("Rol", user.role),
            ("Estado de la cuenta", user.state),
            ("Acceso", user.access),
            ("Span of Control", ", ".join(user.span) or "ALL"),
            ("Correo", user.email),
            ("Último login", user.last_login.strftime("%Y-%m-%d %H:%M:%SZ") if user.last_login else "—"),
        ],
        title="Cuenta de usuario",
    )


def ne_table(nes: Iterable[NetworkElement]) -> Table:
    t = Table(title="Elementos de red", border_style="grey37")
    t.add_column("nombre", style="bold")
    t.add_column("IP de sistema")
    t.add_column("tipo")
    t.add_column("versión")
    t.add_column("grupo")
    t.add_column("sitio")
    t.add_column("gestión")
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
    t = Table(title="LSPs MPLS", border_style="grey37")
    t.add_column("nombre", style="bold")
    t.add_column("tipo")
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
    t = Table(title="Clientes  (subscr.Subscriber)", border_style="grey37")
    t.add_column("id", justify="right", style="bold")
    t.add_column("displayedName")
    t.add_column("objectFullName", style="dim")
    t.add_column("vprn")
    t.add_column("vpls")
    t.add_column("epipe")
    t.add_column("descripción")
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
    t = Table(title="Servicios", border_style="grey37")
    t.add_column("serviceId", justify="right", style="bold")
    t.add_column("id", justify="right", style="dim")
    t.add_column("nombre", style="bold")
    t.add_column("tipo")
    t.add_column("cliente")
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
    t = Table(title="Alarmas", border_style="grey37")
    t.add_column("id")
    t.add_column("sev")
    t.add_column("causa")
    t.add_column("objeto")
    t.add_column("NE")
    t.add_column("ack")
    t.add_column("levantada")
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
            "sí" if a.acked else "no",
            a.raised.strftime("%H:%M:%SZ"),
        )
    if not ordered:
        t.add_row("—", "cleared", "sin alarmas pendientes", "", "", "", "")
    return t


def stats_table(samples: Iterable[StatSample], fdn: str) -> Table:
    t = Table(title=f"Estadísticas de performance  {fdn}", border_style="grey37")
    t.add_column("contador")
    t.add_column("valor", justify="right")
    t.add_column("unidad")
    t.add_column("recogido")
    rows = [s for s in samples if s.object_fdn == fdn]
    for s in rows:
        val = f"{s.value:,.0f}" if s.value >= 100 else f"{s.value:.1f}"
        t.add_row(s.counter, val, s.unit, s.collected.strftime("%H:%M:%SZ"))
    if not rows:
        t.add_row("(ninguno)", "", "", "sin coincidencia de política MIB")
    return t


def topology_ascii() -> RenderableType:
    art = Text.from_markup(
        """
[bold cyan]Topología física / IGP[/]  (lab ARGENTINA)

                    [green]PE-SALTA-01[/]
                         |
                    [green]P-CORE-01[/]────────[green]P-CORE-02[/]
                    /    |    \\              \\
         [green]PE-BAIRES-01[/]  [yellow]PE-MENDOZA-01[/]     [green]PE-CORDOBA-01[/]
                |
         [green]PE-BAIRES-02[/]
                |
         [green]PE-ROSARIO-01[/]

  [green]verde[/] oper-up    [yellow]amarillo[/] degraded    [red]rojo[/] oper-down
  RSVP-TE: lsp-ba-cba, lsp-core-p2p, lsp-ba-sal [red](down)[/]
  SR-TE:   lsp-ba-mza-sr
  LDP:     lsp-ba-ros
"""
    )
    return Panel(art, border_style="cyan", title="Aplicación → Topología")


def sap_create_help() -> RenderableType:
    """Jerarquía NFM-P y comportamiento al crear un SAP."""
    schema = Text.from_markup(
        """\
[bold cyan]netw.NetworkElement[/]              siteId = system IP del router
        │
        └── [bold cyan]vprn.Site / vpls.Site / epipe.Site[/]
                FDN  [bold]svc-mgr:service-<id>:<siteId>[/]
                siteId = [bold]la misma IP del NE[/]
                    │
                    └── [bold cyan]L3/L2AccessInterface[/]  (SAP)
                            portPointer → [bold]equipment.PhysicalPort[/]
                            de [bold]ESE mismo NE[/]
                            [dim]network:<siteId>:shelf-…:port-N[/]
"""
    )
    steps = Table(title="Comportamiento NFM-P al crear el SAP", border_style="grey37")
    steps.add_column("#", style="bold cyan", justify="right")
    steps.add_column("qué hace")
    for n, desc in [
        (
            "1",
            "El servicio (vprn.Vprn / vpls.Vpls / epipe.Epipe) vive en svc-mgr. "
            "Todavía no está en ningún router.",
        ),
        (
            "2",
            "El site es «este servicio en este NE». siteId no es un nombre libre: "
            "es el system IP del NetworkElement. Sin NE con esa IP, el site no se crea.",
        ),
        (
            "3",
            "El SAP no cuelga del servicio suelto: cuelga del site. "
            "El distinguishedName de create es svc-mgr:service-<id>:<siteId>.",
        ),
        (
            "4",
            "portPointer tiene que ser un puerto access/hybrid de ese NE. "
            "NFM-P no deja un puerto de otro router.",
        ),
        (
            "5",
            "En VPRN la IP (rtr.VirtualRouterIpAddress) es hija del L3 Access Interface, "
            "no del site. Por eso ip=a.b.c.d/p es obligatorio en VPRN.",
        ),
    ]:
        steps.add_row(n, desc)

    uso = Table(title="Uso", border_style="grey37")
    uso.add_column("comando", style="bold cyan")
    uso.add_column("detalle")
    for cmd, desc in [
        (
            "sap create service=<id> site=<NE|IP> port=<puerto|FDN> vlan=<n> [ip=cidr]",
            "site= se traduce al system IP del NE; pide confirmación",
        ),
        (
            "create sap site=NE port=P vlan=V ip=…",
            "desde el contexto del servicio (customers>12>vprn>100>)",
        ),
        ("sap shutdown|delete <nombre>", "piden confirmación"),
        ("sap turnup <nombre>", "no pide confirmación"),
        ("VPRN", "vprn.L3AccessInterface + rtr.VirtualRouterIpAddress"),
        ("VPLS", "vpls.L2AccessInterface"),
        ("Epipe", "vll.L2AccessInterface"),
        ("confirm=yes", "batch / script; en el REPL pregunta [sí/no]"),
    ]:
        uso.add_row(cmd, desc)

    nota = Text.from_markup(
        "[dim]Resumen: site = servicio × NE. El SAP siempre pertenece a un site, "
        "y por tanto a un NE. site=PE-BAIRES-01 es un atajo al siteId (system IP).[/]"
    )
    return Group(
        Panel(schema, title="Create SAP — jerarquía NFM-P", border_style="cyan"),
        steps,
        uso,
        nota,
    )


def sdp_create_help() -> RenderableType:
    """Jerarquía NFM-P y comportamiento al crear un SDP binding."""
    schema = Text.from_markup(
        """\
[bold cyan]netw.NetworkElement[/]              site origen (system IP)
        │
        └── [bold cyan]vprn.Site / vpls.Site / epipe.Site[/]
                FDN  [bold]svc-mgr:service-<id>:<siteId>[/]
                    │
                    └── [bold cyan]svt.SpokeSdpBinding / svt.MeshSdpBinding[/]
                            tunnelSelectionTerminationSiteId
                            = system IP del [bold]NE far-end[/]
                            sdpId / vcId opcionales
                            el túnel (svt.Tunnel) ya debe existir
                            entre esos dos NEs
"""
    )
    steps = Table(title="Comportamiento NFM-P al crear el SDP binding", border_style="grey37")
    steps.add_column("#", style="bold cyan", justify="right")
    steps.add_column("qué hace")
    for n, desc in [
        (
            "1",
            "El SDP binding asocia un túnel de servicio (SDP) a un servicio distribuido. "
            "Solo hace falta si el servicio cruza más de un NE.",
        ),
        (
            "2",
            "Cuelga del site de origen, igual que el SAP. "
            "distinguishedName = svc-mgr:service-<id>:<siteId>.",
        ),
        (
            "3",
            "tunnelSelectionTerminationSiteId es el system IP del NE destino (far-end), "
            "no un nombre libre.",
        ),
        (
            "4",
            "VPRN y Epipe usan spoke (svt.SpokeSdpBinding). "
            "VPLS admite mesh (svt.MeshSdpBinding) o spoke; el default en VPLS es mesh.",
        ),
        (
            "5",
            "sdp=<id> apunta a un svt.Tunnel existente. vc= default = serviceId del NE. "
            "Si el site de origen no existe, se crea.",
        ),
    ]:
        steps.add_row(n, desc)

    uso = Table(title="Uso", border_style="grey37")
    uso.add_column("comando", style="bold cyan")
    uso.add_column("detalle")
    for cmd, desc in [
        (
            "sdp create service=<id> site=<NE> far=<NE> [sdp=<id>] [vc=<id>] [type=spoke|mesh]",
            "pide confirmación",
        ),
        (
            "create sdp site=NE far=NE sdp=101",
            "desde el contexto del servicio",
        ),
        ("sdp shutdown|delete <sdp-id>", "piden confirmación"),
        ("sdp turnup <sdp-id>", "no pide confirmación"),
        ("confirm=yes", "batch / script; en el REPL pregunta [sí/no]"),
    ]:
        uso.add_row(cmd, desc)

    nota = Text.from_markup(
        "[dim]Resumen: binding = servicio × site origen × NE far-end. "
        "El SAP es el acceso del cliente; el SDP binding es el transporte entre NEs.[/]"
    )
    return Group(
        Panel(schema, title="Create SDP binding — jerarquía NFM-P", border_style="cyan"),
        steps,
        uso,
        nota,
    )


def tunnel_create_help() -> RenderableType:
    schema = Text.from_markup(
        """\
[bold cyan]svt.Manager[/]                      FDN [bold]serviceTunnel[/]
        │
        └── [bold cyan]svt.Tunnel[/]                 túnel SDP (unidireccional)
                FDN  [bold]serviceTunnel:from-<srcIp>-id-<sdpId>[/]
                sourceNodeId     = system IP del NE origen
                farEndIpAddress  = system IP del NE destino
                lspPointer       = LSP MPLS de origen→destino (opcional)
                    │
                    └── lo usa [bold]svt.SpokeSdpBinding[/] (sdpId)
                            en el site del servicio
"""
    )
    steps = Table(title="Comportamiento NFM-P al crear el túnel SDP", border_style="grey37")
    steps.add_column("#", style="bold cyan", justify="right")
    steps.add_column("qué hace")
    for n, desc in [
        (
            "1",
            "El túnel SDP (svt.Tunnel) es transporte entre dos NEs, independiente del "
            "servicio. Es unidireccional: A→B no cubre B→A.",
        ),
        (
            "2",
            "Se crea bajo svt.Manager (FDN serviceTunnel), no bajo el servicio. "
            "El binding del servicio apunta a este túnel con sdp=<id>.",
        ),
        (
            "3",
            "from= y to= son NEs distintos (system IP). Para MPLS, lsp= debe ser un "
            "LSP que ya vaya de from a to.",
        ),
        (
            "4",
            "id= es el SDP id en el NE origen. Tiene que ser único en ese origen.",
        ),
    ]:
        steps.add_row(n, desc)
    uso = Table(title="Uso", border_style="grey37")
    uso.add_column("comando", style="bold cyan")
    uso.add_column("detalle")
    for cmd, desc in [
        (
            "tunnel create from=<NE> to=<NE> id=<sdpId> [lsp=<nombre>] [sig=tldp]",
            "pide confirmación",
        ),
        ("create tunnel from=NE to=NE id=N", "desde mpls/tunnels"),
        ("tunnel shutdown|delete <id>", "piden confirmación"),
        ("Tab", "completa NEs, LSPs from→to y sdp ids existentes"),
    ]:
        uso.add_row(cmd, desc)
    nota = Text.from_markup(
        "[dim]Orden de red: LSP (opcional) → túnel SDP → SDP binding en el site del servicio → SAP.[/]"
    )
    return Group(
        Panel(schema, title="Create túnel SDP — jerarquía NFM-P", border_style="cyan"),
        steps,
        uso,
        nota,
    )


def help_text() -> RenderableType:
    flow = Table(title="Shell  user@NSP  ·  anidado como Fire / SR OS", border_style="grey37")
    flow.add_column("escribís", style="bold cyan")
    flow.add_column("el prompt queda")
    for cmd, desc in [
        ("(login)", "admin@172.24.80.28> "),
        ("customers", "admin@172.24.80.28>customers> "),
        ("12", "admin@172.24.80.28>customers>12> "),
        ("vprn 100", "admin@172.24.80.28>customers>12>vprn>100> "),
        ("sites", "…>100>sites>   (o en una línea: customers 12 vprn 100 sites)"),
        ("exit", "sube un nivel   ·   exit all / top = raíz"),
        ("logout  /  quit", "cierra la sesión"),
        ("Ctrl-C", "cancela y cierra"),
        ("Ctrl-D", "cierra la sesión (EOF)"),
    ]:
        flow.add_row(cmd, desc)

    nav = Table(title="En cualquier contexto", border_style="grey37")
    nav.add_column("comando", style="bold cyan")
    nav.add_column("qué hace")
    for cmd, desc in [
        ("?  o  ls", "lista los hijos de este contexto"),
        ("info  o  show", "formulario de propiedades del objeto actual"),
        ("<nombre>", "entra a ese hijo (estilo Fire)"),
        ("exit", "sube un nivel (como CLI de router)"),
        ("find <texto>", "busca clientes, servicios, IPs, MACs"),
        ("tree [n]", "árbol de hijos (profundidad 1–6)"),
        ("pwd", "muestra el prompt / ruta actual"),
        ("debug [on|off]", "imprime cada petición HTTP"),
    ]:
        nav.add_row(cmd, desc)

    slash = Table(title="Comandos con /  (escribí /  ·  Tab completa)", border_style="grey37")
    slash.add_column("comando", style="bold cyan")
    slash.add_column("qué hace")
    for cmd, desc in [
        ("/customers", "lista subscr.Subscriber"),
        ("/customer <id>", "abre un cliente (conteo VPRN/VPLS/Epipe)"),
        ("/services [id]", "servicios; con id, los de ese cliente"),
        ("/ne [nombre|IP]", "elementos de red (span of control)"),
        ("/mpls [lsps|paths|tunnels|interfaces]", "transporte MPLS (live por NE)"),
        ("/service create type=vprn|vpls|epipe id=N customer=C name=X", "crea servicio (pide confirmación)"),
        ("/sap create service=N site=NE port=P vlan=V [ip=a.b.c.d/p]", "crea SAP (pide confirmación)"),
        ("/sdp create service=N site=NE far=NE [sdp=id] [type=spoke|mesh]", "crea SDP binding (pide confirmación)"),
        ("/tunnel create from=NE to=NE id=N [lsp=nombre]", "crea túnel SDP svt.Tunnel (pide confirmación)"),
        ("/service shutdown|turnup|delete <id>", "admin servicio (shutdown/delete piden confirmación)"),
        ("/sap shutdown|turnup|delete <nombre>", "admin SAP (shutdown/delete piden confirmación)"),
        ("/sdp shutdown|turnup|delete <sdp-id>", "admin SDP binding (shutdown/delete piden confirmación)"),
        ("/alarms [list|ack|clear|sev]", "fallas (live: fm.AlarmObject por NE)"),
        ("/mpls lsp create name=X from=NE to=NE", "crea LSP (pide confirmación)"),
        ("/mpls lsp shutdown|turnup|delete <n>", "admin LSP (shutdown/delete piden confirmación)"),
        ("/stats <fdn>", "stats live: find log record + timeCaptured (15 min)"),
        ("/topology", "topología ASCII del lab"),
        ("/tasks", "gestor de tareas de esta sesión"),
        ("/users", "usuarios locales (solo admin)"),
        ("/resync [NE…]", "resincroniza NE(s)"),
        ("/passwd <actual> <nueva>", "cambia la contraseña"),
        ("/whoami", "usuario, rol, span of control"),
        ("/status", "resumen de sesión"),
        ("/debug [on|off]", "traza HTTP"),
        ("/cpaa [show]", "estado del CPAA (query 10)"),
        ("/cpaa record bgp [fdn]", "query 17: agrega bgp a protocolRecord (write)"),
        ("/clear", "limpia la pantalla"),
        ("/help", "esta ayuda"),
        ("/quit  /logout", "cierra la sesión"),
    ]:
        slash.add_row(cmd, desc)

    related = Table(title="Objetos bajo un servicio", border_style="grey37")
    related.add_column("carpeta", style="bold cyan")
    related.add_column("clase NFM-P / API")
    for cmd, desc in [
        ("sites", "vprn.Site / vpls.Site / epipe.Site  FDN svc-mgr:service-<id>:<ip>"),
        ("saps", "L3AccessInterface o L2AccessInterface (SAP)"),
        ("sdp-bindings", "svt.SpokeSdpBinding / svt.MeshSdpBinding (hijo del site)"),
        ("tunnels", "svt.Tunnel (SDP)"),
        ("lsps", "mpls.DynamicLsp de esos SDP"),
        ("alarms", "fm.AlarmObject del servicio"),
        ("route-targets / bgp-rib / bgp-rib-info", "VPRN: RT, prefijos RIB (13/14), agrupación RIB-IN"),
        ("mac-table", "VPLS FIB / ProxyArpNdMacAddress"),
    ]:
        related.add_row(cmd, desc)

    ids = Table(title="IDs de servicio y arranque", border_style="grey37")
    ids.add_column("tema", style="bold cyan")
    ids.add_column("detalle")
    for cmd, desc in [
        ("serviceId", "ID del servicio en el NE; es el que se navega (vprn 10)"),
        ("id", "ID interno NFM-P; arma el FDN svc-mgr:service-<id>"),
        ("--host", "IP del NSP en el prompt (user@host>)"),
        ("--user / --password", "login no interactivo"),
        ("--debug", "traza cada petición HTTP"),
        ("--offline", "no contacta el NSP; usa el inventario lab"),
        ("--batch / --script", "ejecuta comandos y sale"),
        ("backend live", "OAuth2 + SAM-O find contra --host"),
        ("backend lab", "inventario local si el NSP no responde o --offline"),
    ]:
        ids.add_row(cmd, desc)

    return Group(
        flow, nav, slash, related, ids, sap_create_help(), sdp_create_help(), tunnel_create_help()
    )


def _object_state(payload: Any) -> str:
    if payload is None:
        return ""
    if isinstance(payload, Alarm):
        return payload.severity if not payload.cleared else "cleared"
    for attr in ("oper", "management", "state"):
        if hasattr(payload, attr):
            return str(getattr(payload, attr))
    return ""
