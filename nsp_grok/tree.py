"""Virtual filesystem over the NFM-P navigation tree.

Maps Equipment / Routing / MPLS / Services / Alarms / Stats views to paths
so the operator can `cd` / `ls` / `show` like a shell.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from nsp_grok.lab import Store
from nsp_grok.models import User


@dataclass
class Node:
    name: str
    kind: str
    label: str = ""
    payload: Any = None
    children: dict[str, Node] = field(default_factory=dict)

    def child(self, name: str) -> Node | None:
        return self.children.get(name)


def _folder(name: str, label: str = "", **kids: Node) -> Node:
    node = Node(name, "folder", label)
    node.children = kids
    return node


def _leaf(name: str, kind: str, payload: Any, label: str = "") -> Node:
    return Node(name, kind, label, payload)


def build_tree(store: Store, user: User) -> Node:
    nes = store.visible_nes(user)

    groups: dict[str, dict[str, Node]] = {}
    for ne in nes.values():
        groups.setdefault(ne.group, {})[ne.name] = _ne_node(ne, store)

    group_nodes = {
        gname: _folder(gname, f"grupo de equipo {gname}", **children)
        for gname, children in sorted(groups.items())
    }

    routing_kids = {name: _routing_node(ne, store, name) for name, ne in nes.items()}

    lsp_kids = {
        lsp.name: _leaf(lsp.name, "lsp", lsp, f"{lsp.signaling} {lsp.from_ne}->{lsp.to_ne}")
        for lsp in store.lsps.values()
        if lsp.from_ne in nes or lsp.to_ne in nes
    }
    path_kids = {
        p.name: _leaf(p.name, "path", p, f"{len(p.hops)} hops")
        for p in store.paths.values()
    }
    tun_kids = {
        str(t.sdp_id): _leaf(str(t.sdp_id), "sdp", t, t.name)
        for t in store.tunnels.values()
        if t.from_ne in nes or t.to_ne in nes
    }
    if_kids = {}
    for iface in store.mpls_ifs:
        if iface.ne not in nes:
            continue
        key = f"{iface.ne}:{iface.name}"
        if_kids[key] = _leaf(key, "mpls-if", iface, iface.interface)

    alarm_kids = {
        a.id: _leaf(a.id, "alarm", a, a.probable_cause)
        for a in store.alarms
        if a.ne in nes or not a.ne
    }

    admin_kids: dict[str, Node] = {}
    if user.role == "administrator":
        admin_kids = {
            "users": _folder(
                "users",
                "usuarios locales",
                **{
                    u.username: _leaf(u.username, "user", u, u.role)
                    for u in store.users.values()
                },
            )
        }

    customer_nodes = {
        str(cid): _customer_node(cust, store, user)
        for cid, cust in store.visible_customers(user).items()
    }
    cpaa_kids = {}
    for cpaa in store.cpaa:
        name = (cpaa.router_id or cpaa.fdn.rsplit(":", 1)[-1] or "cpaa").replace(":", "-")
        cpaa_kids[name] = _leaf(name, "cpaa", cpaa, cpaa.protocol_record or cpaa.fdn)

    root = _folder(
        "/",
        "Dominio gestionado NFM-P",
        customers=_folder("customers", "subscr.Subscriber", **customer_nodes),
        cpaa=_folder("cpaa", "topology.Cpaa (query 10)", **cpaa_kids),
        equipment=_folder("equipment", "Vista de equipos", **group_nodes),
        routing=_folder("routing", "Vista de ruteo", **routing_kids),
        mpls=_folder(
            "mpls",
            "MPLS",
            lsps=_folder("lsps", "LSPs", **lsp_kids),
            paths=_folder("paths", "Paths MPLS", **path_kids),
            interfaces=_folder("interfaces", "Interfaces MPLS", **if_kids),
            tunnels=_folder("tunnels", "Túneles de servicio (SDP)", **tun_kids),
        ),
        alarms=_folder("alarms", "Fallas", **alarm_kids),
        stats=_folder("stats", "Estadísticas"),
        admin=_folder("admin", "Usuarios y seguridad", **admin_kids),
        **{
            "igp-as": _folder(
                "igp-as",
                "topology.AutonomousSystem (query 11, sin LSDB)",
                **{
                    (d.as_number or d.fdn.rsplit("-", 1)[-1] or str(i)): _leaf(
                        d.as_number or d.fdn.rsplit("-", 1)[-1] or str(i),
                        "igp-as",
                        d,
                        d.displayed_name or d.fdn,
                    )
                    for i, d in enumerate(store.igp_ases)
                },
            ),
            "bgp-as": _folder(
                "bgp-as",
                "topology.BgpAutonomousSystem (query 12)",
                **{
                    (d.as_number or str(i)): _leaf(
                        d.as_number or str(i),
                        "bgp-as",
                        d,
                        d.displayed_name or d.fdn,
                    )
                    for i, d in enumerate(store.bgp_ases)
                },
            ),
        },
    )
    return root


def _customer_node(cust, store: Store, user: User) -> Node:
    by_type: dict[str, dict[str, Node]] = {}
    for svc in store.services_of(cust.subscriber_id, user):
        by_type.setdefault(svc.svc_type, {})[str(svc.svc_id)] = _service_node(svc, store, user)
    type_folders = {
        stype: _folder(stype, stype.upper(), **kids)
        for stype, kids in by_type.items()
    }
    counts = ", ".join(f"{k}={len(v)}" for k, v in sorted(by_type.items()))
    return Node(
        str(cust.subscriber_id),
        "customer",
        f"{cust.displayed_name}  {counts}",
        cust,
        type_folders,
    )


def _service_node(svc, store: Store, user: User) -> Node:
    site_kids = {}
    for site in store.sites_of(svc.svc_id, user):
        sap_kids = {
            sap.name.replace("/", "-").replace(":", "-"): _leaf(
                sap.name.replace("/", "-").replace(":", "-"), "sap", sap, sap.layer
            )
            for sap in store.saps_of(svc.svc_id, user, site.site_id)
        }
        bind_kids = {
            f"sdp-{b.sdp_id}": _leaf(f"sdp-{b.sdp_id}", "sdp-binding", b, b.binding_type)
            for b in store.bindings_of(svc.svc_id, user, site.site_id)
        }
        site_kids[site.site_id] = Node(
            site.site_id,
            "site",
            site.ne,
            site,
            {
                "saps": _folder("saps", "interfaces de acceso", **sap_kids),
                "sdp-bindings": _folder("sdp-bindings", "", **bind_kids),
            },
        )
    sap_all = {
        f"{sap.site_id}-{sap.name.replace('/', '-').replace(':', '-')}": _leaf(
            f"{sap.site_id}-{sap.name.replace('/', '-').replace(':', '-')}",
            "sap",
            sap,
            f"{sap.layer} {sap.name}",
        )
        for sap in store.saps_of(svc.svc_id, user)
    }
    bind_all = {
        f"{b.site_id}-sdp-{b.sdp_id}": _leaf(
            f"{b.site_id}-sdp-{b.sdp_id}", "sdp-binding", b, b.binding_type
        )
        for b in store.bindings_of(svc.svc_id, user)
    }
    tun_kids = {
        str(t.sdp_id): _leaf(str(t.sdp_id), "sdp", t, t.name)
        for t in store.tunnels_of(svc, user)
    }
    lsp_kids = {
        lsp.name: _leaf(lsp.name, "lsp", lsp, f"{lsp.from_ne}->{lsp.to_ne}")
        for lsp in store.lsps_of(svc, user)
    }
    alarm_kids = {
        a.id: _leaf(a.id, "alarm", a, a.probable_cause)
        for a in store.alarms_of_service(svc, user)
    }
    extra: dict[str, Node] = {}
    if svc.svc_type == "vprn":
        nhs_by_rt: dict[str, dict] = {}
        for nh in store.route_next_hops:
            if nh.svc_id != svc.svc_id:
                continue
            key = nh.next_hop.replace(".", "-")
            nhs_by_rt.setdefault(nh.route_target, {})[key] = _leaf(
                key, "rt-nh", nh, nh.next_hop
            )
        rt_kids = {}
        for rt in store.route_targets:
            if rt.svc_id != svc.svc_id:
                continue
            name = f"{rt.direction}-{rt.value.replace(':', '-')}"
            label = f"{rt.value}  nh={rt.num_next_hops}" if rt.num_next_hops else rt.value
            rt_kids[name] = Node(
                name, "rt", label, rt, nhs_by_rt.get(rt.value, {})
            )
        sr_kids = {
            sr.prefix.replace("/", "-"): _leaf(sr.prefix.replace("/", "-"), "static-route", sr, sr.next_hop)
            for sr in store.static_routes
            if sr.svc_id == svc.svc_id
        }
        bgp_kids = {
            p.peer_ip: _leaf(p.peer_ip, "bgp-peer", p, f"AS{p.peer_as}")
            for p in store.bgp_peers
            if p.svc_id == svc.svc_id
        }
        rib_kids = {
            p.prefix.replace("/", "-").replace(":", "-"): _leaf(
                p.prefix.replace("/", "-").replace(":", "-"),
                "bgp-rib",
                p,
                f"{p.rd} {p.next_hop}".strip(),
            )
            for p in store.bgp_rib
            if p.svc_id == svc.svc_id
        }
        info_kids = {
            f"{i.kind}-{i.key}".replace(":", "-").replace("/", "-")[:40]: _leaf(
                f"{i.kind}-{i.key}".replace(":", "-").replace("/", "-")[:40],
                "bgp-rib-info",
                i,
                f"{i.num_routes} rutas" if i.num_routes else i.key,
            )
            for i in store.bgp_rib_info
            if i.svc_id == svc.svc_id
        }
        extra = {
            "route-targets": _folder("route-targets", "RT import/export", **rt_kids),
            "static-routes": _folder("static-routes", "", **sr_kids),
            "bgp-peers": _folder("bgp-peers", "", **bgp_kids),
            "bgp-rib": _folder(
                "bgp-rib",
                "prefijos VPNv4 (query 13 value + 14)",
                **rib_kids,
            ),
            "bgp-rib-info": _folder(
                "bgp-rib-info",
                "BgpRibInfo agrupado (NH/MED/LOCAL-PREF/PEER)",
                **info_kids,
            ),
        }
    if svc.svc_type == "vpls":
        mac_kids = {
            m.mac.replace(":", ""): _leaf(m.mac.replace(":", ""), "mac", m, f"{m.site_id} {m.source}")
            for m in store.macs
            if m.svc_id == svc.svc_id
        }
        extra["mac-table"] = _folder("mac-table", "Proxy ARP / FIB", **mac_kids)

    return Node(
        str(svc.svc_id),
        "service",
        f"{svc.svc_type} {svc.name}",
        svc,
        {
            "sites": _folder("sites", "sites del servicio", **site_kids),
            "saps": _folder("saps", "interfaces de acceso", **sap_all),
            "sdp-bindings": _folder("sdp-bindings", "SDP spoke/mesh", **bind_all),
            "tunnels": _folder("tunnels", "svt.Tunnel", **tun_kids),
            "lsps": _folder("lsps", "LSPs de transporte", **lsp_kids),
            "alarms": _folder("alarms", "alarmas de este servicio", **alarm_kids),
            **extra,
        },
    )


def _ne_node(ne, store: Store) -> Node:
    cards = {}
    for card in ne.cards:
        port_kids = {
            p.name.replace("/", "-"): _leaf(p.name.replace("/", "-"), "port", p, p.mode)
            for p in card.ports
        }
        cards[card.slot] = Node(
            card.slot,
            "card",
            card.card_type,
            card,
            port_kids,
        )
    return Node(
        ne.name,
        "ne",
        f"{ne.ne_type} {ne.system_ip}",
        ne,
        {
            "cards": _folder("cards", "shelf / tarjetas", **cards),
            "routing": _routing_node(ne, store, "Base"),
        },
    )


def _routing_node(ne, store: Store, name: str = "Base") -> Node:
    ifs = {
        iface.name: _leaf(iface.name, "mpls-if", iface, iface.interface)
        for iface in store.mpls_ifs
        if iface.ne == ne.name
    }
    lsps = {
        lsp.name: _leaf(lsp.name, "lsp", lsp, lsp.signaling)
        for lsp in store.lsps.values()
        if lsp.from_ne == ne.name
    }
    proto_kids = {p: _folder(p, p.upper()) for p in ne.protocols}
    if "mpls" in proto_kids:
        proto_kids["mpls"].children = {
            "interfaces": _folder("interfaces", "", **ifs),
            "lsps": _folder("lsps", "", **lsps),
        }
    return Node(
        name,
        "vrtr",
        "Instancia de ruteo Base",
        ne,
        proto_kids,
    )


def resolve(root: Node, cwd: list[str], spec: str) -> tuple[list[str], Node] | None:
    if spec in ("", "."):
        node = _walk(root, cwd)
        return (cwd, node) if node else None
    if spec == "/":
        return [], root
    parts = spec.replace("\\", "/").split("/")
    if spec.startswith("/"):
        acc: list[str] = []
        parts = [p for p in parts if p]
    else:
        acc = list(cwd)
        parts = [p for p in parts if p]
    node = _walk(root, acc)
    if node is None:
        return None
    for part in parts:
        if part == ".":
            continue
        if part == "..":
            if acc:
                acc.pop()
                node = _walk(root, acc)
            continue
        if node is None or part not in node.children:
            return None
        acc.append(part)
        node = node.children[part]
    return acc, node


def _walk(root: Node, path: list[str]) -> Node | None:
    node = root
    for part in path:
        node = node.child(part)
        if node is None:
            return None
    return node


def pwd(path: list[str]) -> str:
    return "/" + "/".join(path) if path else "/"


def cli_prompt(username: str, host: str, path: list[str]) -> str:
    """Nokia/SR-OS style: user@nsp-ip>customers>12>vprn>100> """
    if not path:
        return f"{username}@{host}> "
    return f"{username}@{host}>" + ">".join(path) + "> "
