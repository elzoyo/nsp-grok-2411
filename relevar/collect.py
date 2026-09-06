"""Colector de shows. Un archivo raw por comando. No show tech ni LSDB completa."""

from __future__ import annotations

from pathlib import Path

from relevar import ssh as sshmod
from relevar.errors import RelevarError

GLOBAL_COMMANDS = [
    "show version",
    "show inventory",
    "show running-config | include hostname",
    "show ip domain-name",
    "show clock",
    "show users",
    "show ip ssh",
    "show vrf",
    "show ip vrf",
    "show vrf detail",
    "show ip vrf interfaces",
    "show ip protocols",
    "show interfaces description",
    "show ip interface brief",
    "show interfaces status",
    "show etherchannel summary",
    "show port-channel summary",
    "show vlan brief",
    "show interfaces trunk",
    "show running-config | section interface",
    "show cdp neighbors",
    "show cdp neighbors detail",
    "show lldp neighbors",
    "show lldp neighbors detail",
    "show spanning-tree summary",
    "show mac address-table count",
    "show standby brief",
    "show vrrp brief",
    "show ip nat translations",
    "show ip nat statistics",
    "show running-config",
]

VRF_COMMANDS = [
    "show ip protocols vrf {vrf}",
    "show ip interface brief vrf {vrf}",
    "show ip ospf vrf {vrf}",
    "show ip ospf neighbor vrf {vrf}",
    "show ip ospf neighbor detail vrf {vrf}",
    "show ip ospf interface brief vrf {vrf}",
    "show ip ospf interface vrf {vrf}",
    "show ip ospf database vrf {vrf}",
    "show ip route vrf {vrf} summary",
    "show ip route vrf {vrf}",
    "show ip route vrf {vrf} ospf",
    "show ip route vrf {vrf} static",
    "show ip arp vrf {vrf}",
    "show ip pim vrf {vrf} neighbor",
]


def slug(command: str) -> str:
    keep = []
    for ch in command.lower():
        keep.append(ch if ch.isalnum() else "_")
    text = "".join(keep)
    while "__" in text:
        text = text.replace("__", "_")
    return text.strip("_")[:120]


def write_raw(raw_dir: Path, command: str, output: str) -> Path:
    raw_dir.mkdir(parents=True, exist_ok=True)
    path = raw_dir / f"{slug(command)}.txt"
    header = f"! command: {command}\n"
    path.write_text(header + (output or "") + ("\n" if output and not output.endswith("\n") else ""), encoding="utf-8")
    return path


def read_raw_map(raw_dir: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not raw_dir.is_dir():
        raise RelevarError(f"no existe el directorio raw: {raw_dir}", code=1)
    for path in sorted(raw_dir.glob("*.txt")):
        text = path.read_text(encoding="utf-8", errors="replace")
        cmd = ""
        if text.startswith("! command:"):
            first, _, rest = text.partition("\n")
            cmd = first.split(":", 1)[1].strip()
            text = rest
        else:
            cmd = path.stem.replace("_", " ")
        out[cmd] = text
        out[path.stem] = text
    return out


def raw_get(raw: dict[str, str], *names: str) -> str:
    for name in names:
        if name in raw and raw[name].strip():
            return raw[name]
        slug_name = slug(name)
        if slug_name in raw and raw[slug_name].strip():
            return raw[slug_name]
    return ""


def collect_live(
    host: str,
    user: str,
    password: str,
    raw_dir: Path,
    vrfs: list[str] | None = None,
) -> dict[str, str]:
    conn = sshmod.connect(host, user, password)
    collected: dict[str, str] = {}
    try:
        for cmd in GLOBAL_COMMANDS:
            try:
                out = sshmod.send(conn, cmd)
            except RelevarError:
                out = ""
            write_raw(raw_dir, cmd, out)
            collected[cmd] = out
            collected[slug(cmd)] = out
        discovered = vrfs or _vrf_names_from_show(collected.get("show vrf") or collected.get("show ip vrf") or "")
        if not discovered:
            discovered = ["default"]
        for vrf in discovered:
            for tmpl in VRF_COMMANDS:
                cmd = tmpl.format(vrf=vrf)
                try:
                    out = sshmod.send(conn, cmd)
                except RelevarError:
                    out = ""
                write_raw(raw_dir, cmd, out)
                collected[cmd] = out
                collected[slug(cmd)] = out
    finally:
        sshmod.close(conn)
    return collected


def _vrf_names_from_show(raw: str) -> list[str]:
    from relevar.parse import parse_vrfs

    return [v.nombre for v in parse_vrfs(raw)]
