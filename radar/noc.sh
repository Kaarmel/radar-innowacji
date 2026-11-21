#!/bin/zsh
# Pełny przebieg: lista domen → źródła → wpisy → liczby → widok. Wznawialny: źródła i wpisy pomijają gotowe pozycje.
# Każdy przebieg pisze do nowego logu (nadpisywanie logu w folderze Google Drive bywa zawodne).
set -e
cd "$(dirname "$0")"
L=../dane/logi/noc_$(date +%Y%m%d_%H%M%S).txt
mkdir -p ../dane/logi
{
  python3 wejscie.py
  python3 zrodla.py ../dane/wejscie.csv ../dane/zrodla.csv
  python3 wpisy.py ../dane/zrodla.csv ../dane/wpisy.jsonl 10
  python3 liczby.py > /dev/null
  python3 widok.py ../dane/wpisy.jsonl
  echo "KONIEC $(date)"
} >> "$L" 2>&1
