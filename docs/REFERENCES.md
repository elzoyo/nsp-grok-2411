# Referencias NSP 24.11

Biblioteca oficial (Issue 13):  
https://documentation.nokia.com/nsp/24-11/libfiles/libcontents.html

Si algún HTML/PDF de esa lista no es accesible desde acá, pegarlo en el chat.

## Ya usadas en este proyecto

| Documento | Número | Uso |
|---|---|---|
| Classic Management User Guide | 3HE-20021-AAAC-TQZZA | Árbol, forms, MPLS, servicios |
| System Administrator Guide | 3HE-20030-AAAC-TQZZA Issue 11 | Usuarios, UAC, span, password |
| Statistics Management Guide | 3HE-20019-AAAC-TQZZA | Stats de performance |
| XML API Developer Guide | 3HE-20022-AAAC-TQZZA | SOAP, FDN, find, generic, fm, service |
| Service Management Guide | 3HE-20028-AAAC-TQZZA | Customer / Epipe=E-Line, VPLS=E-LAN, VPRN=L3 VPN |
| Catálogo REST vivo | `nsp-catalog.json` | `samo_*`, ServiceSupervision, FaultManagement |

## Modelo de navegación (solo lectura)

1. `subscr.Subscriber` — DN `subscriber:<id>`
2. Servicios del cliente: `vprn.Vprn` / `vpls.Vpls` / `epipe.Epipe` filtrados por `subscriberPointer`
3. Relacionados: `*.Site`, SAP (`L3AccessInterface` / `L2AccessInterface`), SDP binding (`svt`), LSP, alarmas (`fm`)
