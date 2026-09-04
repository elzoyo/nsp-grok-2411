import pytest

from nsp_grok.nsp_api import (
    NspApiError,
    _service_from_row,
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
