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
        "mpls lsp create name=lsp-test from=PE-BAIRES-01 to=PE-CORDOBA-01 type=dynamic sig=rsvp confirm=yes",
    )
    assert out.error == ""
    assert "lsp-test" in ctx.store.lsps
    out = dispatch(ctx, "mpls lsp shutdown lsp-test confirm=yes")
    assert ctx.store.lsps["lsp-test"].admin == "down"


def test_viewer_cannot_cpaa_record():
    ctx = _viewer_ctx()
    ctx.live = True
    out = dispatch(ctx, "cpaa record bgp")
    assert "permiso denegado" in out.error


def test_cpaa_record_requires_live():
    ctx = _admin_ctx()
    out = dispatch(ctx, "cpaa record bgp")
    assert "en vivo" in out.error


def test_viewer_cannot_create_lsp():
    ctx = _viewer_ctx()
    out = dispatch(
        ctx,
        "mpls lsp create name=lsp-x from=PE-BAIRES-01 to=PE-CORDOBA-01",
    )
    assert "permiso denegado" in out.error


class _LiveMplsClient:
    def __init__(self) -> None:
        self.created: list[tuple[str, str, str, str, str]] = []
        self.admin: list[tuple[str, str, str]] = []
        self.deleted: list[str] = []

    def load_network_elements(self):
        return {}

    def load_mpls_inventory(self, nes):
        return [], [], []

    def create_lsp(self, name, source_ip, dest_ip, lsp_type="dynamic", path_id=""):
        self.created.append((name, source_ip, dest_ip, lsp_type, path_id))
        return name

    def configure_lsp_admin(self, fdn, admin, class_name=""):
        self.admin.append((fdn, admin, class_name))
        return fdn

    def delete_lsp(self, fdn):
        self.deleted.append(fdn)
        return fdn


def test_live_lsp_create_posts_to_nsp():
    ctx = _admin_ctx()
    ctx.live = True
    client = _LiveMplsClient()
    ctx.client = client
    out = dispatch(
        ctx,
        "mpls lsp create name=lsp-live from=PE-BAIRES-01 to=PE-CORDOBA-01 type=dynamic confirm=yes",
    )
    assert out.error == ""
    assert client.created == [
        ("lsp-live", "10.10.1.1", "10.10.2.1", "dynamic", "")
    ]
    assert "lsp-live" in ctx.store.lsps


def test_live_lsp_shutdown_needs_fdn():
    ctx = _admin_ctx()
    ctx.live = True
    client = _LiveMplsClient()
    ctx.client = client
    out = dispatch(ctx, "mpls lsp shutdown lsp-ba-cba")
    assert "FDN" in out.error
    assert client.admin == []


def test_live_lsp_shutdown_posts_configure_instance():
    ctx = _admin_ctx()
    ctx.live = True
    client = _LiveMplsClient()
    ctx.client = client
    lsp = ctx.store.lsps["lsp-ba-cba"]
    lsp.fdn = "lsp:from-10.10.1.1-id-1"
    lsp.class_name = "mpls.DynamicLsp"
    out = dispatch(ctx, "mpls lsp shutdown lsp-ba-cba confirm=yes")
    assert out.error == ""
    assert client.admin == [("lsp:from-10.10.1.1-id-1", "down", "mpls.DynamicLsp")]
    assert ctx.store.lsps["lsp-ba-cba"].admin == "down"


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
    assert "Create SAP" in text
    assert "svc-mgr:service-<id>:<siteId>" in text
    assert "site = servicio × NE" in text


def test_help_sap_shows_hierarchy():
    ctx = _admin_ctx()
    out = dispatch(ctx, "help sap")
    assert out.error == ""
    from io import StringIO
    from rich.console import Console

    buf = StringIO()
    Console(file=buf, width=120, color_system=None).print(out.renderable)
    text = buf.getvalue()
    assert "netw.NetworkElement" in text
    assert "L3/L2AccessInterface" in text
    assert "portPointer" in text
    assert "system IP" in text
    out = dispatch(ctx, "sap create")
    buf = StringIO()
    Console(file=buf, width=120, color_system=None).print(out.renderable)
    assert "vprn.Site" in buf.getvalue()


def test_unknown_command_does_not_quit():
    ctx = _admin_ctx()
    out = dispatch(ctx, "blargh")
    assert out.quit is False
    assert "comando desconocido" in out.error


def test_create_requires_confirm():
    ctx = _admin_ctx()
    out = dispatch(
        ctx,
        "service create type=vprn id=201 customer=12 name=vpn-test",
    )
    assert "confirmación" in out.error
    assert 201 not in ctx.store.services


def test_create_cancelled_with_confirm_no():
    ctx = _admin_ctx()
    out = dispatch(
        ctx,
        "service create type=vprn id=201 customer=12 name=vpn-test confirm=no",
    )
    assert out.error == "cancelado"
    assert 201 not in ctx.store.services


def test_create_service_lab_with_confirm_yes():
    ctx = _admin_ctx()
    out = dispatch(
        ctx,
        "service create type=vprn id=201 customer=12 name=vpn-test sites=PE-BAIRES-01 confirm=yes",
    )
    assert out.error == ""
    svc = ctx.store.services[201]
    assert svc.svc_type == "vprn"
    assert svc.customer_id == 12
    assert svc.name == "vpn-test"
    assert "PE-BAIRES-01" in svc.sites
    sites = [s for s in ctx.store.sites if s.svc_id == 201]
    assert sites[0].site_id == "10.10.1.1"


def test_create_service_uses_cwd_customer():
    ctx = _admin_ctx()
    dispatch(ctx, "customers 12")
    out = dispatch(ctx, "service create type=vpls id=202 name=elan-test confirm=yes")
    assert out.error == ""
    assert ctx.store.services[202].customer_id == 12
    assert ctx.store.services[202].svc_type == "vpls"
    out = dispatch(ctx, "create type=epipe id=203 name=eline-cwd confirm=yes")
    assert out.error == ""
    assert ctx.store.services[203].customer_id == 12
    assert ctx.store.services[203].svc_type == "epipe"


def test_service_shutdown_and_delete_need_confirm():
    ctx = _admin_ctx()
    out = dispatch(ctx, "service shutdown 100")
    assert "confirmación" in out.error
    assert ctx.store.services[100].admin == "up"
    out = dispatch(ctx, "service shutdown 100 confirm=yes")
    assert out.error == ""
    assert ctx.store.services[100].admin == "down"
    out = dispatch(ctx, "service delete 100 confirm=no")
    assert out.error == "cancelado"
    assert 100 in ctx.store.services
    out = dispatch(ctx, "service delete 100 confirm=yes")
    assert out.error == ""
    assert 100 not in ctx.store.services


def test_confirm_callback_yes():
    ctx = _admin_ctx()
    asked: list[str] = []

    def _ask(msg: str) -> bool:
        asked.append(msg)
        return True

    ctx.confirm = _ask
    out = dispatch(ctx, "mpls lsp shutdown lsp-ba-cba")
    assert out.error == ""
    assert asked and "shutdown" in asked[0]
    assert ctx.store.lsps["lsp-ba-cba"].admin == "down"


def test_alarm_clear_needs_confirm():
    ctx = _admin_ctx()
    out = dispatch(ctx, "alarm clear A-1001")
    assert "confirmación" in out.error
    alarm = next(a for a in ctx.store.alarms if a.id == "A-1001")
    assert alarm.cleared is False
    out = dispatch(ctx, "alarm clear A-1001 confirm=yes")
    assert out.error == ""
    assert alarm.cleared is True


def test_viewer_cannot_create_service():
    ctx = _viewer_ctx()
    out = dispatch(
        ctx,
        "service create type=vprn id=201 customer=12 name=x confirm=yes",
    )
    assert "permiso denegado" in out.error


class _LiveServiceClient:
    def __init__(self) -> None:
        self.created: list[tuple] = []
        self.admin: list[tuple] = []
        self.deleted: list[str] = []

    def load_services(self, subscriber_id: int):
        return []

    def create_service(self, svc_type, subscriber_id, service_id=None, name="", description="", site_ips=None):
        self.created.append((svc_type, subscriber_id, service_id, name, tuple(site_ips or [])))

    def configure_service_admin(self, fdn, svc_type, admin):
        self.admin.append((fdn, svc_type, admin))
        return fdn

    def delete_service(self, fdn):
        self.deleted.append(fdn)
        return fdn


def test_live_service_create_posts_to_nsp():
    ctx = _admin_ctx()
    ctx.live = True
    client = _LiveServiceClient()
    ctx.client = client
    out = dispatch(
        ctx,
        "service create type=epipe id=310 customer=33 name=eline-x sites=PE-BAIRES-01,PE-ROSARIO-01 confirm=yes",
    )
    assert out.error == ""
    assert client.created == [
        ("epipe", 33, 310, "eline-x", ("10.10.1.1", "10.10.3.1"))
    ]
    assert ctx.store.services[310].svc_type == "epipe"


def test_sap_create_requires_confirm():
    ctx = _admin_ctx()
    out = dispatch(
        ctx,
        "sap create service=100 site=PE-BAIRES-01 port=1/1/11 vlan=101 ip=10.1.12.9/30",
    )
    assert "confirmación" in out.error


def test_sap_create_lab():
    ctx = _admin_ctx()
    out = dispatch(
        ctx,
        "sap create service=100 site=PE-BAIRES-01 port=1/1/11 vlan=101 ip=10.1.12.9/30 confirm=yes",
    )
    assert out.error == ""
    sap = next(
        s for s in ctx.store.saps if s.svc_id == 100 and s.name == "1/1/11:101"
    )
    assert sap.site_id == "10.10.1.1"
    assert sap.port == "1/1/11"
    assert sap.outer_tag == 101
    assert sap.primary_ipv4 == "10.1.12.9/30"
    assert sap.layer == "l3"


def test_sap_create_vpls_from_cwd():
    ctx = _admin_ctx()
    dispatch(ctx, "customers 20 vpls 200")
    out = dispatch(
        ctx,
        "sap create site=PE-BAIRES-02 port=1/1/3 vlan=201 confirm=yes",
    )
    assert out.error == ""
    sap = next(s for s in ctx.store.saps if s.svc_id == 200 and s.name == "1/1/3:201")
    assert sap.layer == "l2"
    assert sap.site_id == "10.10.1.2"


def test_sap_create_vprn_requires_ip():
    ctx = _admin_ctx()
    out = dispatch(
        ctx,
        "sap create service=100 site=PE-BAIRES-01 port=1/1/11 vlan=101 confirm=yes",
    )
    assert "ip=" in out.error


def test_sap_shutdown_and_delete():
    ctx = _admin_ctx()
    dispatch(
        ctx,
        "sap create service=100 site=PE-BAIRES-01 port=1/1/11 vlan=101 ip=10.1.12.9/30 confirm=yes",
    )
    out = dispatch(ctx, "sap shutdown 1/1/11:101")
    assert "confirmación" in out.error
    out = dispatch(ctx, "sap shutdown 1/1/11:101 confirm=yes")
    assert out.error == ""
    sap = next(s for s in ctx.store.saps if s.name == "1/1/11:101" and s.svc_id == 100)
    assert sap.admin == "down"
    out = dispatch(ctx, "sap delete 1/1/11:101 confirm=yes")
    assert out.error == ""
    assert not any(s.name == "1/1/11:101" for s in ctx.store.saps)


def test_viewer_cannot_create_sap():
    ctx = _viewer_ctx()
    out = dispatch(
        ctx,
        "sap create service=100 site=PE-BAIRES-01 port=1/1/11 vlan=101 ip=10.1.1.1/30 confirm=yes",
    )
    assert "permiso denegado" in out.error


class _LiveSapClient:
    def __init__(self) -> None:
        self.sites: list[tuple] = []
        self.saps: list[tuple] = []

    def load_sites(self, svc):
        return []

    def load_saps(self, svc, sites=None):
        return []

    def load_sdp_bindings(self, svc):
        return []

    def create_site(self, svc_fdn, svc_type, site_ip):
        self.sites.append((svc_fdn, svc_type, site_ip))
        return f"{svc_fdn}:{site_ip}"

    def create_sap(self, svc_type, site_fdn, port_pointer, outer=0, inner=0, ip_cidr="", name=""):
        self.saps.append((svc_type, site_fdn, port_pointer, outer, ip_cidr, name))

    def find_port_fdn(self, site_ip, port):
        return f"network:{site_ip}:shelf-1:cardSlot-1:card:port-{port.rsplit('/', 1)[-1]}"


def test_live_sap_create_posts_to_nsp():
    ctx = _admin_ctx()
    ctx.live = True
    client = _LiveSapClient()
    ctx.client = client
    out = dispatch(
        ctx,
        "sap create service=300 site=PE-BAIRES-01 port=1/1/4 vlan=301 confirm=yes",
    )
    assert out.error == ""
    assert client.saps
    assert client.saps[0][0] == "epipe"
    assert client.saps[0][1].endswith(":10.10.1.1")
    assert "port-4" in client.saps[0][2]
    assert client.saps[0][3] == 301


def test_sdp_create_requires_confirm():
    ctx = _admin_ctx()
    out = dispatch(
        ctx,
        "sdp create service=100 site=PE-BAIRES-01 far=PE-CORDOBA-01 sdp=109 vc=100 type=spoke",
    )
    assert "confirmación" in out.error


def test_sdp_create_lab():
    ctx = _admin_ctx()
    out = dispatch(
        ctx,
        "sdp create service=100 site=PE-BAIRES-01 far=PE-CORDOBA-01 sdp=109 vc=100 type=spoke confirm=yes",
    )
    assert out.error == ""
    b = next(x for x in ctx.store.bindings if x.sdp_id == 109 and x.svc_id == 100)
    assert b.binding_type == "spoke"
    assert b.site_id == "10.10.1.1"
    assert b.far_end == "10.10.2.1"
    assert b.vc_id == 100


def test_sdp_create_vpls_defaults_mesh():
    ctx = _admin_ctx()
    dispatch(ctx, "customers 20 vpls 200")
    out = dispatch(
        ctx,
        "sdp create site=PE-BAIRES-01 far=PE-BAIRES-02 sdp=208 confirm=yes",
    )
    assert out.error == ""
    b = next(x for x in ctx.store.bindings if x.sdp_id == 208)
    assert b.binding_type == "mesh"


def test_sdp_shutdown_and_delete():
    ctx = _admin_ctx()
    dispatch(
        ctx,
        "sdp create service=300 site=PE-BAIRES-01 far=PE-ROSARIO-01 sdp=219 vc=300 type=spoke confirm=yes",
    )
    out = dispatch(ctx, "sdp shutdown 219")
    assert "confirmación" in out.error
    out = dispatch(ctx, "sdp shutdown 219 confirm=yes")
    assert out.error == ""
    b = next(x for x in ctx.store.bindings if x.sdp_id == 219)
    assert b.admin == "down"
    out = dispatch(ctx, "sdp delete 219 confirm=yes")
    assert out.error == ""
    assert not any(x.sdp_id == 219 for x in ctx.store.bindings)


def test_help_sdp_shows_hierarchy():
    ctx = _admin_ctx()
    out = dispatch(ctx, "help sdp")
    assert out.error == ""
    from io import StringIO
    from rich.console import Console

    buf = StringIO()
    Console(file=buf, width=120, color_system=None).print(out.renderable)
    text = buf.getvalue()
    assert "SpokeSdpBinding" in text
    assert "tunnelSelectionTerminationSiteId" in text
    out = dispatch(ctx, "sdp create")
    buf = StringIO()
    Console(file=buf, width=120, color_system=None).print(out.renderable)
    assert "far-end" in buf.getvalue().lower() or "far-end" in buf.getvalue()


class _LiveSdpClient:
    def __init__(self) -> None:
        self.created: list[tuple] = []
        self.sites: list[tuple] = []

    def load_sites(self, svc):
        return []

    def load_saps(self, svc, sites=None):
        return []

    def load_sdp_bindings(self, svc):
        return []

    def create_site(self, svc_fdn, svc_type, site_ip):
        self.sites.append((svc_fdn, svc_type, site_ip))
        return f"{svc_fdn}:{site_ip}"

    def create_sdp_binding(self, site_fdn, far_end_ip, binding_type="spoke", sdp_id=None, vc_id=None):
        self.created.append((site_fdn, far_end_ip, binding_type, sdp_id, vc_id))


def test_live_sdp_create_posts_to_nsp():
    ctx = _admin_ctx()
    ctx.live = True
    client = _LiveSdpClient()
    ctx.client = client
    out = dispatch(
        ctx,
        "sdp create service=300 site=PE-BAIRES-01 far=PE-ROSARIO-01 sdp=201 vc=300 type=spoke confirm=yes",
    )
    assert out.error == ""
    assert client.created
    assert client.created[0][1] == "10.10.3.1"
    assert client.created[0][2] == "spoke"
    assert client.created[0][3] == 201


class _LiveAlarmClient:
    def __init__(self) -> None:
        self.acked: list[str] = []
        self.cleared: list[str] = []

    def load_network_elements(self):
        return {}

    def load_alarms(self, nes):
        return []

    def acknowledge_alarm(self, fdn):
        self.acked.append(fdn)
        return fdn

    def clear_alarm(self, fdn):
        self.cleared.append(fdn)
        return fdn


def test_live_alarm_ack_and_clear():
    ctx = _admin_ctx()
    ctx.live = True
    client = _LiveAlarmClient()
    ctx.client = client
    alarm = next(a for a in ctx.store.alarms if a.id == "A-1001")
    alarm.object_fdn = "faultManager:network@10.10.1.1|alarm-10"
    out = dispatch(ctx, "alarm ack A-1001")
    assert out.error == ""
    assert client.acked == ["faultManager:network@10.10.1.1|alarm-10"]
    alarm = next(a for a in ctx.store.alarms if a.id == "A-1001")
    alarm.object_fdn = "faultManager:network@10.10.1.1|alarm-10"
    out = dispatch(ctx, "alarm clear A-1001 confirm=yes")
    assert out.error == ""
    assert client.cleared == ["faultManager:network@10.10.1.1|alarm-10"]


def test_live_alarm_ack_needs_fdn():
    ctx = _admin_ctx()
    ctx.live = True
    client = _LiveAlarmClient()
    ctx.client = client
    out = dispatch(ctx, "alarm ack A-1001")
    assert "FDN" in out.error
    assert client.acked == []
