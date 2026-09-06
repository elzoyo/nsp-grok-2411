"""De raw/ a inventario.json + relevamiento.md + nodo.drawio."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from relevar.collect import raw_get, read_raw_map
from relevar.correlate import classify_and_rack, correlate_ospf, ospf_correlacion_ok
from relevar.emit_drawio import write_drawio
from relevar.emit_json import write_json
from relevar.emit_md import write_md
from relevar.errors import RelevarError
from relevar.models import (
    Estatica,
    HsrpVrrp,
    Inventario,
    Nodo,
    PimNeighbor,
    RutaResumen,
)
from relevar.parse import (
    parse_cdp_detail,
    parse_descriptions,
    parse_etherchannel,
    parse_hostname,
    parse_inventory,
    parse_ip_brief,
    parse_lldp_detail,
    parse_ospf_interface,
    parse_ospf_neighbors,
    parse_ospf_process,
    parse_route_summary,
    parse_standby,
    parse_static_routes,
    parse_version,
    parse_vrf_interfaces,
    parse_vrfs,
    build_interfaces,
)


def build_inventario(raw: dict[str, str], ip_ope: str, vrf_filter: list[str] | None = None) -> Inventario:
    ver_raw = raw_get(raw, "show version")
    ver = parse_version(ver_raw)
    if ver.get("family") == "nxos":
        raise RelevarError("NX-OS no está en el MVP (solo IOS / IOS-XE)", code=1)
    host = parse_hostname(raw_get(raw, "show running-config | include hostname")) or parse_hostname(ver_raw)
    if not host:
        host = "CE-DESCONOCIDO"
    vrfs = parse_vrfs(
        raw_get(raw, "show vrf", "show ip vrf"),
        raw_get(raw, "show vrf detail"),
    )
    if vrf_filter:
        wanted = {v.upper() for v in vrf_filter}
        vrfs = [v for v in vrfs if v.nombre.upper() in wanted]
    vrf_ifs = parse_vrf_interfaces(raw_get(raw, "show ip vrf interfaces"))
    brief = parse_ip_brief(raw_get(raw, "show ip interface brief"))
    descs = parse_descriptions(raw_get(raw, "show interfaces description"))
    bundles = parse_etherchannel(
        raw_get(raw, "show etherchannel summary")
        or raw_get(raw, "show port-channel summary")
    )
    ifs = build_interfaces(vrf_ifs, brief, descs, bundles)
    l2 = parse_cdp_detail(raw_get(raw, "show cdp neighbors detail"))
    l2 += parse_lldp_detail(raw_get(raw, "show lldp neighbors detail"))

    names = [v.nombre for v in vrfs] or ["default"]
    processes = []
    neighbors = []
    if_meta: dict[str, dict[str, str]] = {}
    rutas: list[RutaResumen] = []
    estaticas: list[Estatica] = []
    pim: list[PimNeighbor] = []
    for name in names:
        processes.extend(
            parse_ospf_process(raw_get(raw, f"show ip ospf vrf {name}", "show ip ospf"), name)
        )
        neighbors.extend(
            parse_ospf_neighbors(
                raw_get(raw, f"show ip ospf neighbor vrf {name}", "show ip ospf neighbor"),
                name,
            )
        )
        if_meta.update(
            parse_ospf_interface(
                raw_get(raw, f"show ip ospf interface vrf {name}", "show ip ospf interface"),
                name,
            )
        )
        for code, count in parse_route_summary(
            raw_get(raw, f"show ip route vrf {name} summary", f"show ip route vrf {name}"),
            name,
        ):
            rutas.append(RutaResumen(vrf=name, origen=code, count=count))
        for pref, nh, iface in parse_static_routes(
            raw_get(raw, f"show ip route vrf {name} static", f"show ip route vrf {name}"),
            name,
        ):
            estaticas.append(Estatica(vrf=name, prefijo=pref, next_hop=nh, iface=iface))
        arp = raw_get(raw, f"show ip pim vrf {name} neighbor")
        for line in arp.splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[0].count(".") == 3:
                pim.append(PimNeighbor(vrf=name, neighbor_ip=parts[0], iface=parts[-1]))

    if not vrfs and ifs:
        from relevar.models import Vrf

        vrfs = [Vrf(nombre="default", interfaces=sorted({i.logica for i in ifs if i.logica}))]
        names = ["default"]

    if not vrfs:
        raise RelevarError("no hay VRFs parseables", code=3)

    hsrp = []
    for iface, grp, vip, state in parse_standby(raw_get(raw, "show standby brief")):
        vrf = next((i.vrf for i in ifs if i.logica == iface), "")
        hsrp.append(HsrpVrrp(vrf=vrf, grupo=grp, vip=vip, estado=state, iface=iface))

    nat = bool(
        raw_get(raw, "show ip nat translations").strip()
        and "Prohibited" not in raw_get(raw, "show ip nat translations")
    )
    if "---" in raw_get(raw, "show ip nat statistics"):
        nat = True

    inv = Inventario(
        nodo=Nodo(
            hostname=host,
            ip_ope=ip_ope,
            plataforma=ver.get("plataforma", ""),
            ios=ver.get("ios", ""),
            uptime=ver.get("uptime", ""),
            inventario_fisico=parse_inventory(raw_get(raw, "show inventory")),
        ),
        vrf=vrfs,
        interfaz=ifs,
        vecino_l2=l2,
        ospf_process=processes,
        ospf_neighbor=neighbors,
        ruta_resumen=rutas,
        estatica=estaticas,
        hsrp_vrrp=hsrp,
        nat_flag=nat,
        pim_neighbor=pim,
    )
    inv.ospf_neighbor = correlate_ospf(
        inv.ospf_neighbor, if_meta, inv.interfaz, inv.ospf_process, inv.vecino_l2
    )
    inv = classify_and_rack(inv)
    if not ospf_correlacion_ok(inv):
        raise RelevarError(
            "OSPF no se pudo correlacionar a if física/lógica",
            code=4,
        )
    return inv


def node_dir(out_root: Path, hostname: str, ip: str, when: datetime | None = None) -> Path:
    stamp = (when or datetime.now(timezone.utc)).strftime("%Y%m%d")
    return out_root / f"{hostname}_{ip}_{stamp}"


def emit_all(inv: Inventario, dest: Path) -> dict[str, Path]:
    dest.mkdir(parents=True, exist_ok=True)
    json_path = write_json(inv, dest / "inventario.json")
    md_path = write_md(inv, dest / "relevamiento.md")
    dio_path = write_drawio(inv, dest / "nodo.drawio")
    return {"json": json_path, "md": md_path, "drawio": dio_path}


def from_raw_dir(
    raw_dir: Path,
    ip_ope: str,
    dest: Path,
    vrf_filter: list[str] | None = None,
) -> Inventario:
    raw = read_raw_map(raw_dir)
    inv = build_inventario(raw, ip_ope, vrf_filter)
    emit_all(inv, dest)
    return inv
