"""Live NSP HTTP client (OAuth2 + SAM-O v3 find). --debug prints each request."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from xml.etree import ElementTree

import requests
import urllib3

from nsp_grok.models import (
    AccessInterface,
    Alarm,
    BgpPeer,
    BgpRibInfo,
    BgpRibPrefix,
    Card,
    Cpaa,
    Customer,
    NetworkElement,
    Port,
    TopologyAs,
    Lsp,
    MacEntry,
    RouteNextHop,
    RouteTarget,
    SdpBinding,
    Service,
    ServiceSite,
    ServiceTunnel,
    StatSample,
    StaticRoute,
)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

GATEWAY = "/rest-gateway/rest/api"
V3_BASE = "/nfmpv3service/api"
# Connect + read; find de customers/servicios puede tardar.
REQUEST_TIMEOUT_S = 60


class NspApiError(Exception):
    pass


class UserCancelled(Exception):
    """Ctrl-C u otra cancelación explícita del operador."""


def redact_headers(headers: dict[str, str]) -> dict[str, str]:
    out = dict(headers)
    if "Authorization" in out:
        scheme = out["Authorization"].split(" ", 1)[0]
        out["Authorization"] = f"{scheme} ***"
    return out


def build_find_body(
    full_class_name: str,
    attributes: list[str] | None = None,
    filter_: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """SAM-O v3 find: always children empty string; omit attribute unless a list is given."""
    result_filter: dict[str, Any] = {"children": ""}
    if attributes:
        result_filter["attribute"] = attributes
    find_body: dict[str, Any] = {
        "fullClassName": full_class_name,
        "resultFilter": result_filter,
    }
    if filter_:
        find_body["filter"] = filter_
    return {"find": find_body}


def build_cpaa_record_xml(
    fdn: str,
    event_bits: list[str] | None = None,
    record_bits: list[str] | None = None,
) -> str:
    """Query 17: generic.GenericObject.configureInstance on topology.Cpaa (write)."""
    from xml.sax.saxutils import escape

    events = event_bits or ["ospf", "bgp"]
    records = record_bits or ["ospf", "ospfTe", "bgp"]
    ev = "".join(f"<bit>{escape(b)}</bit>" for b in events)
    rec = "".join(f"<bit>{escape(b)}</bit>" for b in records)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<generic.GenericObject.configureInstance xmlns="xmlapi_1.0">'
        "<deployer>immediate</deployer>"
        f"<distinguishedName>{escape(fdn)}</distinguishedName>"
        "<configInfo>"
        "<topology.Cpaa>"
        "<actionMask><bit>modify</bit></actionMask>"
        f"<protocolEventTypes>{ev}</protocolEventTypes>"
        f"<protocolRecord>{rec}</protocolRecord>"
        "<administrativeState>up</administrativeState>"
        "</topology.Cpaa>"
        "</configInfo>"
        "</generic.GenericObject.configureInstance>"
    )


def raise_if_xml_fault(xml_text: str) -> None:
    text = (xml_text or "").strip()
    if not text.startswith("<"):
        return
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError:
        return
    for el in root.iter():
        if _strip_ns(el.tag) == "XMLException":
            desc = next(
                (c.text for c in el if _strip_ns(c.tag) == "description"),
                el.text,
            )
            raise NspApiError(desc or "XMLException")


def format_request(method: str, url: str, headers: dict[str, str], body: Any) -> str:
    lines = [f">>> {method} {url}", ">>> headers:"]
    lines.append(json.dumps(redact_headers(headers), indent=2, ensure_ascii=False))
    if body is not None:
        lines.append(">>> body:")
        lines.append(json.dumps(body, indent=2, ensure_ascii=False))
    return "\n".join(lines)


def _strip_ns(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _element_to_value(el: ElementTree.Element) -> Any:
    children = list(el)
    if not children:
        return (el.text or "").strip()
    result: dict[str, Any] = {}
    for child in children:
        tag = _strip_ns(child.tag)
        value = _element_to_value(child)
        if tag in result:
            existing = result[tag]
            if isinstance(existing, list):
                existing.append(value)
            else:
                result[tag] = [existing, value]
        else:
            result[tag] = value
    return result


def parse_find_xml(xml_text: str) -> list[dict[str, Any]]:
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError as exc:
        raise NspApiError(f"XML de find inválido: {exc}") from exc
    exception_el = next((c for c in root if _strip_ns(c.tag) == "XMLException"), None)
    if exception_el is not None:
        description = next(
            (c.text for c in exception_el if _strip_ns(c.tag) == "description"),
            None,
        )
        raise NspApiError(description or "XMLException")
    result_el = next((c for c in root if _strip_ns(c.tag) == "result"), None)
    if result_el is None:
        return []
    return [_element_to_value(child) for child in result_el]


@dataclass
class DebugSink:
    enabled: bool = False
    lines: list[str] | None = None
    printer: Any = None

    def emit(self, text: str) -> None:
        if not self.enabled:
            return
        if self.lines is not None:
            self.lines.append(text)
        if self.printer:
            self.printer(text)


class NspClient:
    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        debug: DebugSink | None = None,
        timeout: int | tuple[float, float] = REQUEST_TIMEOUT_S,
        verify: bool = False,
    ) -> None:
        self.host = host
        self.username = username
        self._password = password
        self.debug = debug or DebugSink()
        if isinstance(timeout, tuple):
            self.timeout = timeout
        else:
            self.timeout = (float(timeout), float(timeout))
        self.verify = verify
        self.token: str | None = None
        self._http = requests.Session()

    def _url(self, path: str) -> str:
        return f"https://{self.host}{path}"

    def _send(
        self,
        method: str,
        url: str,
        headers: dict[str, str],
        body: Any = None,
        xml: str | None = None,
    ) -> requests.Response:
        if xml is not None:
            self.debug.emit(f">>> {method} {url}\n>>> body:\n{xml}")
        else:
            self.debug.emit(format_request(method, url, headers, body))
        try:
            kwargs: dict[str, Any] = {
                "headers": headers,
                "timeout": self.timeout,
                "verify": self.verify,
            }
            if xml is not None:
                kwargs["data"] = xml.encode("utf-8")
            else:
                kwargs["json"] = body
            response = self._http.request(method, url, **kwargs)
        except KeyboardInterrupt as exc:
            self.debug.emit("<<< cancelado (Ctrl-C)")
            raise UserCancelled("Cancelado con Ctrl-C.") from exc
        except UserCancelled:
            raise
        except requests.Timeout as exc:
            self.debug.emit(f"<<< timeout tras {self.timeout}s: {exc}")
            raise NspApiError(
                f"timeout de {self.timeout[1]:.0f}s al consultar {url}"
            ) from exc
        except requests.RequestException as exc:
            self.debug.emit(f"<<< error de transporte: {exc}")
            raise NspApiError(f"no se pudo contactar {url}: {exc}") from exc
        except Exception as exc:
            self.debug.emit(f"<<< error: {type(exc).__name__}: {exc}")
            raise NspApiError(f"falla al consultar {url}: {exc}") from exc
        size = len(response.content or b"")
        self.debug.emit(f"<<< HTTP {response.status_code}  ({size} bytes)")
        return response

    def login(self) -> str:
        raw = f"{self.username}:{self._password}".encode()
        basic = base64.b64encode(raw).decode()
        url = self._url(f"{GATEWAY}/v1/auth/token")
        headers = {
            "Authorization": f"Basic {basic}",
            "Content-Type": "application/json",
        }
        response = self._send("POST", url, headers, {"grant_type": "client_credentials"})
        if not response.ok:
            raise NspApiError(
                f"login NSP falló HTTP {response.status_code} contra {self.host}"
            )
        try:
            data = response.json()
        except ValueError as exc:
            raise NspApiError(
                f"login NSP respuesta inválida de {self.host}"
            ) from exc
        token = data.get("access_token")
        if not token:
            raise NspApiError("login NSP no devolvió access_token")
        self.token = token
        return token

    def find(
        self,
        full_class_name: str,
        attributes: list[str] | None = None,
        filter_: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        if not self.token:
            raise NspApiError("no hay token; login primero")
        body = build_find_body(full_class_name, attributes, filter_)
        url = self._url(f"{V3_BASE}/v3/find")
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        response = self._send("POST", url, headers, body)
        if not response.ok:
            raise NspApiError(f"find {full_class_name} HTTP {response.status_code}")
        return parse_find_xml(response.text)

    def load_customers(self) -> dict[int, Customer]:
        rows = self.find(
            "subscr.Subscriber",
            ["objectFullName", "subscriberId", "displayedName", "description"],
        )
        out: dict[int, Customer] = {}
        for row in rows:
            sid = _subscriber_id(row)
            if sid is None:
                continue
            out[sid] = Customer(
                subscriber_id=sid,
                displayed_name=str(row.get("displayedName") or f"subscriber:{sid}"),
                description=str(row.get("description") or ""),
            )
        return out

    def load_services(self, subscriber_id: int) -> list[Service]:
        pointer = f"subscriber:{subscriber_id}"
        filt = {"equal": {"name": "subscriberPointer", "value": pointer}}
        attrs = [
            "objectFullName",
            "id",
            "serviceId",
            "displayedName",
            "description",
            "subscriberPointer",
            "administrativeState",
            "operationalState",
        ]
        services: list[Service] = []
        for svc_type, class_name in (
            ("vprn", "vprn.Vprn"),
            ("vpls", "vpls.Vpls"),
            ("epipe", "epipe.Epipe"),
        ):
            for row in self.find(class_name, attrs, filt):
                svc = _service_from_row(row, svc_type, subscriber_id)
                if svc:
                    services.append(svc)
        return services

    def load_sites(self, svc: Service) -> list[ServiceSite]:
        class_name = {
            "vprn": "vprn.Site",
            "vpls": "vpls.Site",
            "epipe": "epipe.Site",
        }[svc.svc_type]
        wildcard = {
            "wildcard": {
                "name": "objectFullName",
                "value": f"{svc.fdn}:%",
            }
        }
        rows = self.find(
            class_name,
            [
                "objectFullName",
                "siteId",
                "serviceId",
                "displayedName",
                "administrativeState",
                "operationalState",
            ],
            wildcard,
        )
        sites: list[ServiceSite] = []
        for row in rows:
            site_id = str(row.get("siteId") or "")
            if not site_id:
                fdn = str(row.get("objectFullName") or "")
                site_id = fdn.rsplit(":", 1)[-1]
            sites.append(
                ServiceSite(
                    svc_id=svc.svc_id,
                    site_id=site_id,
                    ne=str(row.get("displayedName") or site_id),
                    admin=_state(row.get("administrativeState")),
                    oper=_state(row.get("operationalState")),
                    mgr_id=svc.mgr_id,
                )
            )
        return sites

    def load_saps(
        self, svc: Service, sites: list[ServiceSite] | None = None
    ) -> list[AccessInterface]:
        if svc.svc_type == "vprn":
            classes = ["vprn.L3AccessInterface"]
        elif svc.svc_type == "vpls":
            classes = ["vpls.L2AccessInterface"]
        else:
            classes = ["epipe.L2AccessInterface", "vll.L2AccessInterface"]
        attrs = [
            "objectFullName",
            "displayedName",
            "siteId",
            "portPointer",
            "primaryIPv4Address",
            "administrativeState",
            "operationalState",
        ]
        if sites:
            filters = [
                {
                    "wildcard": {
                        "name": "objectFullName",
                        "value": f"{svc.fdn}:{site.site_id}%",
                    }
                }
                for site in sites
            ]
        else:
            filters = [
                {"wildcard": {"name": "objectFullName", "value": f"{svc.fdn}:%"}}
            ]
        saps: list[AccessInterface] = []
        for filt in filters:
            rows = self._find_first_class(classes, attrs, filt)
            saps.extend(_saps_from_rows(svc, rows))
        return saps

    def _find_first_class(
        self,
        classes: list[str],
        attributes: list[str] | None,
        filter_: dict[str, Any],
    ) -> list[dict[str, Any]]:
        last_err: NspApiError | None = None
        for class_name in classes:
            try:
                return self.find(class_name, attributes, filter_)
            except NspApiError as exc:
                last_err = exc
        if last_err is not None:
            raise last_err
        return []

    def apply_vr_masks(
        self, svc: Service, sites: list[ServiceSite], saps: list[AccessInterface]
    ) -> list[AccessInterface]:
        """Query 7: rtr.VirtualRouterIpAddress — prefix length for SAP IPs."""
        if svc.svc_type != "vprn" or not sites:
            return saps
        by_addr: dict[str, str] = {}
        for site in sites:
            rows = self.find(
                "rtr.VirtualRouterIpAddress",
                None,
                {
                    "wildcard": {
                        "name": "objectFullName",
                        "value": f"{svc.fdn}:{site.site_id}:%",
                    }
                },
            )
            for row in rows:
                cidr = _vr_cidr(row)
                if cidr:
                    addr = cidr.split("/", 1)[0]
                    by_addr[addr] = cidr
        if not by_addr:
            return saps
        for sap in saps:
            raw = sap.primary_ipv4
            if not raw or "/" in raw:
                continue
            addr = raw.split("/", 1)[0]
            if addr in by_addr:
                sap.primary_ipv4 = by_addr[addr]
        return saps

    def load_static_routes(
        self, svc: Service, sites: list[ServiceSite]
    ) -> list[StaticRoute]:
        """Query 8: rtr.StaticRoute under network:<NE>:vprn-<serviceId>:%"""
        if svc.svc_type != "vprn":
            return []
        out: list[StaticRoute] = []
        for site in sites:
            rows = self.find(
                "rtr.StaticRoute",
                None,
                {
                    "wildcard": {
                        "name": "objectFullName",
                        "value": f"network:{site.site_id}:vprn-{svc.svc_id}:%",
                    }
                },
            )
            for row in rows:
                sr = _static_from_row(row, svc, site.site_id)
                if sr:
                    out.append(sr)
        return out

    def load_bgp_sites(self, svc: Service, sites: list[ServiceSite]) -> list[BgpPeer]:
        """Query 9: bgp.Site under network:<NE>:vprn-<serviceId>% (config, not RIB)."""
        if svc.svc_type != "vprn":
            return []
        out: list[BgpPeer] = []
        for site in sites:
            rows = self.find(
                "bgp.Site",
                [
                    "objectFullName",
                    "displayedName",
                    "administrativeState",
                    "operationalState",
                ],
                {
                    "wildcard": {
                        "name": "objectFullName",
                        "value": f"network:{site.site_id}:vprn-{svc.svc_id}%",
                    }
                },
            )
            for row in rows:
                fdn = str(row.get("objectFullName") or "")
                name = str(row.get("displayedName") or fdn.rsplit(":", 1)[-1] or "bgp")
                out.append(
                    BgpPeer(
                        svc_id=svc.svc_id,
                        site_id=site.site_id,
                        peer_ip=name,
                        peer_as=_int_field(row, "asNumber", "peerAS") or 0,
                        admin=_state(row.get("administrativeState")),
                        oper=_state(row.get("operationalState")),
                    )
                )
        return out

    def load_route_targets(self, svc: Service) -> list[RouteTarget]:
        """Query 15: topology.BgpRoutesRouteTarget; keep RTs that match this serviceId."""
        if svc.svc_type != "vprn":
            return []
        rows = self.find(
            "topology.BgpRoutesRouteTarget",
            [
                "objectFullName",
                "routeTargetString",
                "format",
                "numNextHops",
                "asNumber",
            ],
        )
        out: list[RouteTarget] = []
        for row in rows:
            value = str(row.get("routeTargetString") or "")
            if not _rt_matches_service(value, svc):
                continue
            out.append(
                RouteTarget(
                    svc_id=svc.svc_id,
                    direction="vpn",
                    value=value,
                    num_next_hops=_int_field(row, "numNextHops") or 0,
                )
            )
        return out

    def load_route_next_hops(
        self, svc: Service, route_targets: list[RouteTarget]
    ) -> list[RouteNextHop]:
        """Query 16: topology.BgpRoutesNextHop filtered by routeTargetString."""
        if svc.svc_type != "vprn":
            return []
        attrs = [
            "objectFullName",
            "nextHop",
            "nextHopAddrType",
            "routeTargetString",
            "siteId",
        ]
        out: list[RouteNextHop] = []
        seen: set[tuple[str, str]] = set()
        for rt in route_targets:
            rows = self.find(
                "topology.BgpRoutesNextHop",
                attrs,
                {"equal": {"name": "routeTargetString", "value": rt.value}},
            )
            for row in rows:
                nh = _next_hop_from_row(row, svc, rt.value)
                if nh is None:
                    continue
                key = (nh.route_target, nh.next_hop)
                if key in seen:
                    continue
                seen.add(key)
                out.append(nh)
        return out

    def load_sdp_bindings(self, svc: Service) -> list[SdpBinding]:
        """SDP binding under the service FDN (same wildcard contract as vprn.Site)."""
        if svc.svc_type == "vprn":
            classes = ["vprn.SdpBinding"]
        elif svc.svc_type == "vpls":
            classes = ["vpls.SdpBinding"]
        else:
            classes = ["epipe.SdpBinding", "vll.SdpBinding"]
        filt = {
            "wildcard": {"name": "objectFullName", "value": f"{svc.fdn}:%"}
        }
        try:
            rows = self._find_first_class(classes, None, filt)
        except NspApiError:
            return []
        out: list[SdpBinding] = []
        for row in rows:
            binding = _binding_from_row(row, svc)
            if binding:
                out.append(binding)
        return out

    def load_tunnels(self, bindings: list[SdpBinding]) -> list[ServiceTunnel]:
        """svt.Tunnel by SDP id (help: svt.Tunnel). children empty; no global dump."""
        out: list[ServiceTunnel] = []
        seen: set[int] = set()
        for sdp_id in sorted({b.sdp_id for b in bindings if b.sdp_id}):
            if sdp_id in seen:
                continue
            rows = self._optional_find(
                ["svt.Tunnel"],
                None,
                {"equal": {"name": "id", "value": str(sdp_id)}},
            )
            if not rows:
                rows = self._optional_find(
                    ["svt.Tunnel"],
                    None,
                    {"equal": {"name": "sdpId", "value": str(sdp_id)}},
                )
            for row in rows:
                tun = _tunnel_from_row(row, sdp_id)
                if tun and tun.sdp_id not in seen:
                    seen.add(tun.sdp_id)
                    out.append(tun)
        return out

    def load_lsps(self, tunnels: list[ServiceTunnel]) -> list[Lsp]:
        """mpls.DynamicLsp of SDPs (help: mpls.DynamicLsp). One find per LSP name."""
        out: list[Lsp] = []
        seen: set[str] = set()
        for name in sorted({t.lsp for t in tunnels if t.lsp}):
            if name in seen:
                continue
            rows = self._optional_find(
                ["mpls.DynamicLsp", "mpls.StaticLsp"],
                None,
                {"equal": {"name": "displayedName", "value": name}},
            )
            if not rows:
                rows = self._optional_find(
                    ["mpls.DynamicLsp", "mpls.StaticLsp"],
                    None,
                    {
                        "wildcard": {
                            "name": "objectFullName",
                            "value": f"%{name}",
                        }
                    },
                )
            for row in rows:
                lsp = _lsp_from_row(row, name)
                if lsp and lsp.name not in seen:
                    seen.add(lsp.name)
                    out.append(lsp)
            if name not in seen:
                seen.add(name)
        return out

    def load_service_alarms(self, svc: Service) -> list[Alarm]:
        """fm.AlarmObject on the service FDN — never unfiltered."""
        filt = {
            "wildcard": {
                "name": "objectFullName",
                "value": f"{svc.fdn}%",
            }
        }
        rows = self._optional_find(["fm.AlarmObject"], None, filt)
        if not rows:
            rows = self._optional_find(
                ["fm.AlarmObject"],
                None,
                {
                    "wildcard": {
                        "name": "affectedObjectPointer",
                        "value": f"{svc.fdn}%",
                    }
                },
            )
        out: list[Alarm] = []
        for row in rows:
            alarm = _alarm_from_row(row, svc)
            if alarm:
                out.append(alarm)
        return out

    def load_macs(self, svc: Service) -> list[MacEntry]:
        """VPLS FIB / ProxyArpNdMacAddress under the service FDN."""
        if svc.svc_type != "vpls":
            return []
        filt = {
            "wildcard": {"name": "objectFullName", "value": f"{svc.fdn}:%"}
        }
        rows = self._optional_find(
            ["vpls.MacRecord", "ProxyArpNdMacAddress", "vpls.FdbMacAddress"],
            None,
            filt,
        )
        out: list[MacEntry] = []
        for row in rows:
            mac = _mac_from_row(row, svc)
            if mac:
                out.append(mac)
        return out

    def load_cpaa(self) -> list[Cpaa]:
        """Query 10: topology.Cpaa with children empty and a short attribute list."""
        rows = self._try_find(
            ["topology.Cpaa"],
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
            None,
        )
        return [cpaa for row in rows if (cpaa := _cpaa_from_row(row))]

    def configure_cpaa_bgp_record(self, fdn: str, cpaa: Cpaa | None = None) -> str:
        """Query 17: POST XML configureInstance. Explicit write; never called on login."""
        if not self.token:
            raise NspApiError("no hay token; login primero")
        if not fdn:
            raise NspApiError("hace falta el FDN del CPAA (network:<ip>:cpaa)")
        events = ["ospf", "bgp"]
        records = ["ospf", "ospfTe", "bgp"]
        if cpaa:
            ev = [b.strip() for b in cpaa.protocol_events.split(",") if b.strip()]
            rec = [b.strip() for b in cpaa.protocol_record.split(",") if b.strip()]
            if ev:
                events = list(dict.fromkeys(ev + ["bgp"]))
            if rec:
                records = list(dict.fromkeys(rec + ["bgp"]))
        xml = build_cpaa_record_xml(fdn, events, records)
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/xml",
        }
        last_err: NspApiError | None = None
        for path in (f"{V3_BASE}/v3/xml", f"{V3_BASE}/v3/request"):
            url = self._url(path)
            response = self._send("POST", url, headers, xml=xml)
            if response.ok:
                raise_if_xml_fault(response.text)
                return fdn
            last_err = NspApiError(
                f"query 17 configureInstance HTTP {response.status_code} contra {url}"
            )
        raise last_err or NspApiError("query 17 falló")

    def load_igp_domains(self) -> list[TopologyAs]:
        """Query 11: topology.AutonomousSystem — cabecera IGP, children empty (sin LSDB)."""
        rows = self._try_find(
            ["topology.AutonomousSystem"],
            [
                "objectFullName",
                "displayedName",
                "asNumber",
                "description",
                "bgpTopologyEnabled",
                "cpaaPointers",
            ],
            None,
        )
        return [d for row in rows if (d := _topology_as_from_row(row, "igp"))]

    def load_bgp_ases(self) -> list[TopologyAs]:
        """Query 12: topology.BgpAutonomousSystem — cabecera BGP, children empty (sin RT/NH)."""
        rows = self._try_find(
            ["topology.BgpAutonomousSystem"],
            [
                "objectFullName",
                "displayedName",
                "asNumber",
                "asType",
                "description",
                "igpAdminDomain",
                "cpaaPointers",
            ],
            None,
        )
        return [d for row in rows if (d := _topology_as_from_row(row, "bgp"))]

    def load_network_elements(self) -> dict[str, NetworkElement]:
        """netw.NetworkElement — inventory list, children empty, no port dump."""
        rows = self._try_find(
            ["netw.NetworkElement"],
            [
                "objectFullName",
                "displayedName",
                "siteId",
                "siteName",
                "version",
                "chassisType",
                "administrativeState",
                "operationalState",
                "macAddress",
            ],
            None,
        )
        out: dict[str, NetworkElement] = {}
        for row in rows:
            ne = _ne_from_row(row)
            if ne:
                out[ne.name] = ne
        return out

    def load_ne_hardware(self, ne: NetworkElement) -> list[Card]:
        """equipment.PhysicalPort for one NE: wildcard network:<siteId>:%  (XML API inventory)."""
        if not ne.system_ip:
            return []
        port_rows = self._try_find(
            ["equipment.PhysicalPort"],
            [
                "objectFullName",
                "displayedName",
                "administrativeState",
                "operationalState",
                "mode",
                "encapType",
                "actualSpeed",
            ],
            {
                "wildcard": {
                    "name": "objectFullName",
                    "value": f"network:{ne.system_ip}:%",
                }
            },
        )
        card_rows = self._try_find(
            ["equipment.Card"],
            [
                "objectFullName",
                "displayedName",
                "specificType",
                "administrativeState",
                "operationalState",
            ],
            {
                "wildcard": {
                    "name": "objectFullName",
                    "value": f"network:{ne.system_ip}:%",
                }
            },
        )
        return _cards_from_inventory(port_rows, card_rows)

    def load_bgp_rib_info(
        self, svc: Service, route_targets: list[RouteTarget]
    ) -> list[BgpRibInfo]:
        """Query 13 parent: topology.BgpRibInfo scoped to AS/RT FDN, never unfiltered."""
        if svc.svc_type != "vprn":
            return []
        out: list[BgpRibInfo] = []
        seen: set[str] = set()
        for wildcard in _rt_fdn_wildcards(route_targets, svc):
            rows = self._try_find(
                ["topology.BgpRibInfo"],
                [
                    "objectFullName",
                    "displayedName",
                    "asNumber",
                    "nextHop",
                    "med",
                    "localPref",
                    "peer",
                    "originatorId",
                    "numRoutes",
                    "type",
                ],
                {"wildcard": {"name": "objectFullName", "value": wildcard}},
            )
            for row in rows:
                info = _rib_info_from_row(row, svc)
                if info is None or info.fdn in seen:
                    continue
                seen.add(info.fdn)
                out.append(info)
        return out

    def load_bgp_rib(self, svc: Service, route_targets: list[RouteTarget]) -> list[BgpRibPrefix]:
        """Queries 13 value + 14: prefixes for this VPRN only (RD/RT FDN), children empty."""
        if svc.svc_type != "vprn":
            return []
        rds = _rds_of(svc, route_targets)
        out: list[BgpRibPrefix] = []
        seen: set[tuple[str, str, str]] = set()

        def _take(rows: list[dict[str, Any]], rd: str, source: str) -> None:
            for row in rows:
                entry = _rib_from_row(row, svc, rd, source)
                if entry is None:
                    continue
                key = (entry.rd, entry.prefix, entry.next_hop)
                if key in seen:
                    continue
                seen.add(key)
                out.append(entry)

        for rd in rds:
            q14 = {
                "and": {
                    "equal": [
                        {"name": "prefType", "value": "vpnIpv4"},
                        {"name": "prefRD", "value": rd},
                    ]
                }
            }
            _take(self._try_find(["topology.BgpMonitoredPrefix"], None, q14), rd, "BgpMonitoredPrefix")
            q14b = {
                "and": {
                    "equal": [
                        {"name": "prefType", "value": "vpnIpv4"},
                        {"name": "prefRd", "value": rd},
                    ]
                }
            }
            _take(self._try_find(["topology.BgpMonitoredPrefix"], None, q14b), rd, "BgpMonitoredPrefix")
            for wildcard in _rt_fdn_wildcards_for_rd(rd):
                _take(
                    self._try_find(
                        ["topology.BgpRibInfoValue"],
                        None,
                        {"wildcard": {"name": "objectFullName", "value": wildcard}},
                    ),
                    rd,
                    "BgpRibInfoValue",
                )
            _take(
                self._try_find(
                    ["topology.BgpRibInfoValue"],
                    None,
                    {"equal": {"name": "routeTargetString", "value": rd}},
                ),
                rd,
                "BgpRibInfoValue",
            )
        return out

    def load_stats(self, pointer: str, window_s: int = 900) -> list[StatSample]:
        """On-demand stats log records (XML API: find + timeCaptured, children empty)."""
        pointer = pointer.strip()
        if not pointer:
            return []
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        first = str(now_ms - window_s * 1000)
        second = str(now_ms)
        filt = {
            "and": {
                "equal": {"name": "monitoredObjectPointer", "value": pointer},
                "between": {"name": "timeCaptured", "first": first, "second": second},
            }
        }
        rows = self._optional_find(
            [
                "equipment.InterfaceAdditionalStatsLogRecord",
                "equipment.InterfaceStatsLogRecord",
                "mpls.MplsLspStatsLogRecord",
            ],
            None,
            filt,
        )
        samples: list[StatSample] = []
        for row in rows:
            samples.extend(_stats_from_row(row, pointer))
        return samples

    def _optional_find(
        self,
        classes: list[str],
        attributes: list[str] | None,
        filter_: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        try:
            return self._find_first_class(classes, attributes, filter_ or {})
        except NspApiError:
            return []

    def _try_find(
        self,
        classes: list[str],
        attributes: list[str] | None,
        filter_: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        rows = self._optional_find(classes, attributes, filter_)
        if rows or not attributes:
            return rows
        return self._optional_find(classes, None, filter_)


def _rds_of(svc: Service, route_targets: list[RouteTarget]) -> list[str]:
    rds: list[str] = []
    if svc.route_distinguisher:
        rds.append(svc.route_distinguisher)
    for rt in route_targets:
        if rt.value and rt.value not in rds:
            rds.append(rt.value)
    return rds


def _rt_token(rd: str) -> str:
    left, sep, right = rd.partition(":")
    if not sep:
        return f"RT-{rd}"
    return f"RT-{left}%{right}"


def _rt_fdn_wildcards_for_rd(rd: str) -> list[str]:
    token = _rt_token(rd)
    left = rd.split(":", 1)[0]
    return [
        f"tpgy-mgr:AS-{left}:{token}%",
        f"tpgy-mgr:AS-{left}:{token}:%",
    ]


def _rt_fdn_wildcards(route_targets: list[RouteTarget], svc: Service) -> list[str]:
    out: list[str] = []
    for rd in _rds_of(svc, route_targets):
        for w in _rt_fdn_wildcards_for_rd(rd):
            if w not in out:
                out.append(w)
    return out


def _rt_matches_service(value: str, svc: Service) -> bool:
    if not value:
        return False
    if svc.route_distinguisher and value == svc.route_distinguisher:
        return True
    return value.endswith(f":{svc.svc_id}")


def _next_hop_from_row(
    row: dict[str, Any], svc: Service, route_target: str
) -> RouteNextHop | None:
    nh = str(row.get("nextHop") or "").strip()
    if not nh or nh == "0.0.0.0":
        return None
    rt = str(row.get("routeTargetString") or route_target)
    return RouteNextHop(
        svc_id=svc.svc_id,
        route_target=rt,
        next_hop=nh,
        addr_type=str(row.get("nextHopAddrType") or "ipv4"),
        cpaa_site_id=str(row.get("siteId") or ""),
    )


def _sdp_id_from_row(row: dict[str, Any]) -> int | None:
    sid = _int_field(row, "sdpId", "sdpID")
    if sid is not None:
        return sid
    pointer = str(row.get("sdpPointer") or row.get("objectFullName") or "")
    for part in reversed(pointer.replace("/", ":").split(":")):
        text = part.lower().replace("sdp-", "").replace("sdp", "")
        if text.isdigit():
            return int(text)
    return None


def _binding_from_row(row: dict[str, Any], svc: Service) -> SdpBinding | None:
    fdn = str(row.get("objectFullName") or "")
    site_id = str(row.get("siteId") or "")
    if not site_id and fdn.startswith(svc.fdn + ":"):
        site_id = fdn[len(svc.fdn) + 1 :].split(":", 1)[0]
    sdp_id = _sdp_id_from_row(row)
    if sdp_id is None:
        return None
    raw_type = str(row.get("type") or row.get("bindingType") or row.get("sdpBindingType") or "")
    btype = raw_type.lower() or "spoke"
    if "mesh" in btype:
        btype = "mesh"
    elif "spoke" in btype:
        btype = "spoke"
    return SdpBinding(
        svc_id=svc.svc_id,
        site_id=site_id,
        sdp_id=sdp_id,
        vc_id=_int_field(row, "vcId", "vcIdentifier") or 0,
        binding_type=btype,
        admin=_state(row.get("administrativeState")),
        oper=_state(row.get("operationalState")),
        mgr_id=svc.mgr_id,
    )


def _pointer_tail(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return text.rsplit(":", 1)[-1]


def _tunnel_from_row(row: dict[str, Any], sdp_id: int) -> ServiceTunnel | None:
    sid = _int_field(row, "id", "sdpId") or sdp_id
    name = str(row.get("displayedName") or f"sdp-{sid}")
    far = str(row.get("farEndIpAddress") or row.get("farEnd") or "")
    src = _pointer_tail(row.get("sourceSiteId") or row.get("fromPointer") or row.get("siteId"))
    lsp = _pointer_tail(row.get("lspPointer") or row.get("lsp") or row.get("primaryLsp"))
    sig = str(row.get("signaling") or row.get("signalingType") or "")
    return ServiceTunnel(
        sdp_id=sid,
        name=name,
        from_ne=src,
        to_ne=far or _pointer_tail(row.get("destSiteId")),
        signaling=sig.lower() or "tldp",
        lsp=lsp,
        admin=_state(row.get("administrativeState")),
        oper=_state(row.get("operationalState")),
        far_end=far,
    )


def _lsp_from_row(row: dict[str, Any], fallback_name: str) -> Lsp | None:
    name = str(row.get("displayedName") or fallback_name)
    if not name:
        return None
    src = _pointer_tail(row.get("fromPointer") or row.get("sourceSiteId") or row.get("from"))
    dst = _pointer_tail(row.get("toPointer") or row.get("destSiteId") or row.get("to"))
    path = str(row.get("pathName") or row.get("path") or row.get("primaryPath") or "")
    hops_raw = row.get("hops") or row.get("hopList") or ""
    if isinstance(hops_raw, list):
        hops = [str(h) for h in hops_raw]
    elif hops_raw:
        hops = [p.strip() for p in str(hops_raw).replace("→", ",").split(",") if p.strip()]
    else:
        hops = []
    lsp_type = str(row.get("type") or row.get("lspType") or "dynamic").lower()
    sig = str(row.get("signaling") or row.get("signalingType") or "rsvp").lower()
    return Lsp(
        name=name,
        lsp_type=lsp_type if lsp_type else "dynamic",
        signaling=sig if sig else "rsvp",
        from_ne=src,
        to_ne=dst,
        path=path or "loose-any",
        hops=hops,
        admin=_state(row.get("administrativeState")),
        oper=_state(row.get("operationalState")),
    )


def _severity(value: Any) -> str:
    text = str(value or "").lower()
    for sev in ("critical", "major", "minor", "warning", "cleared"):
        if sev in text:
            return sev
    return "warning"


def _parse_time(raw: Any) -> datetime:
    now = datetime.now(timezone.utc)
    if raw is None or raw == "":
        return now
    text = str(raw).strip()
    try:
        num = float(text)
        if num > 10_000_000_000:
            return datetime.fromtimestamp(num / 1000.0, tz=timezone.utc)
        if num > 1_000_000_000:
            return datetime.fromtimestamp(num, tz=timezone.utc)
    except ValueError:
        pass
    cleaned = text.replace("Z", "+0000")
    if "+" not in cleaned[10:] and "-" not in cleaned[10:]:
        cleaned = cleaned[:19]
        try:
            return datetime.strptime(cleaned, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
        except ValueError:
            try:
                return datetime.strptime(cleaned, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            except ValueError:
                return now
    try:
        return datetime.strptime(cleaned[:24], "%Y-%m-%dT%H:%M:%S%z")
    except ValueError:
        return now


def _alarm_from_row(row: dict[str, Any], svc: Service) -> Alarm | None:
    fdn = str(row.get("objectFullName") or row.get("affectedObjectPointer") or svc.fdn)
    alarm_id = str(
        row.get("alarmId")
        or row.get("displayedName")
        or row.get("id")
        or fdn.rsplit(":", 1)[-1]
        or ""
    )
    if not alarm_id:
        return None
    ne = str(row.get("siteId") or row.get("ne") or _pointer_tail(row.get("nodePointer")) or "")
    return Alarm(
        id=alarm_id,
        severity=_severity(row.get("severity") or row.get("perceivedSeverity")),  # type: ignore[arg-type]
        probable_cause=str(row.get("probableCause") or row.get("specificProblem") or ""),
        object_fdn=fdn,
        ne=ne,
        raised=_parse_time(row.get("timeRaised") or row.get("lastTimeDetected") or row.get("firstTimeDetected")),
        additional_text=str(row.get("additionalText") or row.get("description") or ""),
        acked=str(row.get("acknowledged") or "").lower() in {"true", "yes", "1"},
        cleared=str(row.get("cleared") or "").lower() in {"true", "yes", "1"},
    )


def _mac_from_row(row: dict[str, Any], svc: Service) -> MacEntry | None:
    mac = str(row.get("macAddress") or row.get("mac") or row.get("displayedName") or "").strip()
    if not mac or ":" not in mac and "-" not in mac and len(mac) < 12:
        fdn = str(row.get("objectFullName") or "")
        mac = fdn.rsplit(":", 1)[-1]
    if not mac:
        return None
    mac = mac.replace("-", ":")
    site_id = str(row.get("siteId") or "")
    if not site_id:
        fdn = str(row.get("objectFullName") or "")
        if fdn.startswith(svc.fdn + ":"):
            site_id = fdn[len(svc.fdn) + 1 :].split(":", 1)[0]
    source = str(row.get("type") or row.get("source") or row.get("learnedType") or "learned").lower()
    if "static" in source:
        source = "static"
    elif "dyn" in source or "learn" in source:
        source = "learned"
    port = _port_from_pointer(str(row.get("portPointer") or row.get("sapPointer") or row.get("port") or ""))
    return MacEntry(
        svc_id=svc.svc_id,
        site_id=site_id,
        mac=mac,
        port=port,
        source=source or "learned",
    )


def _rib_from_row(
    row: dict[str, Any], svc: Service, rd: str, source: str
) -> BgpRibPrefix | None:
    addr = str(row.get("prefAddr") or row.get("prefix") or row.get("prefPrefix") or row.get("ipPrefix") or "").strip()
    plen = _int_field(row, "prefLen", "prefixLength", "prefLength")
    if addr and plen is not None and "/" not in addr:
        prefix = f"{addr}/{plen}"
    elif addr:
        prefix = addr
    else:
        prefix = str(row.get("displayedName") or "").strip()
        fdn = str(row.get("objectFullName") or "")
        if not prefix or prefix.startswith("tpgy-mgr:"):
            prefix = fdn.rsplit(":", 1)[-1] if fdn else ""
    if not prefix or prefix in {"%", ""}:
        return None
    if prefix.startswith("tpgy-mgr:") or prefix.startswith("NH-"):
        return None
    return BgpRibPrefix(
        svc_id=svc.svc_id,
        prefix=prefix,
        rd=str(row.get("prefRD") or row.get("prefRd") or row.get("routeDistinguisher") or rd),
        pref_type=str(row.get("prefType") or "vpnIpv4"),
        next_hop=str(row.get("nextHop") or row.get("nexthop") or ""),
        source=source,
        med=str(row.get("med") or row.get("MED") or ""),
        local_pref=str(row.get("localPref") or row.get("LOCAL-PREF") or ""),
        as_path=str(row.get("asPath") or row.get("asPathStr") or ""),
        peer=str(row.get("peer") or row.get("peerIp") or ""),
        originator_id=str(row.get("originatorId") or row.get("originatorID") or ""),
    )


def _bits(value: Any) -> str:
    if isinstance(value, list):
        return ",".join(str(v) for v in value)
    if isinstance(value, dict):
        bit = value.get("bit")
        if isinstance(bit, list):
            return ",".join(str(b) for b in bit)
        if bit:
            return str(bit)
    return str(value or "")


def _ne_from_row(row: dict[str, Any]) -> NetworkElement | None:
    fdn = str(row.get("objectFullName") or "")
    site_id = str(row.get("siteId") or "")
    if not site_id and fdn.startswith("network:"):
        site_id = fdn.split(":", 1)[1].split(":", 1)[0]
    name = str(row.get("displayedName") or site_id or fdn)
    if not name:
        return None
    site = str(row.get("siteName") or row.get("site") or "")
    return NetworkElement(
        name=name,
        system_ip=site_id,
        ne_type=str(row.get("chassisType") or row.get("neType") or ""),
        version=str(row.get("version") or row.get("softwareVersion") or ""),
        site=site,
        group=site or "LIVE",
        admin=_state(row.get("administrativeState")),
        oper=_state(row.get("operationalState")),
        chassis_mac=str(row.get("macAddress") or row.get("chassisMac") or ""),
    )


def _port_name_from_inventory(row: dict[str, Any]) -> str:
    displayed = str(row.get("displayedName") or "")
    for tok in displayed.replace("Port", " ").split():
        if "/" in tok:
            return tok
    fdn = str(row.get("objectFullName") or "")
    return fdn.rsplit(":", 1)[-1].replace("port-", "") if fdn else displayed or "?"


def _card_slot_from_fdn(fdn: str) -> str:
    for part in fdn.split(":"):
        if part.startswith("cardSlot-"):
            return part.replace("cardSlot-", "")
    return "0"


def _cards_from_inventory(port_rows: list[dict[str, Any]], card_rows: list[dict[str, Any]]) -> list[Card]:
    types: dict[str, str] = {}
    for row in card_rows:
        fdn = str(row.get("objectFullName") or "")
        slot = _card_slot_from_fdn(fdn)
        types[slot] = str(row.get("specificType") or row.get("displayedName") or "card")
    by_slot: dict[str, list[Port]] = {}
    for row in port_rows:
        fdn = str(row.get("objectFullName") or "")
        slot = _card_slot_from_fdn(fdn)
        mode = str(row.get("mode") or "access").lower()
        if "network" in mode:
            mode = "network"
        else:
            mode = "access"
        encap = str(row.get("encapType") or "")
        by_slot.setdefault(slot, []).append(
            Port(
                name=_port_name_from_inventory(row),
                mode=mode,
                encap=encap or ("null" if mode == "network" else "dot1q"),
                admin=_state(row.get("administrativeState")),  # type: ignore[arg-type]
                oper=_state(row.get("operationalState")),  # type: ignore[arg-type]
                speed=str(row.get("actualSpeed") or row.get("speed") or ""),
                description=str(row.get("displayedName") or ""),
            )
        )
    cards: list[Card] = []
    for slot in sorted(by_slot, key=lambda s: (len(s), s)):
        ports = by_slot[slot]
        down = any(p.oper == "down" for p in ports)
        ctype = types.get(slot, "line-card")
        cards.append(
            Card(
                slot=slot,
                card_type=ctype,
                equipped=ctype,
                admin="up",
                oper="degraded" if down else "up",
                ports=ports,
            )
        )
    return cards


def _topology_as_from_row(row: dict[str, Any], kind: str) -> TopologyAs | None:
    fdn = str(row.get("objectFullName") or "")
    if not fdn:
        return None
    return TopologyAs(
        fdn=fdn,
        kind=kind,
        displayed_name=str(row.get("displayedName") or ""),
        as_number=str(row.get("asNumber") or ""),
        as_type=str(row.get("asType") or ""),
        description=str(row.get("description") or ""),
        bgp_topology_enabled=str(row.get("bgpTopologyEnabled") or ""),
        igp_admin_domain=str(row.get("igpAdminDomain") or ""),
        cpaa_pointers=_bits(row.get("cpaaPointers")),
    )


def _cpaa_from_row(row: dict[str, Any]) -> Cpaa | None:
    fdn = str(row.get("objectFullName") or "")
    if not fdn:
        return None
    return Cpaa(
        fdn=fdn,
        displayed_name=str(row.get("displayedName") or ""),
        router_id=str(row.get("routerId") or ""),
        bgp_as=str(row.get("bgpAsPointer") or ""),
        protocol_record=_bits(row.get("protocolRecord")),
        protocol_events=_bits(row.get("protocolEventTypes")),
        rib_retrieve=str(row.get("bgpRibInfoLastRetrieveTime") or "0"),
        rt_retrieve=str(row.get("bgpVpnv4RoutTargetLastRetrieveTime") or "0"),
        admin=_state(row.get("administrativeState")),
        oper=_state(row.get("operationalState")),
    )


def _rib_info_from_row(row: dict[str, Any], svc: Service) -> BgpRibInfo | None:
    fdn = str(row.get("objectFullName") or "")
    if not fdn:
        return None
    kind = str(row.get("type") or row.get("displayedName") or "rib").lower()
    key = str(
        row.get("nextHop")
        or row.get("peer")
        or row.get("originatorId")
        or row.get("med")
        or row.get("localPref")
        or row.get("displayedName")
        or fdn.rsplit(":", 1)[-1]
    )
    return BgpRibInfo(
        svc_id=svc.svc_id,
        fdn=fdn,
        kind=kind,
        key=key,
        as_number=str(row.get("asNumber") or ""),
        num_routes=_int_field(row, "numRoutes", "numberOfRoutes") or 0,
    )


_STATS_SKIP = {
    "objectfullname",
    "monitoredobjectpointer",
    "timecaptured",
    "id",
    "displayedname",
    "siteid",
    "class",
    "actionmask",
    "self",
    "children",
}


def _stats_from_row(row: dict[str, Any], pointer: str) -> list[StatSample]:
    collected = _parse_time(row.get("timeCaptured") or row.get("collected"))
    fdn = str(row.get("monitoredObjectPointer") or pointer)
    samples: list[StatSample] = []
    for key, raw in row.items():
        if key.lower() in _STATS_SKIP:
            continue
        if isinstance(raw, dict):
            continue
        text = str(raw).strip()
        if text == "" or text in {"true", "false"}:
            continue
        try:
            value = float(text)
        except ValueError:
            continue
        unit = "bytes" if "octet" in key.lower() else "pkts" if "pkt" in key.lower() or "packet" in key.lower() else ""
        samples.append(StatSample(object_fdn=fdn, counter=key, value=value, unit=unit, collected=collected))
    return samples


def _port_from_pointer(pointer: str) -> str:
    if not pointer:
        return ""
    if ":" in pointer:
        return pointer.rsplit(":", 1)[-1]
    return pointer


def _saps_from_rows(svc: Service, rows: list[dict[str, Any]]) -> list[AccessInterface]:
    saps: list[AccessInterface] = []
    for row in rows:
        fdn = str(row.get("objectFullName") or "")
        name = str(row.get("displayedName") or fdn.rsplit(":", 1)[-1])
        pointer = str(row.get("portPointer") or "")
        port = _port_from_pointer(pointer) or name
        site_id = str(row.get("siteId") or "")
        if not site_id and fdn.startswith(svc.fdn + ":"):
            rest = fdn[len(svc.fdn) + 1 :]
            site_id = rest.split(":", 1)[0].rstrip("%")
        saps.append(
            AccessInterface(
                svc_id=svc.svc_id,
                site_id=site_id,
                name=name,
                port=port,
                layer="l3" if svc.svc_type == "vprn" else "l2",
                primary_ipv4=str(row.get("primaryIPv4Address") or ""),
                admin=_state(row.get("administrativeState")),
                oper=_state(row.get("operationalState")),
                mgr_id=svc.mgr_id,
                port_pointer=pointer,
            )
        )
    return saps


def _vr_cidr(row: dict[str, Any]) -> str:
    addr = str(
        row.get("ipAddress")
        or row.get("address")
        or row.get("ipv4Address")
        or row.get("primaryIPv4Address")
        or ""
    ).strip()
    if not addr:
        return ""
    if "/" in addr:
        return addr
    plen = _int_field(row, "prefixLength", "prefixLen", "addressPrefixLength")
    if plen is None:
        return addr
    return f"{addr}/{plen}"


def _static_from_row(row: dict[str, Any], svc: Service, site_id: str) -> StaticRoute | None:
    prefix = str(
        row.get("destPrefix")
        or row.get("prefix")
        or row.get("ipPrefix")
        or row.get("destination")
        or ""
    ).strip()
    if not prefix:
        fdn = str(row.get("objectFullName") or "")
        tail = fdn.rsplit(":", 1)[-1]
        if tail and tail not in {"%", ""}:
            prefix = tail.replace("-", "/", 1)
    if not prefix:
        return None
    nh = str(
        row.get("nextHop")
        or row.get("nextHopAddress")
        or row.get("nexthop")
        or ""
    ).strip()
    return StaticRoute(
        svc_id=svc.svc_id,
        site_id=site_id,
        prefix=prefix,
        next_hop=nh,
        admin=_state(row.get("administrativeState")),
    )


def _subscriber_id(row: dict[str, Any]) -> int | None:
    raw = row.get("subscriberId") or row.get("objectFullName") or ""
    text = str(raw).replace("subscriber:", "")
    try:
        return int(text)
    except ValueError:
        return None


def _int_field(row: dict[str, Any], *keys: str) -> int | None:
    for key in keys:
        raw = row.get(key)
        if raw is None or raw == "":
            continue
        try:
            return int(str(raw).strip())
        except (TypeError, ValueError):
            continue
    return None


def _mgr_id_from_fdn(fdn: str) -> int | None:
    prefix = "svc-mgr:service-"
    if not fdn.startswith(prefix):
        return None
    head = fdn[len(prefix) :].split(":", 1)[0]
    try:
        return int(head)
    except ValueError:
        return None


def _service_from_row(row: dict[str, Any], svc_type: str, subscriber_id: int) -> Service | None:
    fdn = str(row.get("objectFullName") or "")
    mgr_id = _int_field(row, "id") or _mgr_id_from_fdn(fdn)
    svc_id = _int_field(row, "serviceId")
    if svc_id is None:
        svc_id = mgr_id
    if mgr_id is None:
        mgr_id = svc_id
    if svc_id is None or mgr_id is None:
        return None
    admin = _state(row.get("administrativeState"))
    oper = _state(row.get("operationalState"))
    return Service(
        svc_id=svc_id,
        name=str(row.get("displayedName") or f"{svc_type}-{svc_id}"),
        svc_type=svc_type,
        customer="",
        customer_id=subscriber_id,
        sites=[],
        description=str(row.get("description") or ""),
        admin=admin,
        oper=oper,
        mgr_id=mgr_id,
    )


def _state(value: Any) -> str:
    text = str(value or "up").lower()
    if "down" in text or text in {"disabled", "nopresent"}:
        return "down"
    if "degrad" in text:
        return "degraded"
    return "up"
