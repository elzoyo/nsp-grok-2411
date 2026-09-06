"""NFM-P-inspired object model (equipment, routing, MPLS, services, faults)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

Severity = Literal["critical", "major", "minor", "warning", "cleared"]
Access = Literal["none", "read", "write", "execute"]
AdminState = Literal["up", "down"]
OperState = Literal["up", "down", "degraded"]
MgmtState = Literal["managed", "unmanaged", "suspended", "resync"]


SEVERITY_ORDER = {
    "critical": 4,
    "major": 3,
    "minor": 2,
    "warning": 1,
    "cleared": 0,
}


@dataclass
class User:
    username: str
    password_hash: str
    salt: str
    group: str
    role: str
    display_name: str
    email: str = ""
    state: Literal["active", "suspended"] = "active"
    force_password_change: bool = False
    password_history: list[str] = field(default_factory=list)
    failed_logins: int = 0
    locked_until: datetime | None = None
    last_login: datetime | None = None
    # Resource groups the user may see (empty = all).
    span: list[str] = field(default_factory=list)
    access: Access = "execute"


@dataclass
class Port:
    name: str
    mode: str
    encap: str
    admin: AdminState
    oper: OperState
    speed: str
    description: str = ""
    lag: str = ""
    fdn: str = ""


@dataclass
class Card:
    slot: str
    card_type: str
    equipped: str
    admin: AdminState
    oper: OperState
    ports: list[Port] = field(default_factory=list)


@dataclass
class NetworkElement:
    name: str
    system_ip: str
    ne_type: str
    version: str
    site: str
    group: str
    admin: AdminState = "up"
    oper: OperState = "up"
    management: MgmtState = "managed"
    chassis_mac: str = ""
    cards: list[Card] = field(default_factory=list)
    protocols: list[str] = field(default_factory=list)


@dataclass
class MplsInterface:
    ne: str
    name: str
    interface: str
    te_metric: int
    admin: AdminState
    oper: OperState
    srlgs: list[str] = field(default_factory=list)


@dataclass
class MplsPath:
    name: str
    hops: list[str]
    hop_type: str = "strict"


@dataclass
class Lsp:
    name: str
    lsp_type: str  # dynamic, static, sr-te, p2mp, bypass
    signaling: str  # rsvp, ldp, sr
    from_ne: str
    to_ne: str
    path: str
    hops: list[str]
    admin: AdminState = "up"
    oper: OperState = "up"
    metric: int = 10
    bandwidth_mbps: int = 0
    setup_priority: int = 7
    hold_priority: int = 7
    protection: str = "none"
    fdn: str = ""
    class_name: str = ""
    path_id: str = ""


@dataclass
class ServiceTunnel:
    sdp_id: int
    name: str
    from_ne: str
    to_ne: str
    signaling: str
    lsp: str
    admin: AdminState = "up"
    oper: OperState = "up"
    far_end: str = ""


@dataclass
class Customer:
    """NFM-P subscr.Subscriber — DN subscriber:<id>."""

    subscriber_id: int
    displayed_name: str
    description: str = ""
    contact: str = ""

    @property
    def fdn(self) -> str:
        return f"subscriber:{self.subscriber_id}"


@dataclass
class Service:
    svc_id: int  # NE serviceId — navigation (vprn 10)
    name: str
    svc_type: str  # vprn, vpls, epipe
    customer: str
    customer_id: int
    sites: list[str]
    sdp_ids: list[int] = field(default_factory=list)
    admin: AdminState = "up"
    oper: OperState = "up"
    mtu: int = 1514
    description: str = ""
    oos_reasons: str = ""
    route_distinguisher: str = ""
    mgr_id: int = 0  # NFM-P id — FDN svc-mgr:service-<mgr_id>

    def __post_init__(self) -> None:
        if not self.mgr_id:
            self.mgr_id = self.svc_id

    @property
    def fdn(self) -> str:
        return f"svc-mgr:service-{self.mgr_id}"

    @property
    def subscriber_pointer(self) -> str:
        return f"subscriber:{self.customer_id}"


@dataclass
class ServiceSite:
    """vprn.Site / vpls.Site / epipe.Site — svc-mgr:service-<id>:<siteIp>."""

    svc_id: int  # NE serviceId (join to Service.svc_id)
    site_id: str
    ne: str
    admin: AdminState = "up"
    oper: OperState = "up"
    mtu: int = 1514
    mgr_id: int = 0  # NFM-P service id for FDN

    def __post_init__(self) -> None:
        if not self.mgr_id:
            self.mgr_id = self.svc_id

    @property
    def fdn(self) -> str:
        return f"svc-mgr:service-{self.mgr_id}:{self.site_id}"


@dataclass
class AccessInterface:
    """SAP: vprn.L3AccessInterface or vpls/epipe L2AccessInterface."""

    svc_id: int  # NE serviceId (join to Service.svc_id)
    site_id: str
    name: str
    port: str
    layer: str
    encap: str = "dot1q"
    outer_tag: int = 0
    primary_ipv4: str = ""
    admin: AdminState = "up"
    oper: OperState = "up"
    mgr_id: int = 0
    port_pointer: str = ""  # NFM-P portPointer FDN; port is the last component
    object_fdn: str = ""

    def __post_init__(self) -> None:
        if not self.mgr_id:
            self.mgr_id = self.svc_id

    @property
    def fdn(self) -> str:
        return self.object_fdn or (
            f"svc-mgr:service-{self.mgr_id}:{self.site_id}:interface-{self.name}"
        )


@dataclass
class SdpBinding:
    svc_id: int  # NE serviceId (join to Service.svc_id)
    site_id: str
    sdp_id: int
    vc_id: int
    binding_type: str
    admin: AdminState = "up"
    oper: OperState = "up"
    mgr_id: int = 0
    far_end: str = ""
    object_fdn: str = ""

    def __post_init__(self) -> None:
        if not self.mgr_id:
            self.mgr_id = self.svc_id

    @property
    def fdn(self) -> str:
        return self.object_fdn or (
            f"svc-mgr:service-{self.mgr_id}:{self.site_id}:sdp-{self.sdp_id}"
        )


@dataclass
class RouteTarget:
    svc_id: int
    direction: str
    value: str
    num_next_hops: int = 0


@dataclass
class RouteNextHop:
    """Query 16: topology.BgpRoutesNextHop — PE that announces the RT.

    next_hop is the PE system IP. site_id in SAM-O is the CPAA, not the PE.
    """

    svc_id: int
    route_target: str
    next_hop: str
    addr_type: str = "ipv4"
    cpaa_site_id: str = ""  # SAM-O siteId = CPAA, not the PE


@dataclass
class StaticRoute:
    svc_id: int
    site_id: str
    prefix: str
    next_hop: str
    admin: AdminState = "up"


@dataclass
class BgpPeer:
    svc_id: int
    site_id: str
    peer_ip: str
    peer_as: int
    admin: AdminState = "up"
    oper: OperState = "up"


@dataclass
class TopologyAs:
    """Query 11 topology.AutonomousSystem or query 12 topology.BgpAutonomousSystem."""

    fdn: str
    kind: str  # igp | bgp
    displayed_name: str = ""
    as_number: str = ""
    as_type: str = ""
    description: str = ""
    bgp_topology_enabled: str = ""
    igp_admin_domain: str = ""
    cpaa_pointers: str = ""


@dataclass
class Cpaa:
    """Query 10: topology.Cpaa — recolector CPAM."""

    fdn: str
    displayed_name: str = ""
    router_id: str = ""
    bgp_as: str = ""
    protocol_record: str = ""
    protocol_events: str = ""
    rib_retrieve: str = ""
    rt_retrieve: str = ""
    admin: AdminState = "up"
    oper: OperState = "up"


@dataclass
class BgpRibInfo:
    """Query 13: topology.BgpRibInfo — agrupación RIB-IN (NH, MED, LOCAL-PREF, PEER)."""

    svc_id: int
    fdn: str
    kind: str
    key: str
    as_number: str = ""
    num_routes: int = 0


@dataclass
class BgpRibPrefix:
    """Query 13 value / 14 monitored prefix — prefijos VPNv4 del VPRN."""

    svc_id: int
    prefix: str
    rd: str
    pref_type: str = "vpnIpv4"
    next_hop: str = ""
    source: str = "BgpMonitoredPrefix"
    med: str = ""
    local_pref: str = ""
    as_path: str = ""
    peer: str = ""
    originator_id: str = ""


@dataclass
class MacEntry:
    svc_id: int
    site_id: str
    mac: str
    port: str
    source: str


@dataclass
class Alarm:
    id: str
    severity: Severity
    probable_cause: str
    object_fdn: str
    ne: str
    raised: datetime
    additional_text: str = ""
    acked: bool = False
    acked_by: str = ""
    cleared: bool = False


@dataclass
class StatSample:
    object_fdn: str
    counter: str
    value: float
    unit: str
    collected: datetime


@dataclass
class Task:
    id: int
    user: str
    operation: str
    object_fdn: str
    state: str
    started: datetime
    finished: datetime | None = None
