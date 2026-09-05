import pytest

from nsp_grok.app import build_ctx
from nsp_grok.commands import dispatch
from nsp_grok.lab import Store
from nsp_grok.nsp_api import NspApiError, UserCancelled


def _admin_ctx():
    store = Store()
    return build_ctx(store, store.users["admin"])


def _viewer_ctx():
    store = Store()
    return build_ctx(store, store.users["viewer"])


def test_ls_root():
    ctx = _admin_ctx()
    out = dispatch(ctx, "ls /")
    assert out.error == ""
    assert out.renderable is not None


def test_customer_to_service():
    ctx = _admin_ctx()
    out = dispatch(ctx, "/customers")
    assert out.error == ""
    out = dispatch(ctx, "customer 12")
    assert out.error == ""
    assert ctx.cwd == ["customers", "12"]
    out = dispatch(ctx, "cd vprn/100")
    assert out.error == ""
    out = dispatch(ctx, "show")
    assert out.error == ""
    out = dispatch(ctx, "ls sites")
    assert out.error == ""


def test_cd_show_ne():
    ctx = _admin_ctx()
    dispatch(ctx, "cd /equipment/METRO-BA/PE-BAIRES-01")
    out = dispatch(ctx, "show")
    assert out.error == ""


def test_mpls_lsp_list():
    ctx = _admin_ctx()
    out = dispatch(ctx, "/mpls lsps")
    assert out.error == ""


def test_create_and_shutdown_lsp():
    ctx = _admin_ctx()
    out = dispatch(
        ctx,
        "mpls lsp create name=lsp-test from=PE-BAIRES-01 to=PE-CORDOBA-01 type=dynamic sig=rsvp",
    )
    assert out.error == ""
    assert "lsp-test" in ctx.store.lsps
    out = dispatch(ctx, "mpls lsp shutdown lsp-test")
    assert ctx.store.lsps["lsp-test"].admin == "down"


def test_viewer_cannot_create_lsp():
    ctx = _viewer_ctx()
    out = dispatch(
        ctx,
        "mpls lsp create name=lsp-x from=PE-BAIRES-01 to=PE-CORDOBA-01",
    )
    assert "permiso denegado" in out.error


def test_alarm_ack():
    ctx = _admin_ctx()
    out = dispatch(ctx, "alarm ack A-1001")
    assert out.error == ""
    alarm = next(a for a in ctx.store.alarms if a.id == "A-1001")
    assert alarm.acked
    assert alarm.acked_by == "admin"


def test_unknown_command():
    ctx = _admin_ctx()
    out = dispatch(ctx, "blargh")
    assert "comando desconocido" in out.error


def test_find_baires():
    ctx = _admin_ctx()
    out = dispatch(ctx, "find BAIRES")
    assert out.error == ""


def test_fire_walk_customers():
    ctx = _admin_ctx()
    assert ctx.cwd == []
    out = dispatch(ctx, "customers 12 vprn 100")
    assert out.error == ""
    assert ctx.cwd == ["customers", "12", "vprn", "100"]
    out = dispatch(ctx, "exit")
    assert ctx.cwd == ["customers", "12", "vprn"]
    out = dispatch(ctx, "exit all")
    assert ctx.cwd == []
    assert out.quit is False


def test_exit_at_root_logs_out():
    ctx = _admin_ctx()
    out = dispatch(ctx, "exit")
    assert out.quit is True


def test_debug_toggle():
    ctx = _admin_ctx()
    assert ctx.debug is False
    dispatch(ctx, "debug on")
    assert ctx.debug is True
    dispatch(ctx, "debug off")
    assert ctx.debug is False


class _BoomClient:
    def load_cpaa(self):
        return []

    def load_igp_domains(self):
        return []

    def load_bgp_ases(self):
        return []

    def load_customers(self):
        raise NspApiError("timeout de 60s al consultar https://172.24.80.28/nfmpv3service/api/v3/find")


class _CancelClient:
    def load_cpaa(self):
        return []

    def load_igp_domains(self):
        return []

    def load_bgp_ases(self):
        return []

    def load_customers(self):
        raise UserCancelled("Cancelado con Ctrl-C.")


class _UnexpectedClient:
    def load_cpaa(self):
        return []

    def load_igp_domains(self):
        return []

    def load_bgp_ases(self):
        return []

    def load_customers(self):
        raise RuntimeError("socket exploded")


def test_live_customer_api_error_quits():
    ctx = _admin_ctx()
    ctx.live = True
    ctx.client = _BoomClient()
    out = dispatch(ctx, "customers")
    assert out.quit is True
    assert "timeout" in out.error


def test_live_customer_ctrl_c_raises():
    ctx = _admin_ctx()
    ctx.live = True
    ctx.client = _CancelClient()
    with pytest.raises(UserCancelled, match="Ctrl-C"):
        dispatch(ctx, "customers")


def test_live_customer_unexpected_quits():
    ctx = _admin_ctx()
    ctx.live = True
    ctx.client = _UnexpectedClient()
    out = dispatch(ctx, "/customers")
    assert out.quit is True
    assert "RuntimeError" in out.error
    assert "socket exploded" in out.error


def test_help_is_spanish():
    ctx = _admin_ctx()
    out = dispatch(ctx, "help")
    assert out.error == ""
    from io import StringIO
    from rich.console import Console

    buf = StringIO()
    Console(file=buf, width=120, color_system=None).print(out.renderable)
    text = buf.getvalue()
    assert "En cualquier contexto" in text
    assert "Comandos con /" in text
    assert "serviceId" in text
    assert "esta ayuda" in text


def test_unknown_command_does_not_quit():
    ctx = _admin_ctx()
    out = dispatch(ctx, "blargh")
    assert out.quit is False
    assert "comando desconocido" in out.error
