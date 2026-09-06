from pathlib import Path

from relevar.cli import run
from relevar.parse import parse_cdp_detail, parse_ospf_neighbors, parse_vrfs
from relevar.pipeline import from_raw_dir

FIXTURE = Path(__file__).parent / "fixtures" / "relevar" / "raw"


def test_parse_vrfs_multi():
    raw = (FIXTURE / "show_vrf.txt").read_text()
    vrfs = {v.nombre: v for v in parse_vrfs(raw)}
    assert set(vrfs) == {"OPE", "CORP", "TRA"}
    assert "Vlan10" in vrfs["OPE"].interfaces


def test_parse_ospf_neighbor_full_dash():
    raw = (FIXTURE / "show_ip_ospf_neighbor_vrf_CORP.txt").read_text()
    nbs = parse_ospf_neighbors(raw, "CORP")
    assert len(nbs) == 1
    assert nbs[0].neighbor_rid == "10.1.1.1"
    assert nbs[0].estado == "FULL"
    assert nbs[0].if_logica == "Gi1/0/24.110"


def test_parse_cdp_local_switch():
    raw = (FIXTURE / "show_cdp_neighbors_detail.txt").read_text()
    vecs = parse_cdp_detail(raw)
    assert vecs[0].hostname == "SW-PAYSANDU-L2"
    assert vecs[0].if_local == "Gi1/0/48"


def test_inventario_from_fixture(tmp_path):
    inv = from_raw_dir(FIXTURE, "10.0.6.250", tmp_path)
    assert inv.nodo.hostname == "NOD-PAYSANDU-CE"
    assert {v.nombre for v in inv.vrf} == {"OPE", "CORP", "TRA"}
    assert len(inv.ospf_neighbor) == 2
    assert all(n.if_fisica for n in inv.ospf_neighbor)
    corp = next(n for n in inv.ospf_neighbor if n.vrf == "CORP")
    assert corp.if_fisica == "Gi1/0/24"
    assert corp.costo == "10"
    assert corp.area == "0"
    locales = [c for c in inv.conexion if c.clase == "local"]
    assert any(c.equipo_remoto == "SW-PAYSANDU-L2" for c in locales)
    sitios = {c.sitio_remoto for c in inv.conexion if c.clase == "exterior"}
    assert "MERCEDES" in sitios
    assert "SALTO" in sitios
    assert (tmp_path / "inventario.json").is_file()
    assert (tmp_path / "relevamiento.md").is_file()
    drawio = (tmp_path / "nodo.drawio").read_text()
    assert 'name="Nodo"' in drawio
    assert 'name="Rack"' in drawio
    assert 'name="VRF-OPE"' in drawio
    assert "ODF-1" in drawio
    assert "SW-PAYSANDU-L2" in drawio
    assert "MERCEDES" in drawio
    assert "SALTO" in drawio
    md = (tmp_path / "relevamiento.md").read_text()
    assert "Gi1/0/24.110" in md
    assert "SAP candidatos" in md


def test_no_vrfs_exits_3(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "show_version.txt").write_text(
        "! command: show version\nCisco IOS Software, Version 17.9.4a\n",
        encoding="utf-8",
    )
    (raw / "show_vrf.txt").write_text("! command: show vrf\n", encoding="utf-8")
    code = run(["--from-raw", str(raw), "--ip", "10.0.0.1"])
    assert code == 3


def test_cli_from_raw_writes_out(tmp_path, monkeypatch):
    # copy fixture raw into tmp so we don't dirty the tree
    import shutil

    node = tmp_path / "NOD-PAYSANDU-CE_10.0.6.250_20260905"
    shutil.copytree(FIXTURE, node / "raw")
    code = run(["--from-raw", str(node / "raw"), "--ip", "10.0.6.250"])
    assert code == 0
    assert (node / "nodo.drawio").is_file()
    assert (node / "inventario.json").is_file()
