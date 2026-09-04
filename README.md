# NSP-Grok 24.11

Shell de gestión **IP/MPLS** inspirado en Nokia **NFM-P / NSP Classic Management 24.11**.

No replica la GUI Java. El operador inicia sesión y queda en una consola tipo [Grok 4.6](https://x.ai): prompt, **slash commands**, barra de estado, Tab-complete y el árbol de navegación NFM-P montado como un filesystem.

Basado en:

- *NSP NFM-P Classic Management User Guide 24.11* (3HE-20021) — árbol, forms, MPLS, túneles, servicios
- *NSP System Administrator Guide 24.11 Issue 11* (3HE-20030) — usuarios locales, UAC, span of control, password policy, lockout
- *NSP NFM-P Statistics Management Guide 24.11* (3HE-20019) — estadísticas de performance

## Requisitos

Python 3.11+ (Windows, Linux o macOS).

```powershell
cd C:\Users\elzoy\Code\nsp-grok-2411
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

## Arranque

```powershell
nsp-grok
# o
python -m nsp_grok
```

Login interactivo. Usuarios de laboratorio:

| usuario    | password    | rol             | span                         |
|------------|-------------|-----------------|------------------------------|
| `admin`    | `Nokia1234!` | administrator   | ALL                          |
| `operator` | `Nokia1234!` | operator (rw)   | ALL                          |
| `noc`      | `Nokia1234!` | fault-manager   | solo METRO-BA (Buenos Aires) |
| `viewer`   | `Nokia1234!` | monitor (ro)    | ALL, solo lectura            |

Política de password NSP 24.11: ≥10 caracteres, mayúscula, minúscula, dígito, especial. Lockout a los 5 fallos.

Al login intenta **OAuth2** contra `https://<host>/rest-gateway/rest/api/v1/auth/token`. Si el NSP responde, `customers` / VPRN / VPLS / Epipe salen de `POST /nfmpv3service/api/v3/find`. Si el server no está, cae al lab local.

```powershell
.\.venv\Scripts\python.exe -m nsp_grok --host 172.24.80.28 --debug
```

`--debug` imprime cada request (método, URL, headers con token tachado, body). `--offline` fuerza el lab sin HTTP.

## Qué ves después del login

Prompt estilo equipo de red (`usuario@IP_NSP>`). La IP por defecto es `172.24.80.28` (`--host` o `NSP_HOST`). Navegación anidada tipo **Python Fire** / CLI SR OS: cada nombre entra al contexto.

```
admin@172.24.80.28> customers
admin@172.24.80.28>customers> 12
admin@172.24.80.28>customers>12> vprn
admin@172.24.80.28>customers>12>vprn> 100
admin@172.24.80.28>customers>12>vprn>100> sites
admin@172.24.80.28>customers>12>vprn>100>sites> exit
```

O en una línea: `customers 12 vprn 100`. `exit` sube un nivel, `logout` cierra sesión, `?` lista.

Flujo de solo lectura: **customer → VPRN/VPLS/Epipe → servicio → relacionados**.

## Comandos

| comando | efecto |
|---|---|
| `customers` · `12` · `vprn` · `100` | entra al contexto (Fire) |
| `?` / `ls` | lista hijos de este contexto |
| `info` / `show` | detalle del objeto actual |
| `exit` / `exit all` | sube un nivel / vuelve a root |
| `logout` | cierra la sesión |

## Modo no interactivo

```powershell
python -m nsp_grok -u admin -p Nokia1234! --host 172.24.80.28 -c "customers 12 vprn 100" -c "?" -c "logout"
```

## Lab

Lab: 4 customers (12 Banco Nación, 20 Telecom Mayorista, 33 Puerto Rosario, 44 Gobierno Salta), servicios VPRN/VPLS/Epipe con sites/SAP/SDP, 8 NEs, LSPs y alarmas.

Todo vive en memoria: no habla con un NFM-P real. El siguiente paso natural es cablear el XML/REST API de NSP 24.11 detrás de los mismos comandos.

## Tests

```powershell
pytest -q
```
