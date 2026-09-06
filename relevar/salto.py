"""Salto acotado a vecinos por OPE. Siempre se consulta antes de conectar."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from relevar.collect import (
    IDENTITY_COMMANDS,
    L2_SUBSET,
    L3_SUBSET,
    collect_subset,
    raw_get,
    read_raw_map,
    slug,
)
from relevar.correlate import (
    _sitio_from_text,
    classify_and_rack,
    is_local_neighbor,
    is_router_plat,
    is_switch_plat,
    same_ope,
    same_site,
)
from relevar.errors import RelevarError
from relevar.models import Hueco, Inventario, Salto, VecinoL2
from relevar.parse import (
    parse_cdp_detail,
    parse_descriptions,
    parse_hostname,
    parse_inventory,
    parse_version,
)

CONFIRM_YES = {"si", "sí", "s", "yes", "y"}
CONFIRM_NO = {"no", "n"}

OBJETIVO = {
    "l2": (
        "completar rack y L2 del predio "
        "(subset: version, VLAN, CDP, descripciones; sin LSDB ni show tech)"
    ),
    "l3": (
        "inventariar el otro L3 del predio "
        "(subset: version, VRF, CDP, HSRP; un hop, no crawl)"
    ),
    "identidad": (
        "resolver hostname/plataforma para clasificar local vs FO "
        "(solo version + hostname + inventory)"
    ),
}


def mensaje_salto(s: Salto) -> str:
    return (
        "Salto propuesto — se va a abrir SSH por OPE a otro equipo.\n"
        f"  equipo:   {s.hostname or '(sin nombre)'}\n"
        f"  IP OPE:   {s.ip}\n"
        f"  rol:      {s.rol}\n"
        f"  origen:   {s.origen}  if={s.if_local or '—'}\n"
        f"  objetivo: {s.objetivo}\n"
        "  no es crawl: un hop, sin LSDB ni show tech."
    )


def confirmar_salto(
    s: Salto,
    flag: str | None,
    confirm: Callable[[str], bool] | None = None,
) -> bool:
    text = mensaje_salto(s)
    if flag in CONFIRM_YES:
        return True
    if flag in CONFIRM_NO:
        return False
    if confirm is not None:
        return bool(confirm(text))
    print(text)
    try:
        ans = input("¿conectar a ese equipo? [sí/no] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False
    return ans in CONFIRM_YES


def _cdp_on_if(inv: Inventario, if_name: str) -> bool:
    names = {if_name}
    return any(v.if_local in names for v in inv.vecino_l2)


def proponer_saltos(inv: Inventario) -> list[Salto]:
    """L2 local, L3 local, identidad OSPF-sin-CDP en OPE. Nunca sitio remoto."""
    ce = inv.nodo.hostname
    ope = inv.nodo.ip_ope
    by_ip: dict[str, Salto] = {}

    def add(s: Salto) -> None:
        if not s.ip or s.ip == ope:
            return
        rank = {"identidad": 0, "l2": 1, "l3": 2}
        prev = by_ip.get(s.ip)
        if prev is None or rank.get(s.rol, 0) >= rank.get(prev.rol, 0):
            by_ip[s.ip] = s

    for vec in inv.vecino_l2:
        if not vec.ip_mgmt or vec.ip_mgmt == ope:
            continue
        if not is_local_neighbor(vec.hostname, vec.plataforma, vec.ip_mgmt, ce, ope):
            continue
        if is_router_plat(vec.plataforma):
            rol = "l3"
        elif is_switch_plat(vec.plataforma) or same_ope(vec.ip_mgmt, ope) or same_site(vec.hostname, ce):
            rol = "l2" if not is_router_plat(vec.plataforma) else "l3"
        else:
            continue
        add(
            Salto(
                hostname=vec.hostname,
                ip=vec.ip_mgmt,
                rol=rol,
                objetivo=OBJETIVO[rol],
                origen=vec.proto or "cdp",
                if_local=vec.if_local,
                comandos=list(L3_SUBSET if rol == "l3" else L2_SUBSET),
            )
        )

    for nb in inv.ospf_neighbor:
        ip = nb.neighbor_ip
        if not ip or ip == ope:
            continue
        iface = next((i for i in inv.interfaz if i.logica == nb.if_logica), None)
        desc = iface.desc if iface else ""
        sitio = _sitio_from_text(desc, nb.hostname_vecino)
        if sitio and not same_site(sitio, ce):
            continue
        if not same_ope(ip, ope) and (nb.vrf or "").upper() != "OPE":
            continue
        if _cdp_on_if(inv, nb.if_fisica) or _cdp_on_if(inv, nb.if_logica):
            continue
        if ip in by_ip:
            continue
        add(
            Salto(
                hostname=nb.hostname_vecino or "",
                ip=ip,
                rol="identidad",
                objetivo=OBJETIVO["identidad"],
                origen="ospf",
                if_local=nb.if_fisica or nb.if_logica,
                comandos=list(IDENTITY_COMMANDS),
            )
        )
    return list(by_ip.values())


def _dir_vecino(raw_root: Path, s: Salto) -> Path:
    names: list[str] = []
    if s.hostname:
        names.append(s.hostname)
        names.append(slug(s.hostname))
    names.append(s.ip)
    names.append(slug(s.ip))
    for name in names:
        if not name:
            continue
        path = raw_root / "vecinos" / name
        if path.is_dir() and any(path.glob("*.txt")):
            return path
    label = s.hostname or s.ip or "vecino"
    return raw_root / "vecinos" / label


def aplicar_raw_vecino(inv: Inventario, s: Salto, raw: dict[str, str]) -> None:
    host = parse_hostname(raw_get(raw, "show running-config | include hostname"))
    if not host:
        host = parse_hostname(raw_get(raw, "show version"))
    ver = parse_version(raw_get(raw, "show version"))
    plat = ver.get("plataforma") or ""
    inv_fis = parse_inventory(raw_get(raw, "show inventory"))
    if host:
        s.hostname = s.hostname or host
    descs = parse_descriptions(raw_get(raw, "show interfaces description"))
    cdp = parse_cdp_detail(raw_get(raw, "show cdp neighbors detail"))
    ports = [iface for iface in descs if not iface.lower().startswith("vlan")]
    local = is_local_neighbor(
        s.hostname or host, plat, s.ip, inv.nodo.hostname, inv.nodo.ip_ope
    )
    existing = next(
        (v for v in inv.vecino_l2 if v.ip_mgmt == s.ip or (s.hostname and v.hostname == s.hostname)),
        None,
    )
    if existing:
        existing.hostname = existing.hostname or s.hostname
        existing.plataforma = existing.plataforma or plat
        existing.ip_mgmt = existing.ip_mgmt or s.ip
        if not existing.if_remota and ports:
            existing.if_remota = ports[0]
    elif local or s.rol in {"l2", "l3"}:
        inv.vecino_l2.append(
            VecinoL2(
                proto="salto",
                if_local=s.if_local,
                if_remota=ports[0] if ports else "",
                hostname=s.hostname or host or s.ip,
                ip_mgmt=s.ip,
                plataforma=plat,
            )
        )
    for nb in inv.ospf_neighbor:
        if nb.neighbor_ip == s.ip:
            nb.hostname_vecino = s.hostname or host or nb.hostname_vecino
    extras: list[Hueco] = []
    for vec in cdp:
        if vec.hostname and vec.hostname != inv.nodo.hostname:
            if not any(v.hostname == vec.hostname for v in inv.vecino_l2):
                extras.append(
                    Hueco(
                        "vecino_de_vecino",
                        f"{s.hostname or s.ip} ve a {vec.hostname} por {vec.proto}; no se salta en cadena",
                    )
                )
    s.detalle = f"{s.hostname} {plat} " + ("; ".join(inv_fis[:2]) if inv_fis else "")
    s.estado = "ok"
    classify_and_rack(inv)
    inv.huecos.extend(extras)
    if ports:
        for eq in inv.equipo_rack:
            if eq.hostname in {s.hostname, host}:
                eq.faceplate = list(dict.fromkeys(eq.faceplate + ports))[:24]
                eq.plataforma = eq.plataforma or plat


def ejecutar_saltos(
    inv: Inventario,
    raw_root: Path,
    *,
    user: str = "",
    password: str = "",
    flag: str | None = None,
    confirm: Callable[[str], bool] | None = None,
    live: bool = False,
) -> Inventario:
    """Consulta (o --saltar=yes/no). Live abre SSH; --from-raw replay de raw/vecinos/."""
    propuestas = proponer_saltos(inv)
    if not propuestas:
        return inv
    vecinos_root = raw_root / "vecinos"
    for s in propuestas:
        dest = _dir_vecino(raw_root, s)
        replay = dest.is_dir() and any(dest.glob("*.txt"))
        if flag in CONFIRM_NO:
            s.estado = "rechazado"
            inv.salto.append(s)
            continue
        if live and not replay:
            if not confirmar_salto(s, flag, confirm):
                s.estado = "rechazado"
                inv.salto.append(s)
                continue
            s.estado = "aceptado"
            try:
                collect_subset(s.ip, user, password, dest, s.comandos)
            except RelevarError as exc:
                s.estado = "fallo"
                s.detalle = str(exc)
                inv.huecos.append(Hueco("salto_fallido", f"{s.ip} ({s.hostname or 'sin nombre'}): {exc}"))
                inv.salto.append(s)
                continue
        elif replay:
            if live and flag not in CONFIRM_YES:
                # evidencia ya colectada: no repreguntar SSH, sí anotar
                s.estado = "aceptado"
            else:
                s.estado = "aceptado"
        else:
            # from-raw sin carpeta vecinos y sin live: no hay a quién saltar
            if not live:
                s.estado = "propuesto"
                inv.salto.append(s)
                continue
            if not confirmar_salto(s, flag, confirm):
                s.estado = "rechazado"
                inv.salto.append(s)
                continue
        if dest.is_dir() and any(dest.glob("*.txt")):
            raw = read_raw_map(dest)
            aplicar_raw_vecino(inv, s, raw)
        inv.salto.append(s)
    # huecos se regeneran en classify; reponer saltos/huecos extra
    return inv
