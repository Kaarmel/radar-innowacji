#!/usr/bin/env bash
# Cykliczna aktualizacja jednego źródła (uruchamiana przez timery systemd z vm.sh albo z crona).
# Użycie: wdrozenie/aktualizuj.sh mapadotacji|interreg|radon|radon_patenty|uprp|radar
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p dane/logi
log="dane/logi/aktualizacja-$1.log"
echo "== $(date -Iseconds) start $1" >> "$log"
case "$1" in
  radar) .venv/bin/python -m radar.cli radar --limit 300 --dni 180 >> "$log" 2>&1 ;;
  uprp) .venv/bin/python -m radar.cli pobierz uprp >> "$log" 2>&1 ;;
  mapadotacji|interreg|radon|radon_patenty) .venv/bin/python -m radar.cli pobierz "$1" --od-nowa >> "$log" 2>&1 ;;
  *) echo "nieznane źródło: $1" >&2; exit 2 ;;
esac
echo "== $(date -Iseconds) koniec $1" >> "$log"
