# Relevamiento NOD-PAYSANDU-CE

- IP OPE: `10.0.6.250`
- Plataforma: IOS  IOS 17.09.04a
- Uptime: 12 weeks, 3 days, 4 hours, 21 minutes
- Rack: RACK-1 (42U, posición inferida)

## VRFs

| VRF | RD | RT | Protocolos | Interfaces |
|-----|----|----|------------|------------|
| CORP | 65000:110 | — | ipv4 | Gi1/0/24.110 |
| OPE | 65000:10 | — | ipv4 | Gi1/0/1.10, Vlan10 |
| TRA | 65000:200 | — | ipv4 | Gi1/0/23.200 |

## Interfaces (SAP candidatos)

| VRF | if_fisica | if_logica | vlan | ip/mask | estado | descripcion | bundle |
|-----|-----------|-----------|------|---------|--------|-------------|--------|
| OPE | Gi1/0/1 | Gi1/0/1.10 | 10 | 10.0.6.250 | up | OPE gestion predio | — |
| OPE | Vlan10 | Vlan10 | 10 | 10.0.6.1 | up | OPE SVI | — |
| CORP | Gi1/0/24 | Gi1/0/24.110 | 110 | 10.110.1.2 | up | CORP a MERCEDES | — |
| TRA | Gi1/0/23 | Gi1/0/23.200 | 200 | 10.200.1.2 | up | TRA a SALTO | — |
| OPE | Gi1/0/48 | Gi1/0/48 | — | — | up | SW-PAYSANDU-L2 | — |
| — | Gi1/0/1 | Gi1/0/1 | — | — | up | OPE SVI padre | — |
| — | Gi1/0/23 | Gi1/0/23 | — | — | up | FO a SALTO TRA | — |
| — | Gi1/0/24 | Gi1/0/24 | — | — | up | FO a MERCEDES CORP | — |

## Vecinos L2 (CDP/LLDP)

| proto | if_local | if_remota | hostname | ip_mgmt | plataforma |
|-------|----------|-----------|----------|---------|------------|
| cdp | Gi1/0/48 | Gi1/0/1 | SW-PAYSANDU-L2 | 10.0.6.20 | cisco WS-C2960-24TT-L |

## Intermediarias OSPF

| vrf | RID vecino | IP | estado | área | if_logica | if_fisica | vlan | costo | tipo | hostname |
|-----|------------|----|--------|------|-----------|-----------|------|-------|------|----------|
| CORP | 10.1.1.1 | 10.110.1.1 | FULL | 0 | Gi1/0/24.110 | Gi1/0/24 | 110 | 10 | point_to_point | — |
| TRA | 10.2.2.2 | 10.200.1.1 | FULL | 0 | Gi1/0/23.200 | Gi1/0/23 | 200 | 20 | point_to_point | — |

## Rutas (resumen)

| VRF | origen | count |
|-----|--------|-------|
| CORP | S | 360 |
| CORP | O | 240 |

## Saltos a vecinos (consultados)

| equipo | IP | rol | estado | objetivo |
|--------|----|-----|--------|----------|
| SW-PAYSANDU-L2 | 10.0.6.20 | l2 | ok | completar rack y L2 del predio (subset: version, VLAN, CDP, descripciones; sin LSDB ni show tech) |

## Conexiones (rack)

| clase | medio | if_local | if_remota | equipo_remoto / sitio | ODF | origen |
|-------|-------|----------|-----------|------------------------|-----|--------|
| local | cobre | Gi1/0/48 | Gi1/0/1 | SW-PAYSANDU-L2 | — | cdp |
| exterior | fo | Gi1/0/24 | — | MERCEDES | ODF-1:1 | ospf |
| exterior | fo | Gi1/0/23 | — | SALTO | ODF-1:2 | ospf |

## Huecos

- `u_inferida`: posición U del rack inferida (no medida en sitio)
- `ospf_sin_cdp`: CORP vecino 10.1.1.1 en Gi1/0/24.110 sin CDP/LLDP
- `ospf_sin_cdp`: TRA vecino 10.2.2.2 en Gi1/0/23.200 sin CDP/LLDP
- `vrf_sin_igp`: VRF OPE sin OSPF
- `vecino_de_vecino`: SW-PAYSANDU-L2 ve a AP-PAYSANDU-01 por cdp; no se salta en cadena
