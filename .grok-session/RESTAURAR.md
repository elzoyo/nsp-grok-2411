# Retomar esta sesión Grok Build

ID: `01a06e01-5cac-7511-bc2a-a0dd4373fd76`

Grok no sincroniza chats entre PCs. Esta carpeta es un snapshot para `grok --resume`.

En la otra máquina, desde la raíz del repo:

```powershell
.\.grok-session\restore.ps1
cd (repo)
grok --resume 01a06e01-5cac-7511-bc2a-a0dd4373fd76
```

Hace falta `grok login` en esa PC. No incluye `auth.json` ni logs de terminal.
