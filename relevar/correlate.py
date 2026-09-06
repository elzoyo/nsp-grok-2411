"""Correlación VRF → if → CDP/OSPF y clasificación local/exterior/desconocida."""

from __future__ import annotations

import re
from relevar.models import (
    Conexion,
    EquipoRack,
    Hueco,
    Inventario,
    Interfaz,
    OspfNeighbor,
    Patchera,
    Rack,
    VecinoL2,
)
from relevar.parse import _parent_if


_SWITCH_HINT = re.compile(
    r"WS-C|C9200|C9300|C2960|C3750|C3850|C3560|Nexus|switch",
    re.I,
)
_FO_HINT = re.compile(r"\b(FO|fibra|SFP|uplink|WAN|sitio|nodo)\b", re.I)


def _sitio_from_text(*parts: str) -> str:
    blob = " ".join(p for p in parts if p)
    # "FO a MERCEDES CORP" / "TRA a SALTO"
    m = re.search(
        r"\b(?:a|hacia|to)\s+([A-Z][A-Z0-9_-]{2,})\b",
        blob,
        re.I,
    )
    if m:
        token = m.group(1).upper()
        if token not in {"VRF", "OSPF", "VLAN", "OPE", "CORP", "TRA", "DIS", "TELF"}:
            return token
    m = re.search(r"\b(SITIO[-_A-Z0-9]+)\b", blob, re.I)
    if m:
        return m.group(1).upper()
    return ""


def _is_local_l2(vec: VecinoL2, nodo_host: str, ope_prefix: str) -> bool:
    if _SWITCH_HINT.search(vec.plataforma or ""):
        return True
    host = (vec.hostname or "").upper()
    if host and nodo_host:
        # mismo predio si comparte el token de sitio del CE (PAYSANDU, etc.)
        ce_toks = set(re.findall(r"[A-Z]{4,}", nodo_host.upper()))
        nb_toks = set(re.findall(r"[A-Z]{4,}", host))
        if ce_toks & nb_toks:
            return True
    if ope_prefix and vec.ip_mgmt.startswith(ope_prefix):
        return True
    return False


def _iface_by_logical(ifs: list[Interfaz]) -> dict[str, Interfaz]:
    return {i.logica: i for i in ifs}


def _vrf_of_local_if(ifs: list[Interfaz], local_if: str) -> str:
    exact = [i for i in ifs if i.logica == local_if or i.fisica == local_if]
    vrfs = [i.vrf for i in exact if i.vrf]
    if vrfs:
        return vrfs[0]
    parent = _parent_if(local_if)
    for i in ifs:
        if i.fisica == parent and i.vrf:
            return i.vrf
    return ""


def correlate_ospf(
    neighbors: list[OspfNeighbor],
    if_meta: dict[str, dict[str, str]],
    ifs: list[Interfaz],
    processes: list,
    l2: list[VecinoL2],
) -> list[OspfNeighbor]:
    by_log = _iface_by_logical(ifs)
    l2_by_if = {v.if_local: v for v in l2}
    proc_by_vrf = {p.vrf: p for p in processes}
    out: list[OspfNeighbor] = []
    for nb in neighbors:
        meta = if_meta.get(nb.if_logica, {})
        iface = by_log.get(nb.if_logica)
        nb.if_fisica = iface.fisica if iface else _parent_if(nb.if_logica)
        nb.vlan = iface.vlan if iface else ""
        nb.area = meta.get("area") or nb.area
        nb.costo = meta.get("costo") or nb.costo
        nb.network_type = meta.get("network_type") or nb.network_type
        nb.process_id = meta.get("process_id") or nb.process_id
        nb.router_id_local = meta.get("router_id") or nb.router_id_local
        if not nb.process_id and nb.vrf in proc_by_vrf:
            nb.process_id = proc_by_vrf[nb.vrf].process_id
            nb.router_id_local = nb.router_id_local or proc_by_vrf[nb.vrf].router_id
        parent = nb.if_fisica
        vec = l2_by_if.get(parent) or l2_by_if.get(nb.if_logica)
        if vec:
            nb.hostname_vecino = vec.hostname
        out.append(nb)
    return out


def classify_and_rack(inv: Inventario) -> Inventario:
    nodo = inv.nodo.hostname
    ope_ip = inv.nodo.ip_ope
    ope_prefix = ".".join(ope_ip.split(".")[:3]) + "." if ope_ip else ""

    local_hosts: set[str] = {nodo}
    for vec in inv.vecino_l2:
        if _is_local_l2(vec, nodo, ope_prefix):
            local_hosts.add(vec.hostname)

    conex: list[Conexion] = []
    exteriores: list[tuple[str, str, str, str]] = []  # sitio, if_local, vrf, origen
    seen_l2: set[tuple[str, str]] = set()

    for vec in inv.vecino_l2:
        key = (vec.if_local, vec.hostname)
        if key in seen_l2:
            continue
        seen_l2.add(key)
        vrf = _vrf_of_local_if(inv.interfaz, vec.if_local)
        if vec.hostname in local_hosts and _is_local_l2(vec, nodo, ope_prefix):
            conex.append(
                Conexion(
                    id=f"loc-{vec.if_local}-{vec.hostname}",
                    clase="local",
                    medio="cobre",
                    conector_remoto="rj45",
                    if_local=vec.if_local,
                    if_remota=vec.if_remota,
                    equipo_local=nodo,
                    equipo_remoto=vec.hostname,
                    vrf=vrf,
                    origen=vec.proto,
                )
            )
        else:
            sitio = _sitio_from_text(vec.hostname) or vec.hostname or "SITIO-DESCONOCIDO"
            exteriores.append((sitio, vec.if_local, vrf, vec.proto))

    ospf_ifs = {nb.if_fisica or nb.if_logica for nb in inv.ospf_neighbor}
    for nb in inv.ospf_neighbor:
        iface = next((i for i in inv.interfaz if i.logica == nb.if_logica), None)
        desc = iface.desc if iface else ""
        sitio = (
            _sitio_from_text(desc, nb.hostname_vecino)
            or nb.hostname_vecino
            or ""
        )
        local_if = nb.if_fisica or nb.if_logica
        already_local = any(
            c.clase == "local" and c.if_local in {local_if, nb.if_logica}
            for c in conex
        )
        if already_local:
            continue
        if not sitio:
            sitio = "SITIO-DESCONOCIDO"
        exteriores.append((sitio, local_if, nb.vrf, "ospf"))

    # uplinks with FO description and no OSPF/CDP
    covered = {c.if_local for c in conex} | {e[1] for e in exteriores}
    for iface in inv.interfaz:
        if iface.logica in covered or iface.fisica in covered:
            continue
        if iface.fisica != iface.logica:
            continue
        if _FO_HINT.search(iface.desc or ""):
            sitio = _sitio_from_text(iface.desc) or "SITIO-DESCONOCIDO"
            exteriores.append((sitio, iface.fisica, iface.vrf, "descripcion"))

    # unique exteriores by (sitio, if_local)
    uniq: dict[tuple[str, str], tuple[str, str, str, str]] = {}
    for item in exteriores:
        uniq[(item[0], item[1])] = item

    patchera_id = "ODF-1"
    puerto = 1
    usados: list[int] = []
    for sitio, if_local, vrf, origen in uniq.values():
        clase = "desconocida" if sitio == "SITIO-DESCONOCIDO" else "exterior"
        conex.append(
            Conexion(
                id=f"ext-{if_local}-{sitio}-{puerto}",
                clase=clase,
                medio="fo",
                conector_remoto="fc",
                if_local=if_local,
                equipo_local=nodo,
                equipo_remoto=None,
                sitio_remoto=sitio,
                patchera_id=patchera_id,
                patchera_puerto=puerto,
                vrf=vrf,
                origen=origen,
            )
        )
        usados.append(puerto)
        puerto += 1

    inv.conexion = conex
    inv.patchera = [
        Patchera(
            id=patchera_id,
            tipo="FO-FC",
            ru_inicio=41,
            n_conectores=24 if len(usados) <= 24 else 48,
            puertos_usados=usados,
        )
    ]

    equipos = [
        EquipoRack(
            hostname=nodo,
            rol="CE",
            plataforma=inv.nodo.plataforma,
            ru_inicio=20,
            ru_alto=2,
            faceplate=sorted(
                {
                    i.fisica
                    for i in inv.interfaz
                    if i.fisica and not i.fisica.lower().startswith("vlan")
                }
            )[:24],
        )
    ]
    ru_l2 = 18
    seen_eq = {nodo}
    for vec in inv.vecino_l2:
        if vec.hostname not in local_hosts or vec.hostname in seen_eq:
            continue
        seen_eq.add(vec.hostname)
        equipos.append(
            EquipoRack(
                hostname=vec.hostname,
                rol="L2",
                plataforma=vec.plataforma,
                ru_inicio=ru_l2,
                ru_alto=1,
                faceplate=[vec.if_remota] if vec.if_remota else [],
            )
        )
        ru_l2 -= 1
    inv.equipo_rack = equipos
    inv.rack = Rack(origen_posicion="inferida")
    inv.huecos = _huecos(inv, ospf_ifs)
    return inv


def _huecos(inv: Inventario, ospf_ifs: set[str]) -> list[Hueco]:
    out: list[Hueco] = [
        Hueco("u_inferida", "posición U del rack inferida (no medida en sitio)")
    ]
    cdp_ifs = {v.if_local for v in inv.vecino_l2}
    for nb in inv.ospf_neighbor:
        parent = nb.if_fisica or nb.if_logica
        if parent not in cdp_ifs and nb.if_logica not in cdp_ifs:
            out.append(
                Hueco(
                    "ospf_sin_cdp",
                    f"{nb.vrf} vecino {nb.neighbor_rid} en {nb.if_logica} sin CDP/LLDP",
                )
            )
        if not nb.if_fisica:
            out.append(
                Hueco(
                    "ospf_sin_fisica",
                    f"{nb.vrf} vecino {nb.neighbor_rid} sin if física correlacionada",
                )
            )
    igp_vrf = {p.vrf for p in inv.ospf_process} | {n.vrf for n in inv.ospf_neighbor}
    for vrf in inv.vrf:
        if vrf.nombre not in igp_vrf:
            out.append(Hueco("vrf_sin_igp", f"VRF {vrf.nombre} sin OSPF"))
    for iface in inv.interfaz:
        if iface.desc.strip():
            continue
        if iface.logica != iface.fisica:
            continue
        if "trunk" in (iface.desc or "").lower() or iface.trunk_vlans:
            out.append(Hueco("trunk_sin_desc", f"{iface.logica} trunk sin descripción"))
    for c in inv.conexion:
        if c.clase != "exterior":
            continue
        if not c.sitio_remoto or c.sitio_remoto == "SITIO-DESCONOCIDO":
            out.append(
                Hueco(
                    "uplink_sin_sitio",
                    f"{c.if_local} uplink FO sin sitio remoto parseable",
                )
            )
    return out


def ospf_correlacion_ok(inv: Inventario) -> bool:
    if not inv.ospf_neighbor:
        return True
    return all(nb.if_fisica for nb in inv.ospf_neighbor)
