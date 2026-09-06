import pytest

from nsp_grok.nsp_api import (
    NspApiError,
    build_cpaa_record_xml,
    raise_if_xml_fault,
    _alarm_from_row,
    _binding_from_row,
    _cpaa_from_row,
    _lsp_from_row,
    _mac_from_row,
    _next_hop_from_row,
    _rib_from_row,
    _rt_fdn_wildcards_for_rd,
    _rt_matches_service,
    _rt_token,
    _saps_from_rows,
    _service_from_row,
    _static_from_row,
    _tunnel_from_row,
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
    assert saps[0].port_pointer == "network:10.251.121.250:lag-1"
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


def test_find_body_query16_next_hop():
    body = build_find_body(
        "topology.BgpRoutesNextHop",
        [
            "objectFullName",
            "nextHop",
            "nextHopAddrType",
            "routeTargetString",
            "siteId",
        ],
        {"equal": {"name": "routeTargetString", "value": "65000:10"}},
    )
    assert body["find"]["fullClassName"] == "topology.BgpRoutesNextHop"
    assert body["find"]["filter"]["equal"]["value"] == "65000:10"
    assert body["find"]["resultFilter"]["children"] == ""
    assert "nextHop" in body["find"]["resultFilter"]["attribute"]
    assert "attribute" in body["find"]["resultFilter"]


def test_next_hop_ignores_null_and_keeps_pe_ip():
    svc = Service(10, "VPRN 10", "vprn", "Red_Ope", 10, [], mgr_id=1)
    assert (
        _next_hop_from_row(
            {"nextHop": "0.0.0.0", "routeTargetString": "65000:10"}, svc, "65000:10"
        )
        is None
    )
    nh = _next_hop_from_row(
        {
            "objectFullName": "tpgy-mgr:AS-65000:RT-65000%10:NH-10.251.121.250-Type-ipv4",
            "nextHop": "10.251.121.250",
            "nextHopAddrType": "ipv4",
            "routeTargetString": "65000:10",
            "siteId": "10.251.243.250",
        },
        svc,
        "65000:10",
    )
    assert nh is not None
    assert nh.next_hop == "10.251.121.250"
    assert nh.route_target == "65000:10"
    assert nh.svc_id == 10
    assert nh.cpaa_site_id == "10.251.243.250"


def test_find_body_sdp_binding_wildcard():
    body = build_find_body(
        "vprn.SdpBinding",
        None,
        {"wildcard": {"name": "objectFullName", "value": "svc-mgr:service-1:%"}},
    )
    assert body["find"]["fullClassName"] == "vprn.SdpBinding"
    assert body["find"]["resultFilter"] == {"children": ""}
    assert body["find"]["filter"]["wildcard"]["value"] == "svc-mgr:service-1:%"


def test_binding_from_row_parses_sdp_and_site():
    svc = Service(10, "VPRN 10", "vprn", "Red_Ope", 10, [], mgr_id=1)
    b = _binding_from_row(
        {
            "objectFullName": "svc-mgr:service-1:10.251.121.250:sdp-101",
            "siteId": "10.251.121.250",
            "sdpId": "101",
            "vcId": "10",
            "type": "spoke",
            "administrativeState": "up",
            "operationalState": "up",
        },
        svc,
    )
    assert b is not None
    assert b.sdp_id == 101
    assert b.vc_id == 10
    assert b.site_id == "10.251.121.250"
    assert b.mgr_id == 1
    assert b.fdn == "svc-mgr:service-1:10.251.121.250:sdp-101"


def test_find_body_svt_tunnel_by_id():
    body = build_find_body(
        "svt.Tunnel",
        None,
        {"equal": {"name": "id", "value": "101"}},
    )
    assert body["find"]["fullClassName"] == "svt.Tunnel"
    assert body["find"]["resultFilter"] == {"children": ""}
    assert body["find"]["filter"]["equal"]["value"] == "101"


def test_find_body_alarm_wildcard_service_fdn():
    body = build_find_body(
        "fm.AlarmObject",
        None,
        {"wildcard": {"name": "objectFullName", "value": "svc-mgr:service-1%"}},
    )
    assert body["find"]["fullClassName"] == "fm.AlarmObject"
    assert body["find"]["filter"]["wildcard"]["value"] == "svc-mgr:service-1%"
    assert "*" not in body["find"]["filter"]["wildcard"]["value"]
    assert body["find"]["resultFilter"]["children"] == ""


def test_find_body_vpls_mac_wildcard():
    body = build_find_body(
        "vpls.MacRecord",
        None,
        {"wildcard": {"name": "objectFullName", "value": "svc-mgr:service-25:%"}},
    )
    assert body["find"]["fullClassName"] == "vpls.MacRecord"
    assert body["find"]["resultFilter"]["children"] == ""


def test_tunnel_from_row():
    tun = _tunnel_from_row(
        {
            "id": "101",
            "displayedName": "sdp-ba-cba",
            "farEndIpAddress": "10.10.2.1",
            "sourceSiteId": "10.10.1.1",
            "lspPointer": "network:10.10.1.1:dynamicLsp-lsp-ba-cba",
            "signaling": "tldp",
            "administrativeState": "up",
            "operationalState": "up",
        },
        101,
    )
    assert tun is not None
    assert tun.sdp_id == 101
    assert tun.far_end == "10.10.2.1"
    assert tun.lsp == "dynamicLsp-lsp-ba-cba"
    assert tun.from_ne == "10.10.1.1"


def test_lsp_from_row():
    lsp = _lsp_from_row(
        {
            "displayedName": "lsp-ba-cba",
            "fromPointer": "network:10.10.1.1",
            "toPointer": "network:10.10.2.1",
            "signaling": "rsvp",
            "type": "dynamic",
            "administrativeState": "up",
            "operationalState": "up",
        },
        "lsp-ba-cba",
    )
    assert lsp is not None
    assert lsp.name == "lsp-ba-cba"
    assert lsp.from_ne == "10.10.1.1"
    assert lsp.to_ne == "10.10.2.1"


def test_alarm_from_row_maps_severity():
    svc = Service(10, "VPRN 10", "vprn", "Red_Ope", 10, [], mgr_id=1)
    alarm = _alarm_from_row(
        {
            "objectFullName": "svc-mgr:service-1:site-x",
            "alarmId": "A-9",
            "severity": "major",
            "probableCause": "siteDown",
            "siteId": "10.251.121.250",
            "additionalText": "site down",
            "acknowledged": "false",
        },
        svc,
    )
    assert alarm is not None
    assert alarm.id == "A-9"
    assert alarm.severity == "major"
    assert alarm.ne == "10.251.121.250"
    assert "svc-mgr:service-1" in alarm.object_fdn


def test_mac_from_row():
    svc = Service(5110, "VPLS 5110", "vpls", "X", 110, [], mgr_id=25)
    mac = _mac_from_row(
        {
            "objectFullName": "svc-mgr:service-25:10.251.121.250:00:00:5e:00:53:01",
            "macAddress": "00:00:5e:00:53:01",
            "siteId": "10.251.121.250",
            "portPointer": "1/1/10:200",
            "type": "learned",
        },
        svc,
    )
    assert mac is not None
    assert mac.mac == "00:00:5e:00:53:01"
    assert mac.svc_id == 5110
    assert mac.source == "learned"


def test_find_body_query14_monitored_prefix():
    body = build_find_body(
        "topology.BgpMonitoredPrefix",
        None,
        {
            "and": {
                "equal": [
                    {"name": "prefType", "value": "vpnIpv4"},
                    {"name": "prefRD", "value": "65000:10"},
                ]
            }
        },
    )
    assert body["find"]["fullClassName"] == "topology.BgpMonitoredPrefix"
    assert body["find"]["resultFilter"] == {"children": ""}
    equals = body["find"]["filter"]["and"]["equal"]
    assert equals[0]["value"] == "vpnIpv4"
    assert equals[1]["value"] == "65000:10"


def test_find_body_stats_time_captured():
    body = build_find_body(
        "equipment.InterfaceAdditionalStatsLogRecord",
        None,
        {
            "and": {
                "equal": {
                    "name": "monitoredObjectPointer",
                    "value": "network:10.10.1.1:port-1",
                },
                "between": {
                    "name": "timeCaptured",
                    "first": "1",
                    "second": "2",
                },
            }
        },
    )
    assert body["find"]["fullClassName"] == "equipment.InterfaceAdditionalStatsLogRecord"
    assert body["find"]["resultFilter"]["children"] == ""
    assert body["find"]["filter"]["and"]["between"]["name"] == "timeCaptured"


def test_rt_fdn_uses_percent_not_colon():
    assert _rt_token("65000:10") == "RT-65000%10"
    wild = _rt_fdn_wildcards_for_rd("65000:10")
    assert "tpgy-mgr:AS-65000:RT-65000%10%" in wild
    assert all("RT-65000:10" not in w for w in wild)


def test_find_body_query10_cpaa():
    body = build_find_body(
        "topology.Cpaa",
        [
            "objectFullName",
            "displayedName",
            "administrativeState",
            "operationalState",
            "routerId",
            "asPointer",
            "bgpAsPointer",
            "protocolEventTypes",
            "protocolRecord",
            "bgpRibInfoLastRetrieveTime",
            "bgpVpnv4RoutTargetLastRetrieveTime",
        ],
    )
    assert body["find"]["fullClassName"] == "topology.Cpaa"
    assert body["find"]["resultFilter"]["children"] == ""
    assert "filter" not in body["find"]
    assert "bgpRibInfoLastRetrieveTime" in body["find"]["resultFilter"]["attribute"]


def test_find_body_query13_rib_info_scoped_to_rt_fdn():
    body = build_find_body(
        "topology.BgpRibInfo",
        None,
        {"wildcard": {"name": "objectFullName", "value": "tpgy-mgr:AS-65000:RT-65000%10%"}},
    )
    assert body["find"]["fullClassName"] == "topology.BgpRibInfo"
    assert body["find"]["resultFilter"] == {"children": ""}
    assert "RT-65000%10" in body["find"]["filter"]["wildcard"]["value"]


def test_rib_from_pref_addr_and_len():
    svc = Service(10, "VPRN 10", "vprn", "Red_Ope", 10, [], mgr_id=1)
    entry = _rib_from_row(
        {
            "prefAddr": "10.50.1.0",
            "prefLen": "24",
            "prefType": "vpnIpv4",
            "prefRD": "65000:10",
            "nextHop": "10.251.121.250",
            "med": "0",
            "localPref": "100",
            "asPath": "65012",
        },
        svc,
        "65000:10",
        "BgpRibInfoValue",
    )
    assert entry is not None
    assert entry.prefix == "10.50.1.0/24"
    assert entry.next_hop == "10.251.121.250"
    assert entry.as_path == "65012"
    assert entry.source == "BgpRibInfoValue"


def test_cpaa_from_row_protocol_bits():
    cpaa = _cpaa_from_row(
        {
            "objectFullName": "network:10.251.243.250:cpaa",
            "routerId": "10.251.243.250",
            "bgpAsPointer": "tpgy-mgr:AS-65000",
            "protocolRecord": {"bit": ["ospf", "ospfTe", "bgp"]},
            "bgpRibInfoLastRetrieveTime": "1710000000",
            "administrativeState": "up",
            "operationalState": "up",
        }
    )
    assert cpaa is not None
    assert "bgp" in cpaa.protocol_record
    assert cpaa.rib_retrieve == "1710000000"


def test_find_body_query11_igp_as_no_lsdb():
    body = build_find_body(
        "topology.AutonomousSystem",
        [
            "objectFullName",
            "displayedName",
            "asNumber",
            "description",
            "bgpTopologyEnabled",
            "cpaaPointers",
        ],
    )
    assert body["find"]["fullClassName"] == "topology.AutonomousSystem"
    assert body["find"]["resultFilter"]["children"] == ""
    assert "filter" not in body["find"]


def test_find_body_query12_bgp_as_header_only():
    body = build_find_body(
        "topology.BgpAutonomousSystem",
        [
            "objectFullName",
            "displayedName",
            "asNumber",
            "asType",
            "description",
            "igpAdminDomain",
            "cpaaPointers",
        ],
    )
    assert body["find"]["fullClassName"] == "topology.BgpAutonomousSystem"
    assert body["find"]["resultFilter"]["children"] == ""
    assert "filter" not in body["find"]


def test_query17_xml_matches_samo_contract():
    xml = build_cpaa_record_xml("network:10.251.243.250:cpaa")
    assert "generic.GenericObject.configureInstance" in xml
    assert 'xmlns="xmlapi_1.0"' in xml
    assert "<distinguishedName>network:10.251.243.250:cpaa</distinguishedName>" in xml
    assert "<bit>modify</bit>" in xml
    assert "<bit>bgp</bit>" in xml
    assert "<bit>ospf</bit>" in xml
    assert "<bit>ospfTe</bit>" in xml
    assert "<administrativeState>up</administrativeState>" in xml


def test_query17_xml_escapes_fdn():
    xml = build_cpaa_record_xml("network:10.0.0.1:cpaa&x")
    assert "&amp;" in xml
    assert "cpaa&x" not in xml


def test_raise_if_xml_fault():
    with pytest.raises(NspApiError, match="denied"):
        raise_if_xml_fault(
            '<?xml version="1.0"?><r><XMLException><description>denied</description></XMLException></r>'
        )
