# MEMORIA DESCRIPTIVA — herramienta `relevar`

Documento de arranque para Grok Build. Contexto, decisiones y contrato del MVP.
Fecha de corte: 2026-09-05 (rev. vista de rack). Idioma de trabajo: español (Uruguay / UTE).

Si una sesión nueva solo puede leer un archivo, que sea este.

---

## 1. Para qué existe esto

Hay nodos de red todavía **no migrados a MPLS**. Cada nodo es un predio: uno o más equipos L3 y una serie de L2 aguas abajo.

El L3 típico es un **router/switch Cisco multi-VRF**. Las VRF habituales:

| VRF  | Rol típico                         |
|------|------------------------------------|
| OPE  | Operación / gestión del predio     |
| CORP | Corporativa                        |
| TRA  | Tráfico / transporte de servicios  |
| DIS  | Distribución                       |
| TELF | Telefonía                          |

Cada VRF es un **cliente lógico**. En la red MPLS destino ese cliente se materializa como **VPRN Nokia** con el mismo nombre/identificador de cliente.

Objetivo de `relevar`: conectar por SSH al CE Cisco **por la red OPE** (gestión de nodos no migrados), aprender el estado real del predio y dejar inventario + diagramas para diseñar la migración:

```
PE MPLS Nokia  -->  CE Cisco del nodo  -->  L2 / intermediarias  -->  resto del predio
```

No es un NMS. No es un crawler de toda la LAN. Es un **inventario pre-migración de un hop (el CE)** que responde, por VRF:

1. En qué interfaces físicas y lógicas vive.
2. Qué VLAN / subif / SVI / Port-Channel la transporta.
3. Quiénes son vecinos CDP/LLDP en esas interfaces.
4. Quiénes son intermediarias OSPF (RID, IP, if física, if lógica, área, costo, estado).
5. Qué prefijos / estáticas / HSRP / NAT hay, para no perder alcance al pasar a VPRN.
6. Cómo se ve el **frente del rack**: equipos del predio, tendidos locales entre ellos y salidas a otros sitios terminadas en patchera de fibra FC.

---

## 2. Contexto de plataforma ya conocido (mismo proyecto)

Trabajo paralelo sobre NFM-P / NSP / CPAM. No forma parte del MVP de `relevar`, pero el inventario tiene que ser **compatible** con ese mundo.

| Dato | Valor |
|------|--------|
| NFM-P | 172.24.80.21 |
| NE 7705 en análisis | 10.251.121.250 |
| CPAA | network:10.251.243.250:cpaa — IP 172.24.80.31 |
| IGP | tpgy-mgr:name-UTE-AS-0 (UTE, asNumber 0) |
| BGP AS | tpgy-mgr:AS-65000 |
| VPRN 10 | svc-mgr:service-1 (id=1, serviceId=10), RT/RD 65000:10, site en el 7705 up/up, cliente subscriber:10 / Red_Ope |
| VPRN 110 | svc-mgr:service-8, cliente subscriber:110 |
| VPLS 5110 / 5112 | svc-mgr:service-25 / service-27 |
| API find | POST /nfmpv3service/api/v3/find — respuesta XML, comodín `%` |
| Catálogo de queries | `artifacts/samo_v3_find_queries.txt` |
| CPAM | RT/NH VPNv4 (no BgpRibInfo); protocolRecord CPAA solo ospf+ospfTe |

El 7705 ya es PE MPLS. `relevar` apunta a los **Cisco CE / nodos legacy** que todavía se gestionan por OPE y cuyas VRF hay que subir como VPRN a ese tipo de PE.

Fase posterior (fuera de MVP): cruzar el inventario Cisco con sites VPRN NFM-P para marcar “ya migrado” vs “pendiente”.

---

## 3. Contrato del CLI

```text
relevar user@10.0.6.250
relevar user@10.0.6.250 --vrf OPE,CORP,TRA
relevar user@10.0.6.250 --out ./nodos/10.0.6.250
```

- Target = IP de gestión en **OPE**.
- Auth: `SSH_PASS` / clave / prompt. Nunca persistir passwords en el repo ni en la salida.
- Un run = un CE. No saltar a vecinos en el MVP.
- Idempotente, de minutos, sin `show tech-support` ni LSDB OSPF completa.
- Exit ≠ 0 si no hay VRFs parseables, SSH falla, o OSPF no se puede correlacionar.

Plataforma MVP: Cisco IOS / IOS-XE. Detectar con `show version`. NX-OS y Nokia SR/7705 quedan como drivers posteriores.

---

## 4. Fases y comandos (fuente de verdad del relevamiento)

Ejecutar en este orden. Guardar **siempre** el raw de cada show.

### Fase 0 — Identidad

- `show version`
- `show inventory`
- `show running-config | include hostname`
- `show ip domain-name` / `show hosts`
- `show clock`
- `show users` (no bloquear si falla)
- `show ip ssh`

Directorio de salida: `{hostname}_{ip}_{YYYYMMDD}/`.

### Fase 1 — Instancias de ruteo

- `show vrf` / `show ip vrf`
- `show vrf detail`
- `show ip vrf interfaces`
- `show running-config | section vrf definition` (o `ip vrf` en IOS clásico)
- `show ip protocols`
- `show ip protocols vrf <VRF>`

Si no hay VRF, tratar `default` como instancia. OPE se documenta igual que el resto (también migra a VPRN).

### Fase 2 — Interfaces físico + lógico

- `show interfaces description`
- `show ip interface brief`
- `show ip interface brief vrf <VRF>`
- `show interfaces status`
- `show etherchannel summary` / `show port-channel summary`
- `show vlan brief`
- `show interfaces trunk`
- `show running-config | section interface`
- `show interfaces <if>` solo de las if relevantes (no todas)

Tabla canónica:

```text
VRF | if_fisica | if_logica | vlan | ip/mask | estado | descripcion | bundle
```

`if_logica` ejemplos: `Gi1/0/1.110`, `Vlan110`, `Po1.20`.
Esa fila es el **SAP candidato** del VPRN.

### Fase 3 — Vecinos L2 (CDP / LLDP)

- `show cdp neighbors`
- `show cdp neighbors detail`
- `show lldp neighbors`
- `show lldp neighbors detail`
- `show cdp interface` si hace falta

Correlación: puerto local CDP × tabla Fase 2 → VRF(s) donde “cae” el vecino.
Trunk compartido = un objeto L2 referenciado en varias hojas VRF, no duplicar como si fueran L3 distintos.

### Fase 4 — Intermediarias OSPF (núcleo)

Por cada VRF con OSPF:

- `show ip ospf` / `show ip ospf vrf <VRF>`
- `show ip ospf neighbor` / `... vrf <VRF>`
- `show ip ospf neighbor detail` / `... vrf <VRF>`
- `show ip ospf interface brief` / `... vrf <VRF>`
- `show ip ospf interface` / `... vrf <VRF>`
- `show ip ospf database` (resumen; no LSDB completa)
- `show running-config | section router ospf`

Registro obligatorio por vecino OSPF:

```text
vrf
process_id
router_id_local
neighbor_rid
neighbor_ip
estado                # FULL / 2WAY / ...
area
if_logica             # donde corre OSPF
if_fisica             # padre o Port-Channel
vlan
costo
network_type          # broadcast / p2p / p2mp
hostname_vecino       # si CDP/LLDP/ARP lo resuelve
```

### Fase 5 — Rutas y servicios (informe, no diagrama)

- `show ip route vrf <VRF> summary`
- `show ip route vrf <VRF>`
- `show ip route vrf <VRF> ospf`
- `show ip route vrf <VRF> static`
- `show ip bgp vpnv4 vrf <VRF> summary` si aplica
- `show standby brief` / `show vrrp brief`
- `show ip nat translations` / `show ip nat statistics`
- `show ip pim vrf <VRF> neighbor`

TELF y CORP son los que más sorpresas traen (HSRP, PIM, helpers DHCP, NAT).

### Fase 6 — L2 de contexto en el CE

- `show spanning-tree summary`
- `show mac address-table count`
- `show ip arp vrf <VRF>`  → cierra OSPF IP → MAC → puerto cuando no hay CDP

### Fase 7 — Running de evidencia

- `show running-config` → `raw/`
- opcional `show startup-config` para drift

### Prohibido en el primer disparo

- `show tech-support`
- LSDB OSPF completa
- `show logging` entero
- walk SNMP masivo
- SSH recursivo a vecinos

---

## 5. Modelo de datos de salida

```text
nodos/<hostname>_<ip>_<YYYYMMDD>/
  raw/                 # CLI crudo, un archivo por comando
  inventario.json      # modelo canónico (fuente para todo lo demás)
  relevamiento.md      # informe humano
  nodo.drawio          # tapa + una página por VRF + vista frontal de rack
```

`inventario.json` debe poder regenerar MD y draw.io sin volver a SSH.

Entidades mínimas:

- `nodo`: hostname, ip_ope, plataforma, ios, uptime, inventario físico
- `rack`: nombre (default `RACK-1`), unidades (42), lado (`frente`), origen_posicion (`inferida`|`manual`)
- `equipo_rack[]`: hostname, rol (CE|L2|otro), plataforma, ru_inicio, ru_alto, faceplate (puertos frontales conocidos)
- `patchera[]`: id (`ODF-1`, `ODF-2`, …), tipo `FO-FC`, ru_inicio, n_conectores (12/24/48), puertos usados
- `conexion[]`: ver sección 6.1 (local vs exterior)
- `vrf[]`: nombre, rd, rt, ifs, protocolos
- `interfaz[]`: fisica, logica, vlan, vrf, ip, mask, estado, desc, bundle, trunk_vlans
- `vecino_l2[]`: proto (cdp|lldp), if_local, if_remota, hostname, ip_mgmt, plataforma
- `ospf_process[]`: vrf, process_id, router_id, areas
- `ospf_neighbor[]`: ver registro Fase 4
- `ruta_resumen[]`: vrf, origen (C/S/O/B/…), count
- `estatica[]`, `hsrp_vrrp[]`, `nat_flag`, `pim_neighbor[]`
- `huecos[]`: OSPF sin CDP, trunk sin descripción, VRF sin IGP, if down con vecino histórico, uplink sin sitio remoto parseable, posición U inferida

---

## 6. Draw.io

Formato `.drawio` (XML mxGraph), importable en diagrams.net. Generar por código, sin GUI.

Páginas obligatorias, en este orden:

- Página 0 `Nodo`: CE + lista de VRFs + uplinks / bundles.
- Página 1 `Rack`: vista **frontal** del rack del predio (ver 6.1).
- Páginas `VRF-OPE`, `VRF-CORP`, `VRF-TRA`, `VRF-DIS`, `VRF-TELF`, más las que existan.

En cada hoja VRF:

- Caja CE con hostname.
- Una caja por intermediaria OSPF: hostname / RID / IP.
- Link etiquetado: `Gi1/0/24.110  VLAN110  area 0  cost 10  FULL`.
- Vecinos solo-CDP (L2) en **otro color**; no confundirlos con L3.
- Port-Channel como un objeto, no N líneas sueltas.
- No volcar la tabla de ruteo al diagrama.
- Un uplink a otro sitio no se dibuja como nube suelta: se anota “ver Rack / ODF-x puerto n”.

### 6.1 Vista frontal de rack

Entregable de campo, no un diagrama lógico. Tiene que parecerse a lo que un técnico ve parado frente al gabinete.

#### Qué se dibuja

- Un gabinete de 42U visto de **frente** (escala U a la izquierda, 1 arriba / 42 abajo o al revés, pero consistente; default: U1 abajo, U42 arriba).
- Cada equipo descubierto del predio como **frente de equipo** (alto en U según plataforma: router 1–2U, switch 1U, ODF 1U). Hostname + modelo en el faceplate.
- Los **puertos usados** del CE (y de L2 si hay dato) marcados en el frente, no solo el nombre del chasis.
- **Conexiones locales**: tendido entre equipos del mismo nodo (CE ↔ switch de piso, CE ↔ otro L3 del predio, stack, Port-Channel entre cajas locales). Cable dibujado de puerto a puerto por el frente o por el costado del rack, etiqueta `if_local ↔ if_remota`.
- **Conexiones exteriores** (intermediarias hacia **otros sitios**): no se dibuja el equipo remoto dentro del rack. Terminan en **una o más patcheras de fibra con conectores FC** (ODF). Cada conector FC usado lleva:
  - sitio / nombre de la intermediaria remota
  - interfaz local que sale a esa FO
  - VRF principal si se conoce
- Varias FO al mismo sitio remoto = varios FC en la misma patchera, no un solo “tronco” anónimo.
- Si hay más de un destino o se satura una bandeja, agregar `ODF-2`, `ODF-3`… debajo o encima, nunca un cloud.

#### Clasificación de cada enlace (obligatoria)

| Clase | Criterio | Dibujo |
|-------|----------|--------|
| `local` | Vecino CDP/LLDP cuyo hostname/plataforma es equipo del mismo predio (otro switch/router visto desde el CE, misma OPE de gestión cuando se pueda inferir) | Cable equipo ↔ equipo |
| `exterior` | Vecino OSPF o descripción de interfaz que nombra **otro sitio**, o uplink FO/SFP sin vecino L2 local | Cable equipo ↔ conector FC en patchera, label = nombre del sitio/intermediaria |
| `desconocida` | Hay interfaz up / SFP / descripción vacía y no hay CDP ni OSPF | FC o puerto en gris + hueco en el informe |

Heurística de nombre de sitio remoto, en este orden: descripción de interfaz (`show interfaces description`), hostname CDP si no es local, hostname/RID del vecino OSPF. No inventar un sitio si no hay texto: `SITIO-DESCONOCIDO` + hueco.

#### Qué no sabe el SSH (y cómo no mentir)

El CLI no da la unidad U real ni el número de puerto de la patchera física. En el MVP:

- Orden **inferido** de arriba hacia abajo: patcheras FO → CE L3 → L2 del predio → holgura.
- `ru_inicio` queda `inferida`. Si más adelante existe un overlay manual (`rack.yaml` / campos en `inventario.json`), ese overlay gana y `origen_posicion=manual`.
- Puertos FC de la patchera se numeran 1…N en el dibujo; el mapeo puerto-ODF real es editable. Lo que sí es obligatorio acertar es **qué sale del predio y hacia qué nombre de intermediaria/sitio**.

#### Convenciones gráficas

- Rack: rectángulo 19", rieles, numeración U.
- Equipo L3 (CE): frente oscuro, puertos en una o dos filas según `show inventory` / módulos.
- Equipo L2 local: frente distinto (otro relleno), mismo lenguaje de puertos.
- Patchera FO: bandeja 1U con grilla de conectores **FC** (cuadrado pequeño + collarín). Usado = relleno + label; vacío = outline.
- Cobre local: línea continua. FO local (si hay): línea con hash. FO exterior: línea hasta el FC, no más allá del ODF.
- No mezclar esta hoja con las cajas lógicas de VRF. La hoja `Rack` es física; las hojas `VRF-*` son de ruteo.

#### Datos mínimos por conexión en `inventario.json`

```text
id
clase                 # local | exterior | desconocida
medio                 # cobre | fo
conector_remoto       # fc | rj45 | sfp | desconocido
if_local
if_remota             # si se conoce
equipo_local
equipo_remoto         # hostname local, o null si exterior
sitio_remoto          # solo clase exterior
patchera_id           # ODF-n si exterior
patchera_puerto       # 1..N inferido
vrf
origen                # cdp | lldp | ospf | descripcion | sfp
```

---

## 7. Stack acordado

| Pieza | Elección |
|-------|----------|
| Lenguaje | Python 3 |
| SSH | netmiko (Cisco IOS / IOS-XE) |
| Parseo | ntc-templates / TextFSM + parsers propios para `vrf detail` y OSPF |
| Modelo | dataclasses → inventario.json |
| Diagrama | plantilla draw.io + XML |
| CLI | typer o click |
| Secretos | env + prompt |

Orden interno del binario:

1. Parsear `user@host`, abrir SSH por OPE.
2. Fase 0 identidad.
3. Fase 1 VRFs (`--vrf` filtra si vino).
4. Fases 2–6, persistiendo raw.
5. Correlacionar: VRF → if lógica → if física/Po → VLAN → CDP → OSPF neighbor → ARP.
6. Clasificar conexiones `local` / `exterior` / `desconocida` y armar `equipo_rack[]` + `patchera[]`.
7. Emitir JSON + MD + `.drawio` (incluye hoja `Rack`).
8. Exit code según huecos críticos.

---

## 8. MVP vs después

### MVP (construir ahora)

Un hop. Un CE Cisco. N hojas draw.io (tapa + Rack + una por VRF). CLI `relevar user@ip`.
Parsers: `show vrf`, `show ip vrf interfaces`, `show interfaces description`, `show cdp neighbors detail`, `show ip ospf neighbor`, `show ip ospf interface`.
Vista frontal de rack generada con posición U inferida, L2 locales por CDP y salidas a otros sitios como patchera(s) FO-FC.

### Fuera de MVP (no implementar en el primer build)

- Saltar por OPE a intermediarias CDP y repetir un subset.
- Multi-rack / overlay `rack.yaml` con U y puertos ODF reales relevados en sitio.
- Driver Nokia 7705 / SR.
- Cruce con NFM-P (`vprn.Vprn` / site) “ya tiene VPRN vs pendiente”.
- Sugerir SAP `port:vlan` y OSPF PE-CE listo para pegar en el PE.
- BGP PE-CE / NAT como módulos obligatorios (sí capturar raw si el comando existe; no bloquear el run si no hay BGP).

---

## 9. Decisiones ya tomadas

- El host del CLI es siempre la IP OPE del CE, no el PE Nokia.
- OPE se releva como VRF más; no se excluye por ser “solo gestión”.
- “Intermediaria” en el entregable = vecino OSPF correlacionado a if física + lógica. Los L2 por CDP son contexto, otro color en el diagrama.
- Un archivo draw.io con **varias páginas**, no un .drawio por VRF.
- Hoja `Rack` = frente físico del gabinete. Hojas `VRF-*` = ruteo. No mezclar.
- Enlaces a otros sitios = patchera FO con conectores FC + nombre de la intermediaria/sitio. Nunca una nube.
- Enlaces entre equipos del mismo predio = tendido local puerto a puerto.
- Posición U del MVP es inferida; no fingir que el CLI midió el rack. Overlay manual posterior pisa lo inferido.
- Raw de CLI se conserva; el informe no es un dump.
- No guardar secretos. No inventar topología si el parseo falla: anotar hueco.
- Compatibilidad futura con SAM-O / VPRN (RT 65000:X, subscriber:X) pero **cero dependencia** de NFM-P en el MVP.

---

## 10. Cómo debe comportarse Grok Build al implementar

1. Leer este archivo entero y `artifacts/samo_v3_find_queries.txt` solo como contexto de la red destino, no para llamar APIs.
2. Crear el paquete Python del CLI (nombre de proyecto `relevar`).
3. No pedir NFM-P, tokens ni acceso al 7705 para el MVP.
4. Incluir fixtures de `show` Cisco multi-VRF para testear parsers sin red.
5. Generar al menos un `.drawio` de ejemplo a partir de un inventario.json de fixture, **con hoja `Rack`**: CE + un L2 local + ODF-FC hacia dos sitios.
6. Código y tests bajo el árbol del proyecto; no dejar scripts sueltos al lado del entregable de un nodo.
7. Documentar uso en un README breve del paquete: env vars, ejemplo de invocación, layout de salida.

Arranque preferido de implementación:

1. Esqueleto CLI + conexión netmiko.
2. Colector de shows (Fases 0–4 primero).
3. Parsers + `inventario.json` (incluye `conexion[]`, `equipo_rack[]`, `patchera[]`).
4. `relevamiento.md`.
5. Generador `nodo.drawio` (páginas lógicas + vista frontal de rack).

---

## 11. Ejemplo de invocación y resultado esperado

```bash
export SSH_PASS='...'
relevar operador@10.0.6.250 --out ./nodos
```

Resultado mínimo aceptable:

- SSH ok al Cisco por OPE.
- Lista de VRFs (OPE/CORP/TRA/DIS/TELF u otras).
- Por cada VRF con OSPF: vecinos con if física + lógica + VLAN.
- `relevamiento.md` legible por un ingeniero de campo.
- `nodo.drawio` que abre en diagrams.net con tapa, hoja `Rack` y una hoja por VRF.
- En `Rack`: frente de equipos, tendidos locales y una o más patcheras FO-FC con las intermediarias a otros sitios nombradas en los conectores.

Eso es el corte de “MVP listo”. Lo que no esté en las secciones 3–8 no es alcance de este build.
