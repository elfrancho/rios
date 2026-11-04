#!/bin/bash
# Voz clonada de Pancho para el reel de los 30 mil seguidores (03/11/2026). VoiceStudio abierto en http://127.0.0.1:3900.
# Uso: bash festejo30k/voz/generar_voz.sh [bloque ...] -> festejo30k/voz/b<n>.wav
cd "$(dirname "$0")"
MOLDE=../../historias/animacion/voz_pancho/clon3/molde_largo.wav
REF="El río Paraná atraviesa una creciente extraordinaria que afecta a varias provincias del litoral argentino, con miles de evacuados y alertas vigentes. Este lunes dos de noviembre de dos mil veintiséis, la altura del río fue cinco metros veinte en el puerto de Santa Fe. Seguime y te mantengo informado."
B[1]="¿Sabés cómo nace una isla en el Paraná? Grano a grano. El río trae la arena, el agua se frena, y se forma un banco."
B[2]="Después llegan las plantas. Y con las plantas, la vida."
B[3]="Esta cuenta nació igual: grano a grano, ustedes la fueron armando. Hoy somos treinta mil. Gracias por ser parte de esta isla."
PEDIDOS=${@:-1 2 3}
for n in $PEDIDOS; do
  curl -s -m 1500 -X POST http://127.0.0.1:3900/generate -F "text=${B[$n]}" -F "language=Spanish" -F "seed=1" \
    -F "ref_audio=@$MOLDE" -F "ref_text=$REF" -o "b$n.wav"
  echo "b$n: $(ffprobe -v error -show_entries format=duration -of csv=p=0 b$n.wav) s"
done
echo listo
