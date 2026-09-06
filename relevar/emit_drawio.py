"""Genera nodo.drawio (XML mxGraph): Nodo, Rack, una hoja por VRF."""

from __future__ import annotations

from html import escape
from pathlib import Path
from xml.sax.saxutils import escape as xml_esc

from relevar.models import Inventario


def _cell(cid: str, value: str, x: float, y: float, w: float, h: float, style: str, parent: str = "1") -> str:
    return (
        f'<mxCell id="{xml_esc(cid)}" value="{escape(value)}" style="{xml_esc(style)}" '
        f'vertex="1" parent="{xml_esc(parent)}">'
        f'<mxGeometry x="{x:.0f}" y="{y:.0f}" width="{w:.0f}" height="{h:.0f}" as="geometry"/>'
        f"</mxCell>"
    )


def _edge(cid: str, source: str, target: str, label: str, style: str, parent: str = "1") -> str:
    lab = escape(label) if label else ""
    return (
        f'<mxCell id="{xml_esc(cid)}" value="{lab}" style="{xml_esc(style)}" '
        f'edge="1" parent="{xml_esc(parent)}" source="{xml_esc(source)}" target="{xml_esc(target)}">'
        f'<mxGeometry relative="1" as="geometry"/>'
        f"</mxCell>"
    )


def _diagram(name: str, did: str, cells: list[str], width: int = 1200, height: int = 900) -> str:
    body = "\n".join(cells)
    return (
        f'<diagram id="{xml_esc(did)}" name="{xml_esc(name)}">'
        f'<mxGraphModel dx="1000" dy="700" grid="1" gridSize="10" guides="1" tooltips="1" '
        f'connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{width}" '
        f'pageHeight="{height}" math="0" shadow="0">'
        f"<root>"
        f'<mxCell id="0"/>'
        f'<mxCell id="1" parent="0"/>'
        f"{body}"
        f"</root></mxGraphModel></diagram>"
    )


_CE = "rounded=1;whiteSpace=wrap;html=1;fillColor=#1a1a1a;fontColor=#ffffff;strokeColor=#666666;fontSize=12;"
_L2 = "rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;fontSize=11;"
_OSPF = "rounded=1;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#82b366;fontSize=11;"
_CDP = "rounded=1;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;fontSize=11;"
_ODF = "rounded=0;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=#333333;fontSize=10;"
_FC = "rounded=0;whiteSpace=wrap;html=1;fillColor=#f8cecc;strokeColor=#b85450;fontSize=8;"
_FC_EMPTY = "rounded=0;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#999999;fontSize=8;"
_RACK = "rounded=0;whiteSpace=wrap;html=1;fillColor=#eeeeee;strokeColor=#333333;"
_U = "text;html=1;align=right;verticalAlign=middle;fontSize=8;fontColor=#666666;"
_EDGE_OSPF = "endArrow=classic;html=1;strokeColor=#82b366;fontSize=9;"
_EDGE_CDP = "endArrow=none;html=1;dashed=1;strokeColor=#d6b656;fontSize=9;"
_EDGE_CU = "endArrow=none;html=1;strokeColor=#333333;fontSize=9;"
_EDGE_FO = "endArrow=none;html=1;strokeColor=#b85450;fontSize=9;dashed=1;"


def _page_nodo(inv: Inventario) -> str:
    cells = [
        _cell("title", f"Nodo {inv.nodo.hostname}\n{inv.nodo.ip_ope}  {inv.nodo.plataforma}", 40, 20, 360, 60, _CE),
    ]
    y = 110
    cells.append(_cell("vrfhdr", "VRFs", 40, y, 360, 24, "text;html=1;align=left;fontStyle=1;fontSize=12;"))
    y = 140
    for i, vrf in enumerate(inv.vrf):
        cells.append(
            _cell(
                f"vrf{i}",
                f"{vrf.nombre}  RD {vrf.rd or '—'}  {', '.join(vrf.protocolos) or '—'}",
                40,
                y,
                360,
                32,
                "rounded=1;whiteSpace=wrap;html=1;fillColor=#e1d5e7;strokeColor=#9673a6;",
            )
        )
        y += 40
    y += 10
    cells.append(_cell("uphdr", "Uplinks / bundles (ver Rack / ODF)", 40, y, 500, 24, "text;html=1;align=left;fontStyle=1;"))
    y += 30
    for i, c in enumerate(inv.conexion):
        dest = c.equipo_remoto or c.sitio_remoto or "—"
        odf = f"{c.patchera_id}:{c.patchera_puerto}" if c.patchera_id else ""
        cells.append(
            _cell(
                f"up{i}",
                f"{c.clase}  {c.if_local} → {dest}  {odf}",
                40,
                y,
                500,
                28,
                "rounded=0;whiteSpace=wrap;html=1;align=left;fillColor=#fafafa;strokeColor=#999999;",
            )
        )
        y += 34
    return _diagram("Nodo", "nodo", cells)


def _u_y(cabinet_y: float, unit: float, ru: int, alto: int = 1) -> float:
    top_u = ru + alto - 1
    return cabinet_y + (42 - top_u) * unit


def _page_rack(inv: Inventario) -> str:
    unit = 16
    cab_x, cab_y, cab_w = 80, 30, 280
    cab_h = 42 * unit
    cells = [
        _cell("cab", "", cab_x, cab_y, cab_w, cab_h, _RACK),
        _cell("rlabel", inv.rack.nombre + "  frente  (U inferida)", 80, 8, 280, 18, "text;html=1;align=center;fontSize=11;fontStyle=1;"),
    ]
    for u in range(1, 43):
        y = _u_y(cab_y, unit, u, 1)
        if u % 2 == 0 or u in {1, 42}:
            cells.append(_cell(f"u{u}", str(u), cab_x - 28, y, 24, unit, _U))
    ids_eq: dict[str, str] = {}
    for i, eq in enumerate(inv.equipo_rack):
        cid = f"eq{i}"
        ids_eq[eq.hostname] = cid
        y = _u_y(cab_y, unit, eq.ru_inicio, eq.ru_alto)
        h = eq.ru_alto * unit
        style = _CE if eq.rol == "CE" else _L2
        ports = " ".join(eq.faceplate[:8])
        cells.append(
            _cell(
                cid,
                f"{eq.hostname}\n{eq.plataforma}\n{ports}",
                cab_x + 8,
                y + 1,
                cab_w - 16,
                max(h - 2, unit),
                style,
            )
        )
    fc_ids: dict[int, str] = {}
    for p in inv.patchera:
        y = _u_y(cab_y, unit, p.ru_inicio, 1)
        cells.append(
            _cell(
                f"odf-{p.id}",
                f"{p.id}  {p.tipo}",
                cab_x + 8,
                y + 1,
                cab_w - 16,
                unit - 2,
                _ODF,
            )
        )
        n = min(p.n_conectores, 24)
        for nro in range(1, n + 1):
            used = nro in p.puertos_usados
            fx = cab_x + cab_w + 20 + ((nro - 1) % 8) * 22
            fy = y + ((nro - 1) // 8) * 18
            cid = f"fc-{p.id}-{nro}"
            fc_ids[nro] = cid
            conn = next((c for c in inv.conexion if c.patchera_id == p.id and c.patchera_puerto == nro), None)
            label = str(nro)
            if conn and conn.sitio_remoto:
                label = f"{nro}\n{conn.sitio_remoto[:8]}"
            cells.append(_cell(cid, label, fx, fy, 20, 16, _FC if used else _FC_EMPTY))
    ce_id = ids_eq.get(inv.nodo.hostname, "eq0")
    for i, c in enumerate(inv.conexion):
        if c.clase == "local" and c.equipo_remoto and c.equipo_remoto in ids_eq:
            cells.append(
                _edge(
                    f"cl{i}",
                    ce_id,
                    ids_eq[c.equipo_remoto],
                    f"{c.if_local} ↔ {c.if_remota}",
                    _EDGE_CU,
                )
            )
        elif c.clase in {"exterior", "desconocida"} and c.patchera_puerto in fc_ids:
            cells.append(
                _edge(
                    f"cf{i}",
                    ce_id,
                    fc_ids[c.patchera_puerto],
                    f"{c.if_local}  {c.sitio_remoto}",
                    _EDGE_FO,
                )
            )
    return _diagram("Rack", "rack", cells, width=900, height=800)


def _page_vrf(inv: Inventario, vrf_name: str) -> str:
    cells = [
        _cell("ce", inv.nodo.hostname, 320, 40, 200, 50, _CE),
    ]
    nbs = [o for o in inv.ospf_neighbor if o.vrf == vrf_name]
    l2_local = [
        c
        for c in inv.conexion
        if c.clase == "local" and (c.vrf == vrf_name or not c.vrf)
    ]
    x = 40
    for i, nb in enumerate(nbs):
        cid = f"ospf{i}"
        cells.append(
            _cell(
                cid,
                f"{nb.hostname_vecino or nb.neighbor_rid}\nRID {nb.neighbor_rid}\n{nb.neighbor_ip}",
                x,
                220,
                180,
                70,
                _OSPF,
            )
        )
        label = f"{nb.if_logica}  VLAN{nb.vlan or '—'}  area {nb.area or '—'}  cost {nb.costo or '—'}  {nb.estado}"
        cells.append(_edge(f"eospf{i}", "ce", cid, label, _EDGE_OSPF))
        x += 220
    x = 40
    for i, c in enumerate(l2_local):
        cid = f"l2{i}"
        cells.append(
            _cell(
                cid,
                f"{c.equipo_remoto}\nL2 CDP/LLDP",
                x,
                380,
                160,
                50,
                _CDP,
            )
        )
        cells.append(
            _edge(f"el2{i}", "ce", cid, f"{c.if_local} ↔ {c.if_remota}", _EDGE_CDP)
        )
        x += 200
    ifs = [i for i in inv.interfaz if i.vrf == vrf_name]
    y = 500
    cells.append(_cell("ifhdr", "SAP candidatos (no es tabla de ruteo)", 40, y, 400, 20, "text;html=1;align=left;fontStyle=1;fontSize=10;"))
    y += 24
    for i, iface in enumerate(ifs[:8]):
        cells.append(
            _cell(
                f"if{i}",
                f"{iface.logica}  {iface.ip}{'/' + iface.mask if iface.mask else ''}  {iface.desc}",
                40,
                y,
                520,
                22,
                "rounded=0;whiteSpace=wrap;html=1;align=left;fontSize=9;fillColor=#fafafa;",
            )
        )
        y += 26
    return _diagram(f"VRF-{vrf_name}", f"vrf-{vrf_name}", cells)


def render_drawio(inv: Inventario) -> str:
    pages = [_page_nodo(inv), _page_rack(inv)]
    for vrf in inv.vrf:
        pages.append(_page_vrf(inv, vrf.nombre))
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<mxfile host="relevar" agent="relevar" version="22.0.0">'
        + "".join(pages)
        + "</mxfile>\n"
    )


def write_drawio(inv: Inventario, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_drawio(inv), encoding="utf-8")
    return path
