#!/bin/sh
# MiaUI pak launcher - install to /userdata/Ports/UFO50.pak/launch.sh
# MiaUI ROMs is EXT4 only (no FAT32); the OS in /opt is read-only.
set -u
progdir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
cd "$progdir" || exit 1
HOME=$progdir
export HOME

# Never ship a bundled libasound.so* (see Dockerfile CMD): if a stale copy is
# present from a bad manual install, move it aside so it can never shadow the
# SYSTEM /usr/lib/libasound.so.2 via LD_LIBRARY_PATH (Undertale v1.0.0 bug).
if [ -e ./libasound.so ] || [ -e ./libasound.so.2 ] || [ -e ./libasound.so.2.0.0 ]; then
  mkdir -p ./libasound-disabled
  mv -f ./libasound.so ./libasound.so.2 ./libasound.so.2.0.0 ./libasound-disabled/ 2>/dev/null
fi

# butterscotch is glibc: SDL1's libasound dependency must resolve to the
# system libasound 1.2.10 + /etc/asound.conf (the only stack that works with
# MiaUI's atm7059link card). $progdir stays on LD_LIBRARY_PATH only so the
# bundled libSDL-1.2.so.0 is found. Never point ALSA at a bundled datadir.
export LD_LIBRARY_PATH="$progdir${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
unset ALSA_CONFIG_PATH
unset ALSA_CONFIG_DIR

# SDL1.2 + linux framebuffer is the only working video path here (the
# SGX544MP has no usable GBM/DRM/KMS from SDL). SDL_NOMOUSE is mandatory:
# fbcon refuses to init without a mouse device, which this pad does not have.
export SDL_VIDEODRIVER=fbcon
export SDL_FBDEV=/dev/fb0
export SDL_NOMOUSE=1
export SDL_AUDIODRIVER=alsa
# The runtime runs from gamefiles/; point it at the shipped controller DB.
export SDL_GAMECONTROLLERCONFIG_FILE="$progdir/gamecontrollerdb.txt"

# UFO50 runtime tuning (same profile proven on the Miyoo Mini Onion port).
export UFO50_VALIDATE_FILES=1
export UFO50_PLATFORM=miyoo
export UFO50_RENDER_FPS=30
export UFO50_TEXTURE_CACHE_MIB="${UFO50_TEXTURE_CACHE_MIB:-24}"
export UFO50_NATIVE_RESOLUTION=384x216
export UFO50_PERF_LOG="${UFO50_PERF_LOG:-1}"
# RG35XX fb0 is upright - do NOT set UFO50_ROTATE_180 (that is a Miyoo Mini
# panel quirk). 384x216 is scaled to a 640x480 screen with black bars top and
# bottom; the game's Pause -> Settings -> Video Settings -> CRT Effect adds
# scanlines if wanted.

mkdir -p "$progdir/saves"
{
  echo "=== UFO50 MiaUI launch (SW renderer, SDL1.2 fbcon) ==="
  cat /proc/fb
  cat /sys/class/graphics/fb0/virtual_size /sys/class/graphics/fb0/bits_per_pixel 2>&1
  ls -lh /dev/fb* /dev/dri/* 2>&1
  ls /dev/input/event* 2>&1
  ls -R /dev/snd 2>&1 | head -20
  head -n 5 /proc/meminfo 2>&1
  ls -lh ./butterscotch ./lib*.so* ./gamecontrollerdb.txt ./gamefiles/data.win 2>&1
} > "$progdir/debug.log" 2>&1

if [ ! -s "$progdir/gamefiles/data.win" ]; then
  echo "missing gamefiles/data.win - copy the Windows UFO 50 folder contents" >> "$progdir/debug.log"
  echo "  (data.win, every audiogroup*.dat, textures/, fonts/, ext/) into gamefiles/" >> "$progdir/debug.log"
  sleep 3
  exit 1
fi

# overclock.elf only raises scaling_max_freq; the governor stays 'userspace'
# at CPU_SPEED_MENU (504 MHz). Pin all cores to the performance governor at
# the full 1.488 GHz - UFO50's software renderer needs the headroom.
perf_mhz=${CPU_SPEED_PERF:-1488000}
if command -v overclock.elf >/dev/null 2>&1; then
  overclock.elf "$perf_mhz" 2>/dev/null
fi
for i in 0 1 2 3; do
  echo performance > /sys/devices/system/cpu/cpu$i/cpufreq/scaling_governor 2>/dev/null
done
restore_cpu() {
  for i in 0 1 2 3; do
    echo userspace > /sys/devices/system/cpu/cpu$i/cpufreq/scaling_governor 2>/dev/null
    echo 504000 > /sys/devices/system/cpu/cpu$i/cpufreq/scaling_setspeed 2>/dev/null
  done
}

game_pid=
watchdog_pid=
cleanup() {
  result=$?
  trap - EXIT INT TERM
  if [ -n "$watchdog_pid" ]; then
    kill -TERM "$watchdog_pid" 2>/dev/null
    wait "$watchdog_pid" 2>/dev/null
  fi
  if [ -n "$game_pid" ]; then
    kill -TERM "$game_pid" 2>/dev/null
    wait "$game_pid" 2>/dev/null
  fi
  restore_cpu
  exit "$result"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

cd "$progdir/gamefiles" || exit 1
# Heavy assets + 256 MB RAM: the lazy loads are essential. --window-size
# matches fb0; the runtime keeps its 384x216 logical framebuffer internally.
"$progdir/butterscotch" data.win \
  --renderer software \
  --lazy-rooms --lazy-textures --lazy-audio --load-type load-per-chunk \
  --window-size 640x480 \
  --save-folder "$progdir/saves" \
  --disable-log-colours \
  >> "$progdir/debug.log" 2>&1 &
game_pid=$!

# Watch startup only, never gameplay: the runtime logs
# "Startup: first frame presented" after its first displayed frame. The
# RG35XX is much slower than the Mini at parsing WAD17 and executing UFO50's
# ~1000 global init scripts, so the ceiling is generous and overridable:
#   UFO50_STARTUP_TIMEOUT=300 (seconds), or "off" to disable the watchdog.
startup_timeout=${UFO50_STARTUP_TIMEOUT:-240}
if [ "$startup_timeout" != off ]; then
  case "$startup_timeout" in
    ''|*[!0-9]*) startup_timeout=240 ;;
  esac
  [ "$startup_timeout" -lt 30 ] && startup_timeout=240
fi
if [ "$startup_timeout" != off ]; then
(
  trap - EXIT INT TERM
  elapsed=0
  while [ "$elapsed" -lt "$startup_timeout" ]; do
    if grep -q '^Startup: first frame presented$' "$progdir/debug.log" || \
       ! kill -0 "$game_pid" 2>/dev/null; then exit 0; fi
    sleep 1
    elapsed=$((elapsed + 1))
  done
  if grep -q '^Startup: first frame presented$' "$progdir/debug.log" || \
     ! kill -0 "$game_pid" 2>/dev/null; then exit 0; fi
  echo "Startup timed out after $startup_timeout seconds" >> "$progdir/debug.log"
  kill -TERM "$game_pid" 2>/dev/null || exit 0
  sleep 2
  kill -KILL "$game_pid" 2>/dev/null || true
) &
watchdog_pid=$!
fi

status=0
wait "$game_pid" || status=$?
game_pid=
kill -TERM "$watchdog_pid" 2>/dev/null
wait "$watchdog_pid" 2>/dev/null
watchdog_pid=
if grep -q '^Startup timed out' "$progdir/debug.log"; then
  echo "Startup stalled - recopy all game files, including audiogroup*.dat," >> "$progdir/debug.log"
  echo "textures/, fonts/ and ext/ into gamefiles/." >> "$progdir/debug.log"
fi
echo "exit code $status" >> "$progdir/debug.log"
exit "$status"
