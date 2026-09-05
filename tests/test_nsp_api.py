import pytest

from nsp_grok.nsp_api import (
    NspApiError,
    _rt_matches_service,
    _saps_from_rows,
    _service_from_row,
    _static_from_row,
    _vr_cidr,
    build_find_body,
    format_request,
    parse_find_xml,
    redact_headers,
)
from nsp_grok.models import AccessInterface, Service, ServiceSite


def test_redact_authorization():
    headers = redact_headers({"Authorization": "Bearer super-secret", "Content-Type": "application/json"})
    assert headers["Authorization"] == "Bearer ***"
    assert "super-secret" not in headers["Authorization"]


def test_format_request_hides_token():
    text = format_request(
        "POST",
        "https://172.24.80.28/rest-gateway/rest/api/v1/auth/token",
        {"Authorization": "Basic abcdef"},
        {"grant_type": "client_credentials"},
    )
    assert ">>> POST https://172.24.80.28/rest-gateway/rest/api/v1/auth/token" in text
    assert "Basic ***" in text
    assert "abcdef" not in text
    assert "client_credentials" in text


def test_parse_find_subscribers():
    xml = """<?xml version="1.0"?>
<findResponse xmlns="xmlapi_1.0">
  <result>
    <subscr.Subscriber>
      <objectFullName>subscriber:12</objectFullName>
      <subscriberId>12</subscriberId>
      <displayedName>Banco Nación</displayedName>
    </subscr.Subscriber>
  </result>
</findResponse>
"""
    rows = parse_find_xml(xml)
    assert len(rows) == 1
    assert rows[0]["subscriberId"] == "12"
    assert rows[0]["displayedName"] == "Banco Nación"


def test_parse_find_xml_exception():
    xml = """<?xml version="1.0"?>
<findResponse xmlns="xmlapi_1.0">
  <XMLException>
    <description>class not found</description>
  </XMLException>
</findResponse>
"""
    with pytest.raises(NspApiError, match="class not found"):
        parse_find_xml(xml)


def test_parse_find_invalid_xml():
    with pytest.raises(NspApiError, match="XML de find inválido"):
        parse_find_xml("<not-xml")


def test_service_keeps_id_and_service_id_apart():
    svc = _service_from_row(
        {
            "id": "1",
            "serviceId": "10",
            "objectFullName": "svc-mgr:service-1",
            "displayedName": "VPRN 10",
            "subscriberPointer": "subscriber:10",
            "administrativeState": "serviceUp",
            "operationalState": "serviceUp",
        },
        "vprn",
        10,
    )
    assert svc is not None
    assert svc.svc_id == 10
    assert svc.mgr_id == 1
    assert svc.fdn == "svc-mgr:service-1"
    site = ServiceSite(svc_id=svc.svc_id, site_id="10.251.121.250", ne="7705", mgr_id=svc.mgr_id)
    sap = AccessInterface(
        svc_id=svc.svc_id,
        site_id="10.251.121.250",
        name="I-OPE-Pinar",
        port="dc3/port-1",
        layer="l3",
        mgr_id=svc.mgr_id,
    )
    assert site.fdn == "svc-mgr:service-1:10.251.121.250"
    assert sap.fdn.startswith("svc-mgr:service-1:10.251.121.250:")


def test_service_id_from_fdn_when_attributes_missing():
    svc = _service_from_row(
        {"objectFullName": "svc-mgr:service-8", "displayedName": "VPRN 110"},
        "vprn",
        110,
    )
    assert svc is not None
    assert svc.mgr_id == 8
    assert svc.svc_id == 8
    assert svc.fdn == "svc-mgr:service-8"


def test_service_id_without_mgr_id_uses_service_id_for_fdn():
    svc = _service_from_row({"serviceId": "10", "displayedName": "VPRN 10"}, "vprn", 10)
    assert svc is not None
    assert svc.svc_id == 10
    assert svc.mgr_id == 10
    assert svc.fdn == "svc-mgr:service-10"


def test_lab_service_mgr_id_defaults_to_svc_id():
    svc = Service(100, "vprn-banco-nacion", "vprn", "Banco Nación", 12, [])
    assert svc.svc_id == 100
    assert svc.mgr_id == 100
    assert svc.fdn == "svc-mgr:service-100"


def test_find_body_omits_attribute_when_unset():
    body = build_find_body("rtr.VirtualRouterIpAddress")
    assert body == {
        "find": {
            "fullClassName": "rtr.VirtualRouterIpAddress",
            "resultFilter": {"children": ""},
        }
    }


def test_find_body_query6_l3_sap():
    body = build_find_body(
        "vprn.L3AccessInterface",
        [
            "objectFullName",
            "displayedName",
            "siteId",
            "portPointer",
            "primaryIPv4Address",
            "administrativeState",
            "operationalState",
        ],
        {
            "wildcard": {
                "name": "objectFullName",
                "value": "svc-mgr:service-1:10.251.121.250%",
            }
        },
    )
    assert body["find"]["fullClassName"] == "vprn.L3AccessInterface"
    assert body["find"]["resultFilter"]["children"] == ""
    assert "portPointer" in body["find"]["resultFilter"]["attribute"]
    assert body["find"]["filter"]["wildcard"]["value"] == "svc-mgr:service-1:10.251.121.250%"


def test_find_body_query7_vr_address():
    body = build_find_body(
        "rtr.VirtualRouterIpAddress",
        None,
        {
            "wildcard": {
                "name": "objectFullName",
                "value": "svc-mgr:service-1:10.251.121.250:%",
            }
        },
    )
    assert "attribute" not in body["find"]["resultFilter"]
    assert body["find"]["filter"]["wildcard"]["value"].endswith(":%")


def test_find_body_query8_static_route():
    body = build_find_body(
        "rtr.StaticRoute",
        None,
        {
            "wildcard": {
                "name": "objectFullName",
                "value": "network:10.251.121.250:vprn-10:%",
            }
        },
    )
    assert body["find"]["fullClassName"] == "rtr.StaticRoute"
    assert body["find"]["filter"]["wildcard"]["value"] == "network:10.251.121.250:vprn-10:%"
    assert "attribute" not in body["find"]["resultFilter"]


def test_find_body_query9_bgp_site():
    body = build_find_body(
        "bgp.Site",
        ["objectFullName", "displayedName", "administrativeState", "operationalState"],
        {
            "wildcard": {
                "name": "objectFullName",
                "value": "network:10.251.121.250:vprn-10%",
            }
        },
    )
    assert body["find"]["filter"]["wildcard"]["value"] == "network:10.251.121.250:vprn-10%"
    assert not body["find"]["filter"]["wildcard"]["value"].endswith(":%")


def test_find_body_query15_rt():
    body = build_find_body(
        "topology.BgpRoutesRouteTarget",
        ["objectFullName", "routeTargetString", "format", "numNextHops", "asNumber"],
        {"equal": {"name": "routeTargetString", "value": "65000:10"}},
    )
    assert body["find"]["fullClassName"] == "topology.BgpRoutesRouteTarget"
    assert body["find"]["filter"]["equal"]["value"] == "65000:10"
    assert body["find"]["resultFilter"]["children"] == ""


def test_vr_cidr_appends_prefix_length():
    assert _vr_cidr({"ipAddress": "12.5.196.1", "prefixLength": "30"}) == "12.5.196.1/30"
    assert _vr_cidr({"address": "10.10.121.1/30"}) == "10.10.121.1/30"
    assert _vr_cidr({}) == ""


def test_sap_uses_port_pointer():
    svc = Service(10, "VPRN 10", "vprn", "Red_Ope", 10, [], mgr_id=1)
    saps = _saps_from_rows(
        svc,
        [
            {
                "objectFullName": "svc-mgr:service-1:10.251.121.250:ip-if-4",
                "displayedName": "I-OPE-Pinar",
                "siteId": "10.251.121.250",
                "portPointer": "network:10.251.121.250:lag-1",
                "primaryIPv4Address": "12.5.196.1",
                "administrativeState": "up",
                "operationalState": "up",
            }
        ],
    )
    assert saps[0].name == "I-OPE-Pinar"
    assert saps[0].port == "lag-1"
    assert saps[0].primary_ipv4 == "12.5.196.1"
    assert saps[0].svc_id == 10
    assert saps[0].mgr_id == 1


def test_static_from_row_network_fdn():
    svc = Service(10, "VPRN 10", "vprn", "Red_Ope", 10, [], mgr_id=1)
    sr = _static_from_row(
        {
            "objectFullName": "network:10.251.121.250:vprn-10:10.50.0.0-16",
            "destPrefix": "10.50.0.0/16",
            "nextHop": "10.10.121.2",
            "administrativeState": "up",
        },
        svc,
        "10.251.121.250",
    )
    assert sr is not None
    assert sr.prefix == "10.50.0.0/16"
    assert sr.next_hop == "10.10.121.2"
    assert sr.svc_id == 10
    assert sr.site_id == "10.251.121.250"


def test_rt_match_does_not_confuse_10_and_110():
    svc10 = Service(10, "VPRN 10", "vprn", "Red_Ope", 10, [], mgr_id=1)
    svc110 = Service(110, "VPRN 110", "vprn", "X", 110, [], mgr_id=8)
    assert _rt_matches_service("65000:10", svc10)
    assert not _rt_matches_service("65000:110", svc10)
    assert _rt_matches_service("65000:110", svc110)
    assert not _rt_matches_service("65000:10", svc110)
