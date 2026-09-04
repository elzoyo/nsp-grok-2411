from nsp_grok.auth import (
    authenticate,
    can,
    check_password_policy,
    hash_password,
    in_span,
    verify_password,
)
from nsp_grok.lab import Store


def test_default_users_login():
    store = Store()
    user, err = authenticate(store.users, "admin", "Nokia1234!")
    assert err == ""
    assert user is not None
    assert user.role == "administrator"


def test_username_is_case_insensitive():
    store = Store()
    user, err = authenticate(store.users, "ADMIN", "Nokia1234!")
    assert user is not None
    assert err == ""


def test_bad_password_counts_down():
    store = Store()
    _, err = authenticate(store.users, "viewer", "wrong")
    assert "intento" in err
    assert store.users["viewer"].failed_logins == 1


def test_lockout_after_five_failures():
    store = Store()
    for _ in range(5):
        _, err = authenticate(store.users, "viewer", "nope")
    assert "bloqueada" in err.lower()
    _, err = authenticate(store.users, "viewer", "Nokia1234!")
    assert "bloqueada" in err.lower()


def test_password_policy():
    assert check_password_policy("admin", "short")
    assert check_password_policy("admin", "nouppercase1!")
    assert not check_password_policy("admin", "Nokia1234!")


def test_hash_roundtrip():
    digest, salt = hash_password("Nokia1234!")
    from nsp_grok.models import User

    u = User("x", digest, salt, "g", "r", "X")
    assert verify_password(u, "Nokia1234!")
    assert not verify_password(u, "nope")


def test_span_and_access():
    store = Store()
    noc = store.users["noc"]
    admin = store.users["admin"]
    viewer = store.users["viewer"]
    assert in_span(noc, "METRO-BA", "PE-BAIRES-01")
    assert not in_span(noc, "CORE", "P-CORE-01")
    assert in_span(admin, "CORE", "P-CORE-01")
    assert can(admin, "execute")
    assert can(viewer, "read")
    assert not can(viewer, "write")
