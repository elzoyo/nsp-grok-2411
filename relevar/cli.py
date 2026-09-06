"""CLI: relevar user@ip  (MEMORIA_RELEVAR §3)."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from relevar.collect import collect_live, read_raw_map
from relevar.errors import RelevarError
from relevar.pipeline import build_inventario, emit_all, node_dir
from relevar.salto import ejecutar_saltos
from relevar.ssh import credentials


def parse_target(spec: str) -> tuple[str, str]:
    if "@" not in spec:
        raise RelevarError("uso: relevar user@host", code=1)
    user, host = spec.rsplit("@", 1)
    if not user or not host:
        raise RelevarError("uso: relevar user@host", code=1)
    return user, host


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="relevar",
        description="Inventario pre-migración de un CE Cisco (por OPE). "
        "Antes de saltar a un vecino pregunta equipo, IP y objetivo.",
    )
    p.add_argument("target", nargs="?", help="user@ip  (IP de gestión en OPE)")
    p.add_argument("--vrf", default="", help="filtro de VRF, separadas por coma (OPE,CORP,TRA)")
    p.add_argument("--out", default="./nodos", help="directorio raíz de salida")
    p.add_argument(
        "--from-raw",
        default="",
        help="regenerar desde un directorio raw/ ya colectado (sin SSH)",
    )
    p.add_argument("--ip", default="", help="IP OPE a grabar en el inventario (default: host del target)")
    p.add_argument(
        "--saltar",
        default="",
        metavar="yes|no",
        help="yes = aceptar todos los saltos; no = no saltar; vacío = preguntar (live) o replay raw/vecinos",
    )
    return p


def _vrf_list(raw: str) -> list[str] | None:
    if not raw.strip():
        return None
    return [p.strip() for p in raw.split(",") if p.strip()]


def run(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return _run(args)
    except RelevarError as exc:
        print(f"relevar: {exc}", file=sys.stderr)
        return exc.code


def _run(args: argparse.Namespace) -> int:
    vrfs = _vrf_list(args.vrf)
    out_root = Path(args.out)
    if args.from_raw:
        raw_dir = Path(args.from_raw)
        if raw_dir.name != "raw" and (raw_dir / "raw").is_dir():
            dest = raw_dir
            raw_dir = raw_dir / "raw"
        else:
            dest = raw_dir.parent
        ip = args.ip
        if not ip and "_" in dest.name:
            bits = dest.name.split("_")
            if len(bits) >= 2 and bits[1].count(".") == 3:
                ip = bits[1]
        if not ip and args.target and "@" in args.target:
            ip = args.target.rsplit("@", 1)[1]
        if not ip:
            ip = "0.0.0.0"
        raw = read_raw_map(raw_dir)
        inv = build_inventario(raw, ip, vrfs)
        inv = ejecutar_saltos(inv, raw_dir, flag=_saltar_flag(args.saltar), live=False)
        dest.mkdir(parents=True, exist_ok=True)
        emit_all(inv, dest)
        _ok(inv, dest)
        return 0
    if not args.target:
        raise RelevarError("uso: relevar user@host [--vrf OPE,CORP] [--out ./nodos]", code=1)
    user, host = parse_target(args.target)
    password = credentials(user)
    ip = args.ip or host
    stamp = datetime.now(timezone.utc)
    # hostname still unknown: collect into temp raw then rename
    staging = out_root / f"_tmp_{host}_{stamp.strftime('%Y%m%d%H%M%S')}"
    raw_dir = staging / "raw"
    collect_live(host, user, password, raw_dir, vrfs)
    raw = read_raw_map(raw_dir)
    inv = build_inventario(raw, ip, vrfs)
    dest = node_dir(out_root, inv.nodo.hostname, ip, stamp)
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "raw").mkdir(exist_ok=True)
    for src in raw_dir.glob("*.txt"):
        target = dest / "raw" / src.name
        target.write_bytes(src.read_bytes())
    inv = ejecutar_saltos(
        inv,
        dest / "raw",
        user=user,
        password=password,
        flag=_saltar_flag(args.saltar),
        live=True,
    )
    emit_all(inv, dest)
    # cleanup staging
    for src in raw_dir.glob("*.txt"):
        src.unlink()
    try:
        raw_dir.rmdir()
        staging.rmdir()
    except OSError:
        pass
    _ok(inv, dest)
    return 0


def _saltar_flag(raw: str) -> str | None:
    text = (raw or "").strip().lower()
    if not text:
        return None
    if text in {"yes", "y", "si", "sí", "s"}:
        return "yes"
    if text in {"no", "n"}:
        return "no"
    raise RelevarError("--saltar=yes|no", code=1)


def _ok(inv, dest: Path) -> None:
    print(f"nodo {inv.nodo.hostname} ({inv.nodo.ip_ope})")
    print(f"  VRFs: {', '.join(v.nombre for v in inv.vrf) or '—'}")
    print(f"  OSPF vecinos: {len(inv.ospf_neighbor)}")
    print(f"  conexiones: {len(inv.conexion)}  huecos: {len(inv.huecos)}")
    if inv.salto:
        bits = ", ".join(f"{s.hostname or s.ip}:{s.estado}" for s in inv.salto)
        print(f"  saltos: {bits}")
    print(f"  {dest / 'inventario.json'}")
    print(f"  {dest / 'relevamiento.md'}")
    print(f"  {dest / 'nodo.drawio'}")


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
