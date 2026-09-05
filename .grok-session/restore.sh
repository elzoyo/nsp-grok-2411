#!/usr/bin/env bash
set -euo pipefail
id="01a06e01-5cac-7511-bc2a-a0dd4373fd76"
here="$(cd "$(dirname "$0")" && pwd)"
src="$here/$id"
repo="$(cd "$here/.." && pwd)"
enc="$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1], safe=''))" "$repo")"
dst="$HOME/.grok/sessions/$enc/$id"
if [[ ! -d "$src" ]]; then
  echo "No está el snapshot: $src" >&2
  exit 1
fi
mkdir -p "$dst"
cp -R "$src/." "$dst/"
echo "Sesión copiada a $dst"
echo "Desde el repo: grok --resume $id"
