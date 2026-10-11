#!/bin/bash
cd -- "$(dirname -- "$0")" || exit 1
python3 launch.py
result=$?
if [ "$result" -ne 0 ]; then
  echo "Avvio non riuscito. Consulta la guida GUIDA-ITALIANA.md."
  read -r -p "Premi Invio per chiudere…"
fi
exit "$result"
