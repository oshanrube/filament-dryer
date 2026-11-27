#!/bin/sh
# Render the v2 touch screens on this computer (needs a C/C++ compiler and Python with Pillow).
# LVGL comes from the PlatformIO download: run `pio run -e dryer-1roll-v2` once first.
#   sh tools/ui_sim/run.sh [output-dir]
set -e
FW=$(cd "$(dirname "$0")/../.." && pwd)
OUT=${1:-$FW/.pio/ui_sim}
LV=$FW/.pio/libdeps/dryer-1roll-v2/lvgl
mkdir -p "$OUT/obj"
FLAGS="-DLV_CONF_SKIP -DLV_MEM_CUSTOM=1 -DLV_SPRINTF_USE_FLOAT=1 -DLV_FONT_MONTSERRAT_20=1 -DLV_FONT_MONTSERRAT_28=1 -DLV_FONT_MONTSERRAT_48=1 -I$LV -I$LV/src -I$FW/lib/DryerCore/src"
if [ ! -f "$OUT/obj/lvgl.a" ]; then
  for f in $(find "$LV/src" -name '*.c'); do
    o="$OUT/obj/$(echo "$f" | sed "s|$LV/||; s|/|_|g").o"
    cc -c -O1 -w $FLAGS "$f" -o "$o"
  done
  ar rcs "$OUT/obj/lvgl.a" "$OUT"/obj/*.o
fi
c++ -std=gnu++17 -O1 -Wall $FLAGS "$FW/tools/ui_sim/sim.cpp" "$FW/lib/DryerCore/src/DryerCore.cpp" "$OUT/obj/lvgl.a" -o "$OUT/sim"
cd "$OUT" && ./sim
python3 "$FW/tools/ui_sim/ppm2png.py" "$OUT"
