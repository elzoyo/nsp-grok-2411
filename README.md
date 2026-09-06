# NSP-Grok 24.11

Shell de gestión **IP/MPLS** inspirado en Nokia **NFM-P / NSP Classic Management 24.11**.

No replica la GUI Java. El operador inicia sesión y queda en una consola: prompt `usuario@IP_NSP>`, comandos anidados tipo Fire / SR OS, slash commands, Tab-complete y barra de estado.

Alcance de esta instancia: **solo lectura**. Clientes primero (`subscr.Subscriber`), después solo **VPRN / VPLS / Epipe**, detalle del servicio y objetos relacionados. No crea servicios.

## Arranque

Python 3.11+. En PowerShell **no** uses `Activate.ps1` (suele fallar por execution policy). Llamá al intérprete del venv:

```powershell
cd C:\Users\elzoy\Code\nsp-grok-2411
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m nsp_grok --host 172.24.80.28
```

Flags: `--debug` (imprime cada HTTP), `--offline` (lab sin red), `-u` / `-p`, `-c` (batch).

Login: OAuth2 contra `https://<host>/rest-gateway/rest/api/v1/auth/token`. Si el NSP responde, `customers` / VPRN / VPLS / Epipe salen de `POST /nfmpv3service/api/v3/find`. Si no, cae al lab local.

Usuarios de laboratorio: `admin` / `operator` / `noc` / `viewer`, password `Nokia1234!`.

```
admin@172.24.80.28> customers
admin@172.24.80.28>customers> 12
admin@172.24.80.28>customers>12> vprn 100
```

`?` lista, `info` muestra el objeto, `exit` sube, `logout` / Ctrl-C cierra. `help` está en español; los comandos quedan en inglés.

`serviceId` es el ID del NE (el que se navega, p. ej. `vprn 10`). `id` es el interno NFM-P y arma el FDN `svc-mgr:service-<id>`.

## Estado actual

Rama `arquitectura-nsp-grok`. CLI usable. Live cubre cliente → servicio → sites/SAP/SDP, VPRN (máscara, estáticas, BGP, RT/NH) y túnel/LSP/alarmas/MAC VPLS.

**Hecho**

- Shell `user@IP>`, login OAuth2, fallback a lab, `--debug`, timeout 60 s, Ctrl-C con mensaje y cierre.
- Navegación cliente → VPRN/VPLS/Epipe → servicio.
- Live SAM-O: `subscr.Subscriber`, servicios por `subscriberPointer`, `*.Site`, SAP L3/L2 (`portPointer`).
- VPRN live: máscara (`rtr.VirtualRouterIpAddress`), estáticas, `bgp.Site`, RT CPAM y next-hops (query 16).
- Live SDP binding (`vprn/vpls/epipe.SdpBinding`) al entrar al servicio.
- Live `svt.Tunnel` (por SDP id), `mpls.DynamicLsp`, `fm.AlarmObject` (FDN del servicio) y MAC VPLS.
- Live CPAM: queries 10–14 (Cpaa, AS IGP, AS BGP, RIB/RT). Stats on-demand (`timeCaptured`).
- `id` (NFM-P, FDN) separado de `serviceId` (NE, prompt).
- UI de ayuda / errores / contexto en español; comandos en inglés.
- Lab local completo (customers, sites, SAP, SDP, LSP, alarmas, RT, estáticas, BGP, MAC).
- Tests: `.\.venv\Scripts\python.exe -m pytest -q` (Windows) o `.venv/bin/python -m pytest -q` (macOS)

## Pendientes

**Live, queries SAM-O ya documentadas que el CLI aún no pide**

| Dato | Query | Estado |
|---|---|---|
| Máscara de SAP (`rtr.VirtualRouterIpAddress`) | 7 | live al entrar al VPRN |
| Rutas estáticas (`rtr.StaticRoute`) | 8 | live (`network:<NE>:vprn-<serviceId>:%`) |
| BGP del VR (`bgp.Site`) | 9 | live (config, no RIB) |
| RT CPAM (`topology.BgpRoutesRouteTarget`) | 15 | live; NH count en el RT |
| Next-hops por RT | 16 | live (`topology.BgpRoutesNextHop`; ignora 0.0.0.0) |
| AS IGP | 11 | live `topology.AutonomousSystem` cabecera (`children: ""`, sin LSDB) |
| AS BGP | 12 | live `topology.BgpAutonomousSystem` cabecera |
| RIB BGP | 10, 13–14 | live completo: CPAA, BgpRibInfo (FDN RT), BgpRibInfoValue + BgpMonitoredPrefix; no dump global |

**Live stats:** `stats <fdn>` en vivo hace find de `InterfaceAdditionalStatsLogRecord` (u otras) con `monitoredObjectPointer` + `between timeCaptured` (15 min) y `children: ""`. Sin política MIB o sin logs, muestra el lab. No usamos findToFile ni dump.

**Producto:** primera instancia no crea servicios. MPLS create/shutdown sigue en lab. Query 17 es comando explícito `cpaa record bgp [fdn]` (write, live); no corre al login.

**Deuda chica:** `port` es el último componente de `portPointer`; el FDN completo se muestra. `siteId` del NH CPAM se etiqueta como CPAA.

Clases no documentadas en el archivo SAM-O (`svt.Tunnel`, `fm.AlarmObject`, MAC, stats log) usan `children: ""` y filtro; si la clase no existe, no cierran la sesión.

## Retomar la sesión Grok Build

Snapshot en `.grok-session/` (ID `01a06e01-5cac-7511-bc2a-a0dd4373fd76`).

**macOS**

```bash
gh repo clone elzoyo/nsp-grok-2411 -- -b arquitectura-nsp-grok
cd nsp-grok-2411
chmod +x .grok-session/restore.sh
./.grok-session/restore.sh
grok login
grok --resume 01a06e01-5cac-7511-bc2a-a0dd4373fd76
```

**Windows**

```powershell
gh repo clone elzoyo/nsp-grok-2411 -- -b arquitectura-nsp-grok
cd nsp-grok-2411
.\.grok-session\restore.ps1
grok --resume 01a06e01-5cac-7511-bc2a-a0dd4373fd76
```

## Referencias

`docs/REFERENCES.md` — User Guide, Admin Guide, Statistics, XML API, Service Management, catálogo REST.
