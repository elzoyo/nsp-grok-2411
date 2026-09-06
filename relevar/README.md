# relevar

Inventario **pre-migración** de un CE Cisco (un hop). SSH por la VRF **OPE**, parsers de show, `inventario.json`, informe y un `.drawio` con tapa, **vista frontal de rack** y una hoja por VRF.

Contrato: [`docs/MEMORIA_RELEVAR.md`](../docs/MEMORIA_RELEVAR.md).

No es un NMS. No salta a vecinos. No llama NFM-P.

## Uso

```bash
pip install -e ".[relevar]"   # netmiko para SSH live
export SSH_PASS='...'
relevar operador@10.0.6.250 --out ./nodos
relevar operador@10.0.6.250 --vrf OPE,CORP,TRA --out ./nodos
```

Sin SSH, regenerar desde raw ya colectado (tests / reproceso):

```bash
relevar --from-raw tests/fixtures/relevar/raw --out /tmp/nodo-ejemplo --ip 10.0.6.250
```

Password: `SSH_PASS` o `RELEVAR_SSH_PASS`, si no hay env pide prompt. Nunca se guarda.

## Salida

```text
nodos/<hostname>_<ip>_<YYYYMMDD>/
  raw/                 # un archivo por show
  inventario.json      # modelo canónico
  relevamiento.md
  nodo.drawio          # páginas Nodo, Rack, VRF-*
```

`inventario.json` regenera MD y draw.io sin volver a SSH.

Hoja **Rack**: frente 42U (U inferida). Tendido local puerto a puerto. Salidas a otros sitios = patchera FO-FC, nunca una nube.

## Exit

| código | causa |
|--------|--------|
| 0 | ok |
| 2 | SSH falló |
| 3 | no hay VRFs parseables |
| 4 | OSPF no se correlacionó a if física |

## MVP

Cisco IOS / IOS-XE. NX-OS y Nokia 7705 quedan fuera. Overlay `rack.yaml` con U reales: fase posterior.
