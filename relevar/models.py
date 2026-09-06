"""Modelo canónico de inventario.json (MEMORIA_RELEVAR §5 y §6.1)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Nodo:
    hostname: str
    ip_ope: str
    plataforma: str = ""
    ios: str = ""
    uptime: str = ""
    inventario_fisico: list[str] = field(default_factory=list)


@dataclass
class Rack:
    nombre: str = "RACK-1"
    unidades: int = 42
    lado: str = "frente"
    origen_posicion: str = "inferida"


@dataclass
class EquipoRack:
    hostname: str
    rol: str  # CE | L2 | otro
    plataforma: str = ""
    ru_inicio: int = 1
    ru_alto: int = 1
    faceplate: list[str] = field(default_factory=list)


@dataclass
class Patchera:
    id: str
    tipo: str = "FO-FC"
    ru_inicio: int = 41
    n_conectores: int = 24
    puertos_usados: list[int] = field(default_factory=list)


@dataclass
class Conexion:
    id: str
    clase: str  # local | exterior | desconocida
    medio: str = "cobre"
    conector_remoto: str = "desconocido"
    if_local: str = ""
    if_remota: str = ""
    equipo_local: str = ""
    equipo_remoto: str | None = None
    sitio_remoto: str | None = None
    patchera_id: str | None = None
    patchera_puerto: int | None = None
    vrf: str = ""
    origen: str = ""


@dataclass
class Vrf:
    nombre: str
    rd: str = ""
    rt: list[str] = field(default_factory=list)
    interfaces: list[str] = field(default_factory=list)
    protocolos: list[str] = field(default_factory=list)


@dataclass
class Interfaz:
    fisica: str
    logica: str
    vlan: str = ""
    vrf: str = ""
    ip: str = ""
    mask: str = ""
    estado: str = ""
    desc: str = ""
    bundle: str = ""
    trunk_vlans: list[str] = field(default_factory=list)


@dataclass
class VecinoL2:
    proto: str  # cdp | lldp
    if_local: str
    if_remota: str = ""
    hostname: str = ""
    ip_mgmt: str = ""
    plataforma: str = ""


@dataclass
class OspfProcess:
    vrf: str
    process_id: str = ""
    router_id: str = ""
    areas: list[str] = field(default_factory=list)


@dataclass
class OspfNeighbor:
    vrf: str
    process_id: str = ""
    router_id_local: str = ""
    neighbor_rid: str = ""
    neighbor_ip: str = ""
    estado: str = ""
    area: str = ""
    if_logica: str = ""
    if_fisica: str = ""
    vlan: str = ""
    costo: str = ""
    network_type: str = ""
    hostname_vecino: str = ""


@dataclass
class RutaResumen:
    vrf: str
    origen: str
    count: int


@dataclass
class Estatica:
    vrf: str
    prefijo: str
    next_hop: str = ""
    iface: str = ""


@dataclass
class HsrpVrrp:
    vrf: str
    grupo: str
    vip: str = ""
    estado: str = ""
    iface: str = ""


@dataclass
class PimNeighbor:
    vrf: str
    neighbor_ip: str
    iface: str = ""


@dataclass
class Hueco:
    codigo: str
    detalle: str


@dataclass
class Salto:
    """Hop acotado por OPE. Nunca crawl; siempre con objetivo explícito."""

    hostname: str
    ip: str
    rol: str  # l2 | l3 | identidad
    objetivo: str
    origen: str  # cdp | lldp | ospf
    estado: str = "propuesto"  # propuesto | aceptado | rechazado | ok | fallo
    if_local: str = ""
    detalle: str = ""
    comandos: list[str] = field(default_factory=list)


@dataclass
class Inventario:
    nodo: Nodo
    rack: Rack = field(default_factory=Rack)
    equipo_rack: list[EquipoRack] = field(default_factory=list)
    patchera: list[Patchera] = field(default_factory=list)
    conexion: list[Conexion] = field(default_factory=list)
    vrf: list[Vrf] = field(default_factory=list)
    interfaz: list[Interfaz] = field(default_factory=list)
    vecino_l2: list[VecinoL2] = field(default_factory=list)
    ospf_process: list[OspfProcess] = field(default_factory=list)
    ospf_neighbor: list[OspfNeighbor] = field(default_factory=list)
    ruta_resumen: list[RutaResumen] = field(default_factory=list)
    estatica: list[Estatica] = field(default_factory=list)
    hsrp_vrrp: list[HsrpVrrp] = field(default_factory=list)
    nat_flag: bool = False
    pim_neighbor: list[PimNeighbor] = field(default_factory=list)
    huecos: list[Hueco] = field(default_factory=list)
    salto: list[Salto] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
