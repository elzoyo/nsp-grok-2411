from prompt_toolkit.document import Document

from nsp_grok.app import build_ctx
from nsp_grok.completer import NspCompleter, detect_create_kind
from nsp_grok.lab import Store


def _ctx():
    store = Store()
    return build_ctx(store, store.users["admin"])


def _texts(ctx, line: str) -> list[str]:
    comp = NspCompleter(ctx)
    doc = Document(line, len(line))
    return [c.text for c in comp.get_completions(doc, None)]


def test_detect_create_kind():
    assert detect_create_kind(["sap", "create"], []) == "sap"
    assert detect_create_kind(["create", "tunnel"], []) == "tunnel"
    assert detect_create_kind(["mpls", "lsp", "create"], []) == "lsp"
    assert detect_create_kind(["mpls", "path", "create"], []) == "path"
    assert detect_create_kind(["service", "create"], []) == "service"
    assert detect_create_kind(["create"], ["mpls", "tunnels"]) == "tunnel"
    assert detect_create_kind(["create"], ["mpls", "paths"]) == "path"


def test_sap_create_completes_service_and_site():
    ctx = _ctx()
    texts = _texts(ctx, "sap create service=")
    assert "service=100" in texts
    texts = _texts(ctx, "sap create service=100 site=")
    assert any(t.startswith("site=PE-BAIRES-01") for t in texts)
    texts = _texts(ctx, "sap create service=200 site=PE-BAIRES-01 port=")
    assert any("1/1/10" in t for t in texts)


def test_sdp_create_far_and_sdp_from_tunnels():
    ctx = _ctx()
    texts = _texts(ctx, "sdp create service=100 site=PE-BAIRES-01 far=")
    assert any("PE-CORDOBA-01" in t for t in texts)
    assert not any(t == "far=PE-BAIRES-01" for t in texts)
    texts = _texts(ctx, "sdp create service=100 site=PE-BAIRES-01 far=PE-CORDOBA-01 sdp=")
    assert "sdp=101" in texts


def test_tunnel_create_lsp_filtered_by_direction():
    ctx = _ctx()
    texts = _texts(ctx, "tunnel create from=PE-BAIRES-01 to=PE-CORDOBA-01 lsp=")
    assert "lsp=lsp-ba-cba" in texts
    assert "lsp=lsp-cba-ba" not in texts


def test_path_create_completes_site_and_hops():
    ctx = _ctx()
    texts = _texts(ctx, "mpls path create site=")
    assert any(t.startswith("site=PE-BAIRES-01") for t in texts)
    texts = _texts(ctx, "mpls path create site=PE-BAIRES-01 hops=")
    assert any(t.startswith("hops=PE-CORDOBA-01") for t in texts)
    texts = _texts(ctx, "mpls path create site=PE-BAIRES-01 hops=PE-CORDOBA-01,")
    assert any("P-CORE-01" in t for t in texts)
    texts = _texts(ctx, "mpls path create type=")
    assert "type=strict" in texts
    assert "type=loose" in texts


def test_service_create_customer_and_sites():
    ctx = _ctx()
    texts = _texts(ctx, "service create customer=")
    assert "customer=12" in texts
    texts = _texts(ctx, "service create type=vprn customer=12 sites=")
    assert any(t.startswith("sites=PE-BAIRES-01") for t in texts)
