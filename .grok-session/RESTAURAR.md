# Retomar esta sesión Grok Build

ID: `01a06e01-5cac-7511-bc2a-a0dd4373fd76`

Grok no sincroniza chats entre PCs. Esta carpeta es un snapshot para `grok --resume`.

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

Hace falta `grok login` en esa máquina. No incluye `auth.json` ni logs de terminal.
