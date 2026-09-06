"""In-memory demo lab: Argentina IP/MPLS core managed by NFM-P 24.11."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from nsp_grok.auth import hash_password
from nsp_grok.models import (
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


def _ts(hours_ago: float) -> datetime:
    return datetime.now(timezone.utc) - timedelta(hours=hours_ago)


def _user(username: str, password: str, **kwargs) -> User:
    digest, salt = hash_password(password)
    return User(
        username=username,
        password_hash=digest,
        salt=salt,
        password_history=[digest],
        **kwargs,
    )


def _ports(names: list[tuple[str, str, str, str, str]]) -> list[Port]:
    out: list[Port] = []
    for name, mode, speed, admin, oper in names:
        encap = "null" if mode == "network" else "dot1q"
        out.append(
            Port(
                name=name,
                mode=mode,
                encap=encap,
                admin=admin,  # type: ignore[arg-type]
                oper=oper,  # type: ignore[arg-type]
                speed=speed,
                description=f"{mode} {name}",
            )
        )
    return out


def _line_card(slot: str, card_type: str, ports: list[Port]) -> Card:
    down = any(p.oper == "down" for p in ports)
    return Card(
        slot=slot,
        card_type=card_type,
        equipped=card_type,
        admin="up",
        oper="degraded" if down else "up",
        ports=ports,
    )


def seed_users() -> dict[str, User]:
    users = [
        _user(
            "admin",
            "Nokia1234!",
            group="administrators",
            role="administrator",
            display_name="NSP Administrator",
            email="admin@lab.nsp",
            access="execute",
        ),
        _user(
            "operator",
            "Nokia1234!",
            group="ip-mpls-ops",
            role="operator",
            display_name="MPLS Operator",
            email="operator@lab.nsp",
            access="write",
        ),
        _user(
            "noc",
            "Nokia1234!",
            group="noc-ba",
            role="fault-manager",
            display_name="NOC Buenos Aires",
            email="noc@lab.nsp",
            access="execute",
            span=["METRO-BA", "PE-BAIRES-01", "PE-BAIRES-02"],
        ),
        _user(
            "viewer",
            "Nokia1234!",
            group="read-only",
            role="monitor",
            display_name="Read-only Viewer",
            email="viewer@lab.nsp",
            access="read",
        ),
    ]
    return {u.username: u for u in users}


def seed_nes() -> dict[str, NetworkElement]:
    nes = [
        NetworkElement(
            name="PE-BAIRES-01",
            system_ip="10.10.1.1",
            ne_type="7750 SR-12e",
            version="TiMOS-C-24.10.R1",
            site="Buenos Aires",
            group="METRO-BA",
            chassis_mac="00:03:fa:11:01:01",
            protocols=["ospf", "isis", "ldp", "rsvp", "mpls", "bgp", "sr"],
            cards=[
                Card("A", "cpm-2", "cpm-2", "up", "up"),
                Card("B", "cpm-2", "cpm-2", "up", "up"),
                _line_card(
                    "1",
                    "imm48-sfp+",
                    _ports(
                        [
                            ("1/1/1", "network", "10G", "up", "up"),
                            ("1/1/2", "network", "10G", "up", "up"),
                            ("1/1/3", "network", "10G", "up", "up"),
                            ("1/1/10", "access", "10G", "up", "up"),
                            ("1/1/11", "access", "10G", "up", "down"),
                        ]
                    ),
                ),
            ],
        ),
        NetworkElement(
            name="PE-BAIRES-02",
            system_ip="10.10.1.2",
            ne_type="7750 SR-7",
            version="TiMOS-C-24.10.R1",
            site="Buenos Aires",
            group="METRO-BA",
            chassis_mac="00:03:fa:11:01:02",
            protocols=["ospf", "isis", "ldp", "rsvp", "mpls", "bgp"],
            cards=[
                Card("A", "cpm-2", "cpm-2", "up", "up"),
                _line_card(
                    "1",
                    "imm24-sfp+",
                    _ports(
                        [
                            ("1/1/1", "network", "10G", "up", "up"),
                            ("1/1/2", "network", "10G", "up", "up"),
                            ("1/1/10", "access", "1G", "up", "up"),
                        ]
                    ),
                ),
            ],
        ),
        NetworkElement(
            name="P-CORE-01",
            system_ip="10.10.0.1",
            ne_type="7950 XRS-20",
            version="TiMOS-C-24.10.R1",
            site="Core BA",
            group="CORE",
            chassis_mac="00:03:fa:00:00:01",
            protocols=["isis", "ldp", "rsvp", "mpls", "sr"],
            cards=[
                Card("A", "cpm-xrs", "cpm-xrs", "up", "up"),
                _line_card(
                    "1",
                    "xcm-2s",
                    _ports(
                        [
                            ("1/1/1", "network", "100G", "up", "up"),
                            ("1/1/2", "network", "100G", "up", "up"),
                            ("1/1/3", "network", "100G", "up", "up"),
                            ("1/1/4", "network", "100G", "up", "up"),
                        ]
                    ),
                ),
            ],
        ),
        NetworkElement(
            name="P-CORE-02",
            system_ip="10.10.0.2",
            ne_type="7950 XRS-20",
            version="TiMOS-C-24.10.R1",
            site="Core CBA",
            group="CORE",
            chassis_mac="00:03:fa:00:00:02",
            protocols=["isis", "ldp", "rsvp", "mpls", "sr"],
            cards=[
                Card("A", "cpm-xrs", "cpm-xrs", "up", "up"),
                _line_card(
                    "1",
                    "xcm-2s",
                    _ports(
                        [
                            ("1/1/1", "network", "100G", "up", "up"),
                            ("1/1/2", "network", "100G", "up", "up"),
                            ("1/1/3", "network", "100G", "up", "up"),
                        ]
                    ),
                ),
            ],
        ),
        NetworkElement(
            name="PE-CORDOBA-01",
            system_ip="10.10.2.1",
            ne_type="7750 SR-12",
            version="TiMOS-C-24.7.R2",
            site="Córdoba",
            group="METRO-CBA",
            chassis_mac="00:03:fa:22:02:01",
            protocols=["ospf", "isis", "ldp", "rsvp", "mpls", "bgp", "sr"],
            cards=[
                Card("A", "cpm-2", "cpm-2", "up", "up"),
                _line_card(
                    "1",
                    "imm48-sfp+",
                    _ports(
                        [
                            ("1/1/1", "network", "10G", "up", "up"),
                            ("1/1/2", "network", "10G", "up", "up"),
                            ("1/1/10", "access", "10G", "up", "up"),
                        ]
                    ),
                ),
            ],
        ),
        NetworkElement(
            name="PE-ROSARIO-01",
            system_ip="10.10.3.1",
            ne_type="7705 SAR-8",
            version="TiMOS-B-24.10.R1",
            site="Rosario",
            group="ACCESS",
            chassis_mac="00:03:fa:33:03:01",
            protocols=["ospf", "ldp", "mpls", "bgp"],
            cards=[
                Card("A", "csm", "csm", "up", "up"),
                _line_card(
                    "1",
                    "sar-8-eth",
                    _ports(
                        [
                            ("1/1/1", "network", "1G", "up", "up"),
                            ("1/1/2", "access", "1G", "up", "up"),
                            ("1/1/3", "access", "1G", "up", "up"),
                        ]
                    ),
                ),
            ],
        ),
        NetworkElement(
            name="PE-MENDOZA-01",
            system_ip="10.10.4.1",
            ne_type="7750 SR-12",
            version="TiMOS-C-24.10.R1",
            site="Mendoza",
            group="METRO-Cuyo",
            chassis_mac="00:03:fa:44:04:01",
            protocols=["isis", "ldp", "rsvp", "mpls", "bgp", "sr"],
            cards=[
                Card("A", "cpm-2", "cpm-2", "up", "up"),
                _line_card(
                    "1",
                    "imm48-sfp+",
                    _ports(
                        [
                            ("1/1/1", "network", "10G", "up", "up"),
                            ("1/1/2", "network", "10G", "up", "degraded"),
                            ("1/1/10", "access", "10G", "up", "up"),
                        ]
                    ),
                ),
            ],
        ),
        NetworkElement(
            name="PE-SALTA-01",
            system_ip="10.10.5.1",
            ne_type="7705 SAR-8",
            version="TiMOS-B-24.7.R1",
            site="Salta",
            group="ACCESS",
            chassis_mac="00:03:fa:55:05:01",
            management="managed",
            protocols=["ospf", "ldp", "mpls"],
            cards=[
                Card("A", "csm", "csm", "up", "up"),
                _line_card(
                    "1",
                    "sar-8-eth",
                    _ports(
                        [
                            ("1/1/1", "network", "1G", "up", "up"),
                            ("1/1/2", "access", "1G", "up", "up"),
                        ]
                    ),
                ),
            ],
        ),
    ]
    return {ne.name: ne for ne in nes}


def seed_paths() -> dict[str, MplsPath]:
    paths = [
        MplsPath("path-ba-cba", ["PE-BAIRES-01", "P-CORE-01", "P-CORE-02", "PE-CORDOBA-01"]),
        MplsPath("path-ba-mza", ["PE-BAIRES-01", "P-CORE-01", "PE-MENDOZA-01"]),
        MplsPath("path-ba-ros", ["PE-BAIRES-01", "PE-BAIRES-02", "PE-ROSARIO-01"]),
        MplsPath("path-core", ["P-CORE-01", "P-CORE-02"]),
        MplsPath("path-ba-sal", ["PE-BAIRES-01", "P-CORE-01", "PE-SALTA-01"]),
        MplsPath("loose-any", [], "loose"),
    ]
    return {p.name: p for p in paths}


def seed_lsps() -> dict[str, Lsp]:
    lsps = [
        Lsp(
            "lsp-ba-cba",
            "dynamic",
            "rsvp",
            "PE-BAIRES-01",
            "PE-CORDOBA-01",
            "path-ba-cba",
            ["PE-BAIRES-01", "P-CORE-01", "P-CORE-02", "PE-CORDOBA-01"],
            bandwidth_mbps=1000,
            protection="fast-reroute",
            metric=30,
        ),
        Lsp(
            "lsp-cba-ba",
            "dynamic",
            "rsvp",
            "PE-CORDOBA-01",
            "PE-BAIRES-01",
            "path-ba-cba",
            ["PE-CORDOBA-01", "P-CORE-02", "P-CORE-01", "PE-BAIRES-01"],
            bandwidth_mbps=1000,
            protection="fast-reroute",
            metric=30,
        ),
        Lsp(
            "lsp-ba-mza-sr",
            "sr-te",
            "sr",
            "PE-BAIRES-01",
            "PE-MENDOZA-01",
            "path-ba-mza",
            ["PE-BAIRES-01", "P-CORE-01", "PE-MENDOZA-01"],
            bandwidth_mbps=500,
            protection="ti-lfa",
            metric=20,
        ),
        Lsp(
            "lsp-ba-ros",
            "dynamic",
            "ldp",
            "PE-BAIRES-01",
            "PE-ROSARIO-01",
            "path-ba-ros",
            ["PE-BAIRES-01", "PE-BAIRES-02", "PE-ROSARIO-01"],
            bandwidth_mbps=200,
            metric=15,
        ),
        Lsp(
            "lsp-core-p2p",
            "dynamic",
            "rsvp",
            "P-CORE-01",
            "P-CORE-02",
            "path-core",
            ["P-CORE-01", "P-CORE-02"],
            bandwidth_mbps=10000,
            protection="bypass",
            metric=5,
        ),
        Lsp(
            "lsp-ba-sal",
            "dynamic",
            "rsvp",
            "PE-BAIRES-01",
            "PE-SALTA-01",
            "path-ba-sal",
            ["PE-BAIRES-01", "P-CORE-01", "PE-SALTA-01"],
            admin="up",
            oper="down",
            bandwidth_mbps=100,
            metric=40,
        ),
        Lsp(
            "bypass-core-01",
            "bypass",
            "rsvp",
            "P-CORE-01",
            "P-CORE-02",
            "loose-any",
            ["P-CORE-01", "PE-BAIRES-01", "P-CORE-02"],
            bandwidth_mbps=0,
            protection="manual-bypass",
            metric=50,
        ),
        Lsp(
            "lsp-ba-cba-sec",
            "static",
            "rsvp",
            "PE-BAIRES-01",
            "PE-CORDOBA-01",
            "loose-any",
            ["PE-BAIRES-01", "PE-ROSARIO-01", "PE-CORDOBA-01"],
            admin="down",
            oper="down",
            metric=80,
        ),
    ]
    return {l.name: l for l in lsps}


def seed_interfaces() -> list[MplsInterface]:
    return [
        MplsInterface("PE-BAIRES-01", "to-core-01", "1/1/1", 10, "up", "up", ["srlg-ba"]),
        MplsInterface("PE-BAIRES-01", "to-ba-02", "1/1/2", 10, "up", "up"),
        MplsInterface("PE-BAIRES-02", "to-ba-01", "1/1/1", 10, "up", "up"),
        MplsInterface("P-CORE-01", "to-xrs-02", "1/1/1", 5, "up", "up", ["srlg-core"]),
        MplsInterface("P-CORE-01", "to-ba-01", "1/1/2", 10, "up", "up"),
        MplsInterface("P-CORE-01", "to-mza", "1/1/3", 20, "up", "up"),
        MplsInterface("P-CORE-02", "to-xrs-01", "1/1/1", 5, "up", "up", ["srlg-core"]),
        MplsInterface("P-CORE-02", "to-cba", "1/1/2", 10, "up", "up"),
        MplsInterface("PE-CORDOBA-01", "to-core-02", "1/1/1", 10, "up", "up"),
        MplsInterface("PE-MENDOZA-01", "to-core-01", "1/1/1", 20, "up", "up"),
        MplsInterface("PE-MENDOZA-01", "to-core-backup", "1/1/2", 40, "up", "degraded"),
        MplsInterface("PE-ROSARIO-01", "to-ba", "1/1/1", 15, "up", "up"),
        MplsInterface("PE-SALTA-01", "to-core-01", "1/1/1", 30, "up", "up"),
    ]


def seed_tunnels() -> dict[int, ServiceTunnel]:
    tunnels = [
        ServiceTunnel(101, "sdp-ba-cba", "PE-BAIRES-01", "PE-CORDOBA-01", "tldp", "lsp-ba-cba", far_end="10.10.2.1"),
        ServiceTunnel(102, "sdp-cba-ba", "PE-CORDOBA-01", "PE-BAIRES-01", "tldp", "lsp-cba-ba", far_end="10.10.1.1"),
        ServiceTunnel(201, "sdp-ba-ros", "PE-BAIRES-01", "PE-ROSARIO-01", "tldp", "lsp-ba-ros", far_end="10.10.3.1"),
        ServiceTunnel(202, "sdp-ros-ba", "PE-ROSARIO-01", "PE-BAIRES-01", "tldp", "lsp-ba-ros", far_end="10.10.1.1"),
        ServiceTunnel(301, "sdp-ba-mza", "PE-BAIRES-01", "PE-MENDOZA-01", "sr-isis", "lsp-ba-mza-sr", far_end="10.10.4.1"),
        ServiceTunnel(401, "sdp-ba-sal", "PE-BAIRES-01", "PE-SALTA-01", "tldp", "lsp-ba-sal", "up", "down", "10.10.5.1"),
    ]
    return {t.sdp_id: t for t in tunnels}


def seed_customers() -> dict[int, Customer]:
    customers = [
        Customer(12, "Banco Nación", "L3VPN sucursales", "noc@bna.lab"),
        Customer(20, "Telecom Mayorista", "Metro Ethernet CABA", "mayorista@telecom.lab"),
        Customer(33, "Puerto Rosario", "P2P L2 Rosario–BA", "red@puertorosario.lab"),
        Customer(44, "Gobierno Salta", "L3VPN backup Salta", "tic@salta.lab"),
    ]
    return {c.subscriber_id: c for c in customers}


def seed_services() -> dict[int, Service]:
    services = [
        Service(
            100,
            "vprn-banco-nacion",
            "vprn",
            "Banco Nación",
            12,
            ["PE-BAIRES-01", "PE-CORDOBA-01", "PE-MENDOZA-01"],
            [101, 102, 301],
            mtu=1500,
            description="L3VPN sucursales",
            route_distinguisher="65000:12",
        ),
        Service(
            110,
            "vprn-banco-cajeros",
            "vprn",
            "Banco Nación",
            12,
            ["PE-BAIRES-01", "PE-BAIRES-02"],
            [],
            mtu=1500,
            description="L3VPN red de cajeros",
            route_distinguisher="65000:13",
        ),
        Service(
            200,
            "vpls-metro-ba",
            "vpls",
            "Telecom Mayorista",
            20,
            ["PE-BAIRES-01", "PE-BAIRES-02"],
            mtu=1518,
            description="Metro Ethernet CABA (E-LAN)",
        ),
        Service(
            210,
            "epipe-cliente-fibra",
            "epipe",
            "Telecom Mayorista",
            20,
            ["PE-BAIRES-01", "PE-BAIRES-02"],
            description="E-Line mayorista P2P",
        ),
        Service(
            300,
            "epipe-ros-ba",
            "epipe",
            "Puerto Rosario",
            33,
            ["PE-BAIRES-01", "PE-ROSARIO-01"],
            [201, 202],
            description="P2P L2 Rosario–BA (E-Line)",
        ),
        Service(
            500,
            "vprn-salta-backup",
            "vprn",
            "Gobierno Salta",
            44,
            ["PE-BAIRES-01", "PE-SALTA-01"],
            [401],
            admin="up",
            oper="down",
            description="L3VPN Salta — SDP down",
            oos_reasons="sdpBindingDown,siteDown",
            route_distinguisher="65000:44",
        ),
    ]
    return {s.svc_id: s for s in services}


def seed_sites(nes: dict[str, NetworkElement], services: dict[int, Service]) -> list[ServiceSite]:
    out: list[ServiceSite] = []
    for svc in services.values():
        for ne_name in svc.sites:
            ne = nes[ne_name]
            oper: str = "down" if svc.oper == "down" else ne.oper
            out.append(
                ServiceSite(
                    svc.svc_id,
                    ne.system_ip,
                    ne_name,
                    admin=svc.admin,
                    oper=oper,  # type: ignore[arg-type]
                    mtu=svc.mtu,
                )
            )
    return out


def seed_saps() -> list[AccessInterface]:
    return [
        AccessInterface(100, "10.10.1.1", "1/1/10:100", "1/1/10", "l3", outer_tag=100, primary_ipv4="10.1.12.1/30"),
        AccessInterface(100, "10.10.2.1", "1/1/10:100", "1/1/10", "l3", outer_tag=100, primary_ipv4="10.2.12.1/30"),
        AccessInterface(100, "10.10.4.1", "1/1/10:100", "1/1/10", "l3", outer_tag=100, primary_ipv4="10.4.12.1/30"),
        AccessInterface(110, "10.10.1.1", "1/1/10:110", "1/1/10", "l3", outer_tag=110, primary_ipv4="10.1.13.1/30"),
        AccessInterface(110, "10.10.1.2", "1/1/10:110", "1/1/10", "l3", outer_tag=110, primary_ipv4="10.1.13.5/30"),
        AccessInterface(200, "10.10.1.1", "1/1/10:200", "1/1/10", "l2", outer_tag=200),
        AccessInterface(200, "10.10.1.2", "1/1/10:200", "1/1/10", "l2", outer_tag=200),
        AccessInterface(210, "10.10.1.1", "1/1/11:210", "1/1/11", "l2", outer_tag=210, oper="down"),
        AccessInterface(210, "10.10.1.2", "1/1/10:210", "1/1/10", "l2", outer_tag=210),
        AccessInterface(300, "10.10.1.1", "1/1/10:300", "1/1/10", "l2", outer_tag=300),
        AccessInterface(300, "10.10.3.1", "1/1/2:300", "1/1/2", "l2", outer_tag=300),
        AccessInterface(500, "10.10.1.1", "1/1/10:500", "1/1/10", "l3", outer_tag=500, primary_ipv4="10.5.44.1/30"),
        AccessInterface(500, "10.10.5.1", "1/1/2:500", "1/1/2", "l3", outer_tag=500, primary_ipv4="10.5.44.5/30", oper="down"),
    ]


def seed_bindings() -> list[SdpBinding]:
    return [
        SdpBinding(100, "10.10.1.1", 101, 100, "spoke"),
        SdpBinding(100, "10.10.2.1", 102, 100, "spoke"),
        SdpBinding(100, "10.10.4.1", 301, 100, "spoke"),
        SdpBinding(200, "10.10.1.1", 0, 200, "mesh"),
        SdpBinding(200, "10.10.1.2", 0, 200, "mesh"),
        SdpBinding(210, "10.10.1.1", 0, 210, "spoke", oper="down"),
        SdpBinding(210, "10.10.1.2", 0, 210, "spoke"),
        SdpBinding(300, "10.10.1.1", 201, 300, "spoke"),
        SdpBinding(300, "10.10.3.1", 202, 300, "spoke"),
        SdpBinding(500, "10.10.1.1", 401, 500, "spoke", oper="down"),
        SdpBinding(500, "10.10.5.1", 401, 500, "spoke", oper="down"),
    ]


def seed_route_targets() -> list[RouteTarget]:
    return [
        RouteTarget(100, "import", "65000:12"),
        RouteTarget(100, "export", "65000:12"),
        RouteTarget(110, "import", "65000:13"),
        RouteTarget(110, "export", "65000:13"),
        RouteTarget(500, "import", "65000:44"),
        RouteTarget(500, "export", "65000:44"),
    ]


def seed_static_routes() -> list[StaticRoute]:
    return [
        StaticRoute(100, "10.10.1.1", "10.50.0.0/16", "10.1.12.2"),
        StaticRoute(100, "10.10.2.1", "10.51.0.0/16", "10.2.12.2"),
        StaticRoute(110, "10.10.1.1", "10.60.0.0/16", "10.1.13.2"),
        StaticRoute(500, "10.10.1.1", "10.44.0.0/16", "10.5.44.2", admin="down"),
    ]


def seed_bgp_peers() -> list[BgpPeer]:
    return [
        BgpPeer(100, "10.10.1.1", "10.1.12.2", 65012),
        BgpPeer(100, "10.10.2.1", "10.2.12.2", 65012),
        BgpPeer(100, "10.10.4.1", "10.4.12.2", 65012),
        BgpPeer(110, "10.10.1.1", "10.1.13.2", 65013),
        BgpPeer(500, "10.10.1.1", "10.5.44.2", 65044, oper="down"),
    ]


def seed_macs() -> list[MacEntry]:
    return [
        MacEntry(200, "10.10.1.1", "00:00:5e:00:53:01", "1/1/10:200", "learned"),
        MacEntry(200, "10.10.1.2", "00:00:5e:00:53:02", "1/1/10:200", "learned"),
        MacEntry(200, "10.10.1.1", "00:00:5e:00:53:aa", "1/1/10:200", "static"),
    ]


def seed_alarms() -> list[Alarm]:
    return [
        Alarm(
            "A-1001",
            "critical",
            "tunnelOperDown",
            "sdp:401",
            "PE-BAIRES-01",
            _ts(2.1),
            "SDP 401 oper-down — far-end PE-SALTA-01 unreachable via lsp-ba-sal",
        ),
        Alarm(
            "A-1002",
            "critical",
            "lspOperDown",
            "lsp:lsp-ba-sal",
            "PE-BAIRES-01",
            _ts(2.1),
            "Dynamic RSVP LSP lsp-ba-sal operationally down",
        ),
        Alarm(
            "A-1003",
            "major",
            "portLinkDown",
            "ne:PE-BAIRES-01:port:1/1/11",
            "PE-BAIRES-01",
            _ts(8.0),
            "Access port 1/1/11 link down",
        ),
        Alarm(
            "A-1004",
            "major",
            "serviceSiteDown",
            "svc:500",
            "PE-SALTA-01",
            _ts(2.0),
            "VPRN 500 site down at PE-SALTA-01 — svc-mgr:service-500",
        ),
        Alarm(
            "A-1005",
            "minor",
            "sfpRxPowerLow",
            "ne:PE-MENDOZA-01:port:1/1/2",
            "PE-MENDOZA-01",
            _ts(26.0),
            "Optical Rx power below threshold on 1/1/2",
        ),
        Alarm(
            "A-1006",
            "warning",
            "neCpuHigh",
            "ne:P-CORE-01",
            "P-CORE-01",
            _ts(0.4),
            "CPM CPU 78% (threshold 75%)",
        ),
        Alarm(
            "A-1007",
            "minor",
            "versionMismatch",
            "ne:PE-CORDOBA-01",
            "PE-CORDOBA-01",
            _ts(120.0),
            "NE software TiMOS-C-24.7.R2 behind NFM-P preferred 24.10.R1",
            acked=True,
            acked_by="operator",
        ),
    ]


def seed_stats(nes: dict[str, NetworkElement], lsps: dict[str, Lsp]) -> list[StatSample]:
    now = datetime.now(timezone.utc)
    samples: list[StatSample] = []
    for ne in nes.values():
        for card in ne.cards:
            for port in card.ports:
                if port.oper != "up":
                    continue
                base = 1_000_000 if "100G" in port.speed else 80_000 if "10G" in port.speed else 8_000
                fdn = f"ne:{ne.name}:port:{port.name}"
                samples.append(StatSample(fdn, "ifInOctets", base * 940, "bytes", now))
                samples.append(StatSample(fdn, "ifOutOctets", base * 710, "bytes", now))
                samples.append(StatSample(fdn, "utilizationIn", 34.2 if "100G" in port.speed else 41.0, "%", now))
                samples.append(StatSample(fdn, "utilizationOut", 22.8 if "100G" in port.speed else 29.5, "%", now))
    for lsp in lsps.values():
        fdn = f"lsp:{lsp.name}"
        samples.append(StatSample(fdn, "lspOctets", 12_400_000 if lsp.oper == "up" else 0, "bytes", now))
        samples.append(StatSample(fdn, "lspPackets", 98_100 if lsp.oper == "up" else 0, "pkts", now))
        samples.append(StatSample(fdn, "bandwidthReserved", float(lsp.bandwidth_mbps), "Mbps", now))
    return samples


class Store:
    """Mutable in-memory NFM-P database for the demo lab."""

    SERVICE_TYPES = ("vprn", "vpls", "epipe")

    def __init__(self) -> None:
        self.users = seed_users()
        self.nes = seed_nes()
        self.paths = seed_paths()
        self.lsps = seed_lsps()
        self.mpls_ifs = seed_interfaces()
        self.tunnels = seed_tunnels()
        self.customers = seed_customers()
        self.services = seed_services()
        self.sites = seed_sites(self.nes, self.services)
        self.saps = seed_saps()
        self.bindings = seed_bindings()
        self.route_targets = seed_route_targets()
        self.route_next_hops: list[RouteNextHop] = []
        self.bgp_rib: list[BgpRibPrefix] = []
        self.bgp_rib_info: list[BgpRibInfo] = []
        self.cpaa: list[Cpaa] = []
        self.igp_ases: list[TopologyAs] = []
        self.bgp_ases: list[TopologyAs] = []
        self.static_routes = seed_static_routes()
        self.bgp_peers = seed_bgp_peers()
        self.macs = seed_macs()
        self.alarms = seed_alarms()
        self.stats = seed_stats(self.nes, self.lsps)
        self.tasks: list = []
        self.task_seq = 1

    def visible_nes(self, user: User) -> dict[str, NetworkElement]:
        from nsp_grok.auth import in_span

        return {
            name: ne
            for name, ne in self.nes.items()
            if in_span(user, ne.group, ne.name)
        }

    def visible_services(self, user: User) -> dict[int, Service]:
        nes = self.visible_nes(user)
        out: dict[int, Service] = {}
        for sid, svc in self.services.items():
            if svc.svc_type not in self.SERVICE_TYPES:
                continue
            if svc.sites and user.span and user.role != "administrator":
                if not any(n in nes for n in svc.sites):
                    continue
            out[sid] = svc
        return out

    def visible_customers(self, user: User) -> dict[int, Customer]:
        return dict(self.customers)

    def services_of(self, subscriber_id: int, user: User) -> list[Service]:
        return [
            s
            for s in self.visible_services(user).values()
            if s.customer_id == subscriber_id
        ]

    def sites_of(self, svc_id: int, user: User) -> list[ServiceSite]:
        nes = self.visible_nes(user)
        return [s for s in self.sites if s.svc_id == svc_id and s.ne in nes]

    def saps_of(self, svc_id: int, user: User, site_id: str | None = None) -> list[AccessInterface]:
        sites = {s.site_id for s in self.sites_of(svc_id, user)}
        return [
            sap
            for sap in self.saps
            if sap.svc_id == svc_id and sap.site_id in sites and (site_id is None or sap.site_id == site_id)
        ]

    def bindings_of(self, svc_id: int, user: User, site_id: str | None = None) -> list[SdpBinding]:
        sites = {s.site_id for s in self.sites_of(svc_id, user)}
        return [
            b
            for b in self.bindings
            if b.svc_id == svc_id and b.site_id in sites and (site_id is None or b.site_id == site_id)
        ]

    def tunnels_of(self, svc: Service, user: User) -> list[ServiceTunnel]:
        nes = self.visible_nes(user)
        out: list[ServiceTunnel] = []
        for i in svc.sdp_ids:
            if i not in self.tunnels:
                continue
            tun = self.tunnels[i]
            if tun.from_ne in nes or tun.to_ne in nes:
                out.append(tun)
            elif tun.from_ne not in self.nes and tun.to_ne not in self.nes:
                out.append(tun)
        return out

    def lsps_of(self, svc: Service, user: User) -> list[Lsp]:
        names = {t.lsp for t in self.tunnels_of(svc, user) if t.lsp}
        return [self.lsps[n] for n in names if n in self.lsps]

    def alarms_of_service(self, svc: Service, user: User) -> list[Alarm]:
        nes = self.visible_nes(user)
        needle = svc.fdn
        return [
            a
            for a in self.alarms
            if not a.cleared
            and a.ne in nes
            and (needle in a.object_fdn or needle in a.additional_text or a.object_fdn.startswith(f"svc:{svc.svc_id}"))
        ]

    def apply_customers(self, customers: dict[int, Customer]) -> None:
        self.customers = customers

    def apply_services(self, subscriber_id: int, services: list[Service], customer_name: str) -> None:
        for svc in services:
            if not svc.customer:
                svc.customer = customer_name
        kept = {
            sid: svc
            for sid, svc in self.services.items()
            if svc.customer_id != subscriber_id
        }
        for svc in services:
            kept[svc.svc_id] = svc
        self.services = kept

    def apply_sites_saps(
        self,
        svc_id: int,
        sites: list[ServiceSite],
        saps: list[AccessInterface],
    ) -> None:
        self.sites = [s for s in self.sites if s.svc_id != svc_id] + list(sites)
        self.saps = [s for s in self.saps if s.svc_id != svc_id] + list(saps)
        svc = self.services.get(svc_id)
        if svc is not None:
            svc.sites = [site.ne for site in sites]

    def apply_vprn_related(
        self,
        svc_id: int,
        static_routes: list[StaticRoute] | None = None,
        bgp_peers: list[BgpPeer] | None = None,
        route_targets: list[RouteTarget] | None = None,
    ) -> None:
        if static_routes is not None:
            self.static_routes = [s for s in self.static_routes if s.svc_id != svc_id] + list(
                static_routes
            )
        if bgp_peers is not None:
            self.bgp_peers = [p for p in self.bgp_peers if p.svc_id != svc_id] + list(bgp_peers)
        if route_targets is not None:
            self.route_targets = [r for r in self.route_targets if r.svc_id != svc_id] + list(
                route_targets
            )

    def apply_route_next_hops(self, svc_id: int, hops: list[RouteNextHop]) -> None:
        self.route_next_hops = [h for h in self.route_next_hops if h.svc_id != svc_id] + list(hops)

    def apply_bindings(self, svc_id: int, bindings: list[SdpBinding]) -> None:
        self.bindings = [b for b in self.bindings if b.svc_id != svc_id] + list(bindings)
        svc = self.services.get(svc_id)
        if svc is not None and bindings:
            svc.sdp_ids = list(dict.fromkeys(b.sdp_id for b in bindings))

    def apply_tunnels(self, tunnels: list[ServiceTunnel]) -> None:
        for tun in tunnels:
            self.tunnels[tun.sdp_id] = tun

    def apply_lsps(self, lsps: list[Lsp]) -> None:
        for lsp in lsps:
            self.lsps[lsp.name] = lsp

    def apply_service_alarms(self, svc: Service, alarms: list[Alarm]) -> None:
        needle = svc.fdn
        kept = [
            a
            for a in self.alarms
            if needle not in a.object_fdn and needle not in a.additional_text
        ]
        self.alarms = kept + list(alarms)

    def apply_macs(self, svc_id: int, macs: list[MacEntry]) -> None:
        self.macs = [m for m in self.macs if m.svc_id != svc_id] + list(macs)

    def apply_bgp_rib(self, svc_id: int, prefixes: list[BgpRibPrefix]) -> None:
        self.bgp_rib = [p for p in self.bgp_rib if p.svc_id != svc_id] + list(prefixes)

    def apply_bgp_rib_info(self, svc_id: int, infos: list[BgpRibInfo]) -> None:
        self.bgp_rib_info = [i for i in self.bgp_rib_info if i.svc_id != svc_id] + list(infos)

    def apply_cpaa(self, cpaas: list[Cpaa]) -> None:
        self.cpaa = list(cpaas)

    def apply_igp_ases(self, domains: list[TopologyAs]) -> None:
        self.igp_ases = list(domains)

    def apply_bgp_ases(self, ases: list[TopologyAs]) -> None:
        self.bgp_ases = list(ases)

    def apply_nes(self, nes: dict[str, NetworkElement]) -> None:
        if nes:
            self.nes = nes

    def apply_ne_hardware(self, name: str, cards: list[Card]) -> None:
        ne = self.nes.get(name)
        if ne is not None:
            ne.cards = cards

    def apply_mpls_inventory(
        self,
        lsps: list[Lsp],
        tunnels: list[ServiceTunnel],
        interfaces: list[MplsInterface],
    ) -> None:
        if lsps:
            self.lsps = {lsp.name: lsp for lsp in lsps}
        if tunnels:
            self.tunnels = {tun.sdp_id: tun for tun in tunnels}
        if interfaces:
            self.mpls_ifs = list(interfaces)
