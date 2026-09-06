from pathlib import Path

from relevar.cli import run
from relevar.models import Inventario, Nodo, OspfNeighbor, VecinoL2
from relevar.pipeline import from_raw_dir
from relevar.salto import confirmar_salto, mensaje_salto, proponer_saltos

FIXTURE = Path(__file__).parent / "fixtures" / "relevar" / "raw"


def test_proponer_l2_no_sitio_remoto(tmp_path):
    inv = from_raw_dir(FIXTURE, "10.0.6.250", tmp_path, saltar="no")
    props = proponer_saltos(inv)
    ips = {s.ip for s in props}
    roles = {s.ip: s.rol for s in props}
    assert "10.0.6.20" in ips
    assert roles["10.0.6.20"] == "l2"
    assert "10.110.1.1" not in ips
    assert "10.200.1.1" not in ips


def test_mensaje_incluye_objetivo():
    from relevar.models import Salto

    s = Salto(
        hostname="SW-PAYSANDU-L2",
        ip="10.0.6.20",
        rol="l2",
        objetivo="completar rack",
        origen="cdp",
    )
    text = mensaje_salto(s)
    assert "SW-PAYSANDU-L2" in text
    assert "10.0.6.20" in text
    assert "completar rack" in text
    assert "SSH" in text


def test_confirmar_flag_y_callback():
    from relevar.models import Salto

    s = Salto(hostname="X", ip="1.1.1.1", rol="l2", objetivo="t", origen="cdp")
    assert confirmar_salto(s, "yes") is True
    assert confirmar_salto(s, "no") is False
    seen: list[str] = []

    def _ask(msg: str) -> bool:
        seen.append(msg)
        return True

    assert confirmar_salto(s, None, _ask) is True
    assert "1.1.1.1" in seen[0]


def test_replay_vecinos_enriquece_rack(tmp_path):
    inv = from_raw_dir(FIXTURE, "10.0.6.250", tmp_path, saltar="yes")
    sw = next(s for s in inv.salto if s.ip == "10.0.6.20")
    assert sw.estado == "ok"
    eq = next(e for e in inv.equipo_rack if e.hostname == "SW-PAYSANDU-L2")
    assert "Gi0/1" in eq.faceplate or "Gi0/2" in eq.faceplate
    assert any(h.codigo == "vecino_de_vecino" for h in inv.huecos)
    md = (tmp_path / "relevamiento.md").read_text()
    assert "Saltos a vecinos" in md
    assert "SW-PAYSANDU-L2" in md


def test_saltar_no_no_aplica_vecinos(tmp_path):
    inv = from_raw_dir(FIXTURE, "10.0.6.250", tmp_path, saltar="no")
    assert all(s.estado == "rechazado" for s in inv.salto)
    eq = next(e for e in inv.equipo_rack if e.hostname == "SW-PAYSANDU-L2")
    assert "Gi0/2" not in eq.faceplate


def test_cli_saltar_yes(tmp_path):
    import shutil

    node = tmp_path / "NOD-PAYSANDU-CE_10.0.6.250_20260905"
    shutil.copytree(FIXTURE, node / "raw")
    code = run(["--from-raw", str(node / "raw"), "--ip", "10.0.6.250", "--saltar=yes"])
    assert code == 0
    text = (node / "relevamiento.md").read_text()
    assert "Saltos a vecinos" in text


def test_identidad_ospf_ope_sin_cdp():
    inv = Inventario(
        nodo=Nodo(hostname="NOD-PAYSANDU-CE", ip_ope="10.0.6.250"),
        ospf_neighbor=[
            OspfNeighbor(
                vrf="OPE",
                neighbor_rid="10.0.6.2",
                neighbor_ip="10.0.6.2",
                if_logica="Gi1/0/2",
                if_fisica="Gi1/0/2",
            )
        ],
    )
    props = proponer_saltos(inv)
    assert len(props) == 1
    assert props[0].rol == "identidad"
    assert props[0].ip == "10.0.6.2"


def test_no_saltar_ospf_otro_sitio():
    inv = Inventario(
        nodo=Nodo(hostname="NOD-PAYSANDU-CE", ip_ope="10.0.6.250"),
        ospf_neighbor=[
            OspfNeighbor(
                vrf="CORP",
                neighbor_rid="10.1.1.1",
                neighbor_ip="10.110.1.1",
                if_logica="Gi1/0/24.110",
                if_fisica="Gi1/0/24",
                hostname_vecino="",
            )
        ],
    )
    from relevar.models import Interfaz

    inv.interfaz = [
        Interfaz(
            fisica="Gi1/0/24",
            logica="Gi1/0/24.110",
            vrf="CORP",
            desc="CORP a MERCEDES",
        )
    ]
    assert proponer_saltos(inv) == []
