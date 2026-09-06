from __future__ import annotations

from pathlib import Path

from relevar.models import Inventario


def render_md(inv: Inventario) -> str:
    n = inv.nodo
    lines = [
        f"# Relevamiento {n.hostname}",
        "",
        f"- IP OPE: `{n.ip_ope}`",
        f"- Plataforma: {n.plataforma or '—'}  IOS {n.ios or '—'}",
        f"- Uptime: {n.uptime or '—'}",
        f"- Rack: {inv.rack.nombre} ({inv.rack.unidades}U, posición {inv.rack.origen_posicion})",
        "",
        "## VRFs",
        "",
        "| VRF | RD | RT | Protocolos | Interfaces |",
        "|-----|----|----|------------|------------|",
    ]
    for v in inv.vrf:
        lines.append(
            f"| {v.nombre} | {v.rd or '—'} | {', '.join(v.rt) or '—'} | "
            f"{', '.join(v.protocolos) or '—'} | {', '.join(v.interfaces) or '—'} |"
        )
    lines += [
        "",
        "## Interfaces (SAP candidatos)",
        "",
        "| VRF | if_fisica | if_logica | vlan | ip/mask | estado | descripcion | bundle |",
        "|-----|-----------|-----------|------|---------|--------|-------------|--------|",
    ]
    for i in inv.interfaz:
        mask = f"/{i.mask}" if i.mask else ""
        ip = f"{i.ip}{mask}" if i.ip else "—"
        lines.append(
            f"| {i.vrf or '—'} | {i.fisica} | {i.logica} | {i.vlan or '—'} | "
            f"{ip} | {i.estado or '—'} | {i.desc or '—'} | {i.bundle or '—'} |"
        )
    lines += [
        "",
        "## Vecinos L2 (CDP/LLDP)",
        "",
        "| proto | if_local | if_remota | hostname | ip_mgmt | plataforma |",
        "|-------|----------|-----------|----------|---------|------------|",
    ]
    for v in inv.vecino_l2:
        lines.append(
            f"| {v.proto} | {v.if_local} | {v.if_remota or '—'} | {v.hostname or '—'} | "
            f"{v.ip_mgmt or '—'} | {v.plataforma or '—'} |"
        )
    lines += [
        "",
        "## Intermediarias OSPF",
        "",
        "| vrf | RID vecino | IP | estado | área | if_logica | if_fisica | vlan | costo | tipo | hostname |",
        "|-----|------------|----|--------|------|-----------|-----------|------|-------|------|----------|",
    ]
    for o in inv.ospf_neighbor:
        lines.append(
            f"| {o.vrf} | {o.neighbor_rid} | {o.neighbor_ip} | {o.estado} | {o.area or '—'} | "
            f"{o.if_logica} | {o.if_fisica or '—'} | {o.vlan or '—'} | {o.costo or '—'} | "
            f"{o.network_type or '—'} | {o.hostname_vecino or '—'} |"
        )
    if inv.ruta_resumen:
        lines += ["", "## Rutas (resumen)", "", "| VRF | origen | count |", "|-----|--------|-------|"]
        for r in inv.ruta_resumen:
            lines.append(f"| {r.vrf} | {r.origen} | {r.count} |")
    if inv.estatica:
        lines += ["", "## Estáticas", ""]
        for e in inv.estatica:
            lines.append(f"- `{e.vrf}` {e.prefijo} via {e.next_hop or e.iface or '—'}")
    if inv.hsrp_vrrp:
        lines += ["", "## HSRP/VRRP", ""]
        for h in inv.hsrp_vrrp:
            lines.append(f"- `{h.iface}` grupo {h.grupo} VIP {h.vip} {h.estado}")
    lines += [
        "",
        "## Conexiones (rack)",
        "",
        "| clase | medio | if_local | if_remota | equipo_remoto / sitio | ODF | origen |",
        "|-------|-------|----------|-----------|------------------------|-----|--------|",
    ]
    for c in inv.conexion:
        dest = c.equipo_remoto or c.sitio_remoto or "—"
        odf = f"{c.patchera_id}:{c.patchera_puerto}" if c.patchera_id else "—"
        lines.append(
            f"| {c.clase} | {c.medio} | {c.if_local} | {c.if_remota or '—'} | {dest} | {odf} | {c.origen} |"
        )
    lines += ["", "## Huecos", ""]
    if inv.huecos:
        for h in inv.huecos:
            lines.append(f"- `{h.codigo}`: {h.detalle}")
    else:
        lines.append("- (ninguno)")
    lines.append("")
    return "\n".join(lines)


def write_md(inv: Inventario, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_md(inv), encoding="utf-8")
    return path
