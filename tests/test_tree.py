from nsp_grok.lab import Store
from nsp_grok.tree import build_tree, pwd, resolve


def _root():
    store = Store()
    user = store.users["admin"]
    return store, user, build_tree(store, user)


def test_root_children():
    _store, _user, root = _root()
    assert set(root.children) >= {"customers", "equipment", "routing", "mpls", "alarms"}


def test_customer_service_path():
    _store, _user, root = _root()
    found = resolve(root, [], "/customers/12/vprn/100")
    assert found is not None
    path, node = found
    assert node.kind == "service"
    assert "sites" in node.children
    assert "saps" in node.children
    assert pwd(path) == "/customers/12/vprn/100"


def test_cd_and_pwd():
    _store, _user, root = _root()
    found = resolve(root, [], "equipment")
    assert found is not None
    path, node = found
    assert pwd(path) == "/equipment"
    assert "METRO-BA" in node.children


def test_absolute_and_parent():
    _store, _user, root = _root()
    found = resolve(root, [], "/equipment/METRO-BA/PE-BAIRES-01")
    assert found is not None
    path, node = found
    assert node.kind == "ne"
    up = resolve(root, path, "..")
    assert up is not None
    assert up[0] == ["equipment", "METRO-BA"]


def test_span_hides_core_from_noc():
    store = Store()
    noc = store.users["noc"]
    root = build_tree(store, noc)
    found = resolve(root, [], "/equipment")
    assert found is not None
    groups = set(found[1].children)
    assert "METRO-BA" in groups
    assert "CORE" not in groups
