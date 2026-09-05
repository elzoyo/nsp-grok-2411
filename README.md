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

Rama `arquitectura-nsp-grok`, al día con `origin`. CLI usable; el live cubre solo una parte del árbol.

**Hecho**

- Shell `user@IP>`, login OAuth2, fallback a lab, `--debug`, timeout 60 s, Ctrl-C con mensaje y cierre.
- Navegación cliente → VPRN/VPLS/Epipe → servicio.
- Live SAM-O: `subscr.Subscriber`, servicios por `subscriberPointer`, `*.Site`, SAP L3/L2.
- `id` (NFM-P, FDN) separado de `serviceId` (NE, prompt).
- UI de ayuda / errores / contexto en español; comandos en inglés.
- Lab local completo (customers, sites, SAP, SDP, LSP, alarmas, RT, estáticas, BGP, MAC).
- Tests: `.\.venv\Scripts\python.exe -m pytest -q`

## Pendientes

**Live, queries SAM-O ya documentadas que el CLI aún no pide**

| Dato | Query | Estado |
|---|---|---|
| Máscara de SAP (`rtr.VirtualRouterIpAddress`) | 7 | no |
| Rutas estáticas (`rtr.StaticRoute`) | 8 | carpeta lab vacía en vivo |
| BGP del VR (`bgp.Site`) | 9 | igual |
| RT / next-hops CPAM | 15–16 | igual |
| RIB BGP | 13–14 | vacío en ese NFM-P; no es `show router` |

**Live, en el árbol pero sin HTTP:** SDP bindings, túneles, LSPs, alarmas `fm`, stats, MAC VPLS.

**Producto:** primera instancia solo lectura — no crear servicios. MPLS create/shutdown sigue siendo del lab.

**Deuda chica:** SAP live usa el nombre como puerto; falta `portPointer`.

Lo más natural a continuación, según las queries SAM-O: VPRN en vivo (máscara, estáticas, BGP del VR y RT/NH).

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
