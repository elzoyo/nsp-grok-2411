"""Parsers de shows Cisco IOS / IOS-XE (MVP). Parsers propios, sin NMS."""

from __future__ import annotations

import re
from ipaddress import ip_interface

from relevar.models import (
    Interfaz,
    OspfNeighbor,
    OspfProcess,
    VecinoL2,
    Vrf,
)


def _norm_if(name: str) -> str:
    text = (name or "").strip()
    repl = (
        ("GigabitEthernet", "Gi"),
        ("TenGigabitEthernet", "Te"),
        ("FastEthernet", "Fa"),
        ("Port-channel", "Po"),
        ("port-channel", "Po"),
        ("Ethernet", "Eth"),
        ("Loopback", "Lo"),
        ("Vlan", "Vlan"),
        ("VLAN", "Vlan"),
    )
    for long, short in repl:
        if text.startswith(long):
            return short + text[len(long) :]
    return text


def _parent_if(logical: str) -> str:
    name = _norm_if(logical)
    if name.lower().startswith("vlan"):
        return name
    if "." in name:
        return name.rsplit(".", 1)[0]
    return name


def _vlan_of(logical: str, desc: str = "") -> str:
    name = _norm_if(logical)
    if name.lower().startswith("vlan") and name[4:].isdigit():
        return name[4:]
    if "." in name:
        tail = name.rsplit(".", 1)[-1]
        if tail.isdigit():
            return tail
    m = re.search(r"vlan\s*(\d+)", desc, re.I)
    return m.group(1) if m else ""


def parse_hostname(raw: str) -> str:
    m = re.search(r"^hostname\s+(\S+)", raw, re.M)
    if m:
        return m.group(1)
    m = re.search(r"^(\S+)\s+uptime is ", raw, re.M)
    return m.group(1) if m else ""


def parse_version(raw: str) -> dict[str, str]:
    ios = ""
    m = re.search(r"Version\s+([0-9][0-9A-Za-z._()-]+)", raw)
    if m:
        ios = m.group(1)
    plataforma = ""
    m = re.search(r"^cisco\s+(\S+)", raw, re.M | re.I)
    if m:
        plataforma = m.group(1).rstrip(",")
    uptime = ""
    m = re.search(r"uptime is\s+(.+)$", raw, re.M)
    if m:
        uptime = m.group(1).strip()
    nx = "NX-OS" in raw or "Cisco Nexus" in raw
    return {
        "ios": ios,
        "plataforma": plataforma,
        "uptime": uptime,
        "family": "nxos" if nx else "ios",
    }


def parse_inventory(raw: str) -> list[str]:
    out: list[str] = []
    for m in re.finditer(
        r"NAME:\s*[\"']?([^\"'\n]+)[\"']?\s*,\s*DESCR:\s*[\"']?([^\"'\n]+)[\"']?",
        raw,
    ):
        out.append(f"{m.group(1).strip()}: {m.group(2).strip()}")
    return out


def parse_vrfs(raw_vrf: str, raw_detail: str = "") -> list[Vrf]:
    vrfs: dict[str, Vrf] = {}
    # show vrf / show ip vrf
    for line in raw_vrf.splitlines():
        if re.match(r"^\s*Name\s+", line) or not line.strip() or line.lstrip().startswith("!"):
            continue
        m = re.match(
            r"^\s*(\S+)\s+(\S+)\s+(\S+)(?:\s+(\S.*))?$",
            line,
        )
        if not m:
            continue
        name, rd, proto = m.group(1), m.group(2), m.group(3)
        if name.lower() in {"name", "vrf"} or name.startswith("!"):
            continue
        if rd.lower() in {"default", "rd"}:
            continue
        ifaces = [p.strip() for p in (m.group(4) or "").split() if p.strip()]
        vrfs[name] = Vrf(
            nombre=name,
            rd="" if rd in {"<not", "<not set>", "not"} else rd,
            protocolos=[p.strip() for p in proto.split(",") if p.strip()],
            interfaces=[_norm_if(i) for i in ifaces],
        )
    # continuation interface lines (indented, no VRF name)
    current = ""
    for line in raw_vrf.splitlines():
        m = re.match(r"^\s*(\S+)\s+\S+\s+\S+", line)
        if m and m.group(1) in vrfs:
            current = m.group(1)
            continue
        if current and re.match(r"^\s+\S+", line) and not re.match(r"^\s*Name\s+", line):
            extra = [_norm_if(p) for p in line.split() if p]
            for iface in extra:
                if iface not in vrfs[current].interfaces:
                    vrfs[current].interfaces.append(iface)
    # show vrf detail — RD / RT
    block_name = ""
    for line in raw_detail.splitlines():
        m = re.match(r"^VRF\s+(\S+)", line)
        if m:
            block_name = m.group(1).rstrip(";")
            vrfs.setdefault(block_name, Vrf(nombre=block_name))
            continue
        if not block_name:
            continue
        m = re.search(r"RD:\s+(\S+)", line)
        if m and vrfs[block_name].rd in {"", "<not", "<not set>"}:
            vrfs[block_name].rd = m.group(1)
        m = re.search(r"route-target\s+(?:export|import|both)\s+(\S+)", line, re.I)
        if m and m.group(1) not in vrfs[block_name].rt:
            vrfs[block_name].rt.append(m.group(1))
        m = re.match(r"^\s+(Gi\S+|Te\S+|Fa\S+|Po\S+|Vlan\S+|Lo\S+|Eth\S+)", line)
        if m:
            iface = _norm_if(m.group(1))
            if iface not in vrfs[block_name].interfaces:
                vrfs[block_name].interfaces.append(iface)
    return list(vrfs.values())


def parse_vrf_interfaces(raw: str) -> list[tuple[str, str, str, str]]:
    """(iface, ip, vrf, protocol) from show ip vrf interfaces."""
    rows: list[tuple[str, str, str, str]] = []
    for line in raw.splitlines():
        if re.match(r"^\s*Interface\s+", line) or not line.strip():
            continue
        parts = line.split()
        if len(parts) < 3:
            continue
        iface, ip, vrf = parts[0], parts[1], parts[2]
        proto = parts[3] if len(parts) > 3 else ""
        if iface.lower() == "interface":
            continue
        rows.append((_norm_if(iface), ip, vrf, proto))
    return rows


def parse_ip_brief(raw: str) -> list[tuple[str, str, str, str]]:
    """(iface, ip, ok, method/status leftover) from show ip interface brief."""
    rows: list[tuple[str, str, str, str]] = []
    for line in raw.splitlines():
        if re.match(r"^Interface\s+", line) or not line.strip():
            continue
        parts = line.split()
        if len(parts) < 6:
            continue
        iface, ip = _norm_if(parts[0]), parts[1]
        status, proto = parts[-2], parts[-1]
        estado = "up" if status.lower() == "up" and proto.lower() == "up" else "down"
        rows.append((iface, ip, estado, ""))
    return rows


def parse_descriptions(raw: str) -> dict[str, tuple[str, str, str]]:
    """iface -> (status, protocol, description)."""
    out: dict[str, tuple[str, str, str]] = {}
    for line in raw.splitlines():
        m = re.match(
            r"^(\S+)\s+(up|down|admin(?:istratively)?\s+down|deleted)\s+"
            r"(up|down)\s*(.*)$",
            line,
            re.I,
        )
        if not m:
            continue
        iface = _norm_if(m.group(1))
        if iface.lower() == "interface":
            continue
        out[iface] = (m.group(2).lower(), m.group(3).lower(), m.group(4).strip())
    return out


def parse_etherchannel(raw: str) -> dict[str, str]:
    """member iface -> bundle PoN."""
    out: dict[str, str] = {}
    current = ""
    for line in raw.splitlines():
        m = re.search(r"\b(Po|Port-channel)\s*(\d+)\b", line, re.I)
        if m and re.match(r"^\s*\d+", line) or (m and "Po" in line[:8]):
            current = f"Po{m.group(2)}"
        members = re.findall(
            r"((?:Gi|Te|Fa|Eth)\S+)",
            line,
        )
        if current:
            for mem in members:
                out[_norm_if(mem.split("(")[0])] = current
    return out


def parse_cdp_detail(raw: str) -> list[VecinoL2]:
    chunks = re.split(r"-{5,}", raw)
    out: list[VecinoL2] = []
    for chunk in chunks:
        if "Device ID" not in chunk and "DeviceID" not in chunk:
            continue
        host = _first(r"Device ID:\s*(\S+)", chunk)
        ip = _first(r"IP address:\s*(\S+)", chunk)
        plat = _first(r"Platform:\s*([^,\n]+)", chunk)
        local = _first(r"Interface:\s*([^,\n]+)", chunk)
        remote = _first(r"Port ID \(outgoing port\):\s*(\S+)", chunk)
        if not local and not host:
            continue
        out.append(
            VecinoL2(
                proto="cdp",
                if_local=_norm_if(local),
                if_remota=_norm_if(remote),
                hostname=host.split(".")[0] if host else "",
                ip_mgmt=ip,
                plataforma=plat.strip(),
            )
        )
    return out


def parse_lldp_detail(raw: str) -> list[VecinoL2]:
    chunks = re.split(r"(?=Local Intf:)|(?=Chassis id:)", raw)
    out: list[VecinoL2] = []
    for chunk in chunks:
        local = _first(r"Local Intf:\s*(\S+)", chunk)
        remote = _first(r"Port id:\s*(\S+)", chunk) or _first(
            r"Port Description:\s*(\S+)", chunk
        )
        host = _first(r"System Name:\s*(\S+)", chunk)
        ip = _first(r"Management Address:\s*(\S+)", chunk) or _first(
            r"IP:\s*(\S+)", chunk
        )
        plat = _first(r"System Description:\s*(.+)", chunk)
        if not local and not host:
            continue
        out.append(
            VecinoL2(
                proto="lldp",
                if_local=_norm_if(local),
                if_remota=_norm_if(remote),
                hostname=(host or "").split(".")[0],
                ip_mgmt=ip,
                plataforma=(plat or "").strip()[:80],
            )
        )
    return out


def parse_ospf_process(raw: str, vrf: str) -> list[OspfProcess]:
    procs: list[OspfProcess] = []
    pid = _first(r"Routing Process\s+[\"']?ospf\s+(\d+)", raw) or _first(
        r"Process ID\s+(\d+)", raw
    )
    rid = _first(r"Router ID\s+(\S+)", raw)
    areas = re.findall(r"Area\s+(?:BACKBONE\()?([0-9.]+)\)?", raw)
    if pid or rid:
        procs.append(
            OspfProcess(
                vrf=vrf,
                process_id=pid,
                router_id=rid.rstrip(","),
                areas=list(dict.fromkeys(areas)) or ["0"],
            )
        )
    return procs


def parse_ospf_neighbors(raw: str, vrf: str) -> list[OspfNeighbor]:
    out: list[OspfNeighbor] = []
    for line in raw.splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        if not re.match(r"^\d+\.\d+\.\d+\.\d+$", parts[0]):
            continue
        if not re.match(r"^\d+\.\d+\.\d+\.\d+$", parts[-2]):
            continue
        estado = ""
        for tok in parts[1:-2]:
            up = tok.upper().replace("/", "")
            if up.startswith(("FULL", "2WAY", "INIT", "EXSTART", "EXCHANGE", "LOADING", "DOWN")):
                estado = tok.split("/", 1)[0]
                break
        out.append(
            OspfNeighbor(
                vrf=vrf,
                neighbor_rid=parts[0],
                estado=estado or parts[2].split("/", 1)[0],
                neighbor_ip=parts[-2],
                if_logica=_norm_if(parts[-1]),
            )
        )
    return out


def parse_ospf_interface(raw: str, vrf: str) -> dict[str, dict[str, str]]:
    """logical if -> {area, cost, network_type, ip, process_id, router_id}."""
    out: dict[str, dict[str, str]] = {}
    current = ""
    for line in raw.splitlines():
        m = re.match(r"^(\S+)\s+is up, line protocol is up", line)
        if m:
            current = _norm_if(m.group(1))
            out[current] = {}
            continue
        if not current:
            continue
        m = re.search(r"Internet Address\s+(\S+),\s+Area\s+(\S+)", line)
        if m:
            out[current]["ip"] = m.group(1)
            out[current]["area"] = m.group(2).rstrip(",")
        m = re.search(
            r"Process ID\s+(\d+),\s+Router ID\s+(\S+),\s+Network Type\s+(\S+),\s+Cost:\s+(\d+)",
            line,
        )
        if m:
            out[current]["process_id"] = m.group(1)
            out[current]["router_id"] = m.group(2).rstrip(",")
            out[current]["network_type"] = m.group(3).rstrip(",").lower()
            out[current]["costo"] = m.group(4)
    return out


def parse_route_summary(raw: str, vrf: str) -> list[tuple[str, int]]:
    """[(code, count), ...] from show ip route vrf X summary or full table codes."""
    counts: dict[str, int] = {}
    m = re.search(r"(\d+)\s+connected", raw, re.I)
    if m:
        counts["C"] = int(m.group(1))
    m = re.search(r"(\d+)\s+static", raw, re.I)
    if m:
        counts["S"] = int(m.group(1))
    m = re.search(r"(\d+)\s+ospf", raw, re.I)
    if m:
        counts["O"] = int(m.group(1))
    m = re.search(r"(\d+)\s+bgp", raw, re.I)
    if m:
        counts["B"] = int(m.group(1))
    if counts:
        return list(counts.items())
    for line in raw.splitlines():
        code = line[:3].strip()
        if code[:1] in {"C", "S", "O", "B", "D", "R", "i"} and "/" in line:
            key = code[0]
            counts[key] = counts.get(key, 0) + 1
    return list(counts.items())


def parse_static_routes(raw: str, vrf: str) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    for line in raw.splitlines():
        m = re.search(
            r"S\s+(\d+\.\d+\.\d+\.\d+/\d+).+?(?:via\s+(\d+\.\d+\.\d+\.\d+))?(?:,\s+(\S+))?",
            line,
        )
        if m:
            rows.append((m.group(1), m.group(2) or "", _norm_if(m.group(3) or "")))
    return rows


def parse_standby(raw: str) -> list[tuple[str, str, str, str]]:
    """(iface, group, vip, state)."""
    rows: list[tuple[str, str, str, str]] = []
    for line in raw.splitlines():
        parts = line.split()
        if len(parts) < 5 or parts[0].lower() in {"interface", "intf"}:
            continue
        if not re.match(r"^(Gi|Te|Fa|Po|Vl|Eth|Lo)", parts[0], re.I) and not parts[
            0
        ].lower().startswith("vlan"):
            continue
        iface = _norm_if(parts[0])
        grp = parts[1]
        vip = next((p for p in parts if re.match(r"\d+\.\d+\.\d+\.\d+", p)), "")
        state = next(
            (p for p in parts if p.lower() in {"active", "standby", "listen", "init"}),
            "",
        )
        rows.append((iface, grp, vip, state))
    return rows


def cidr_of(ip: str, mask: str = "") -> tuple[str, str]:
    if not ip or ip.lower() in {"unassigned", "n/a", "unset"}:
        return "", ""
    if "/" in ip:
        try:
            iface = ip_interface(ip)
            return str(iface.ip), str(iface.network.prefixlen)
        except ValueError:
            return ip, ""
    return ip, mask


def build_interfaces(
    vrf_ifs: list[tuple[str, str, str, str]],
    brief: list[tuple[str, str, str, str]],
    descs: dict[str, tuple[str, str, str]],
    bundles: dict[str, str],
) -> list[Interfaz]:
    by_name: dict[str, Interfaz] = {}
    for iface, ip, vrf, proto in vrf_ifs:
        ip_addr, mask = cidr_of(ip)
        st_proto = proto.lower() if proto else ""
        desc = descs.get(iface, ("", "", ""))[2]
        estado = "up" if st_proto == "up" else (st_proto or "unknown")
        logical = iface
        physical = _parent_if(logical)
        by_name[logical] = Interfaz(
            fisica=physical,
            logica=logical,
            vlan=_vlan_of(logical, desc),
            vrf=vrf,
            ip=ip_addr,
            mask=mask,
            estado=estado,
            desc=desc,
            bundle=bundles.get(physical, bundles.get(logical, "")),
        )
    for iface, ip, estado, _ in brief:
        if iface in by_name:
            if not by_name[iface].ip:
                addr, mask = cidr_of(ip)
                by_name[iface].ip = addr
                by_name[iface].mask = mask
            if by_name[iface].estado in {"", "unknown"}:
                by_name[iface].estado = estado
            continue
        desc = descs.get(iface, ("", "", ""))[2]
        addr, mask = cidr_of(ip)
        by_name[iface] = Interfaz(
            fisica=_parent_if(iface),
            logica=iface,
            vlan=_vlan_of(iface, desc),
            vrf="",
            ip=addr,
            mask=mask,
            estado=estado,
            desc=desc,
            bundle=bundles.get(_parent_if(iface), ""),
        )
    for iface, (_st, _pr, desc) in descs.items():
        if iface not in by_name:
            by_name[iface] = Interfaz(
                fisica=_parent_if(iface),
                logica=iface,
                vlan=_vlan_of(iface, desc),
                desc=desc,
                bundle=bundles.get(_parent_if(iface), ""),
            )
        elif not by_name[iface].desc:
            by_name[iface].desc = desc
    return list(by_name.values())


def _first(pattern: str, text: str) -> str:
    m = re.search(pattern, text)
    return m.group(1).strip() if m else ""
