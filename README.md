# UFO 50 - MiaUI (RG35XX) Port

UFO 50 on the original (non-H700) Anbernic RG35XX running MiaUI v2.0.0, using
the open-source Butterscotch GameMaker runner. Ported from
[Producdevity/ufo50-miyoo-mini-port](https://github.com/Producdevity/ufo50-miyoo-mini-port)
(v0.1.9, Miyoo Mini / Onion).

## Overview

This port runs the Windows release of UFO 50 on the original RG35XX through the
open-source Butterscotch runner. It draws at 30 FPS using the runner's software
renderer, plays audio through the handheld's system sound stack, and maps the
RG35XX controls to the game.

Needs MiaUI v2.0.0, the release zip, and **your own Windows copy of UFO 50**.
The game files are not included in this repo.

## Install

0. Get the port folder - either extract the `UFO50_MiaUI-release-v1.zip`
   release asset from GitHub, or use your own staged `out/UFO50.pak` - and
   prepare your Windows UFO 50 game files.
1. Extract the zip into `PORTS/` (MiaUI's ROMs partition is **EXT4**).
2. Copy the **contents** of your Windows UFO 50 folder into
   `/userdata/Ports/UFO50.pak/gamefiles/`. Keep `data.win`, **every**
   `audiogroup*.dat`, `textures/` (or `Textures/`), `fonts/` and `ext/`
   together. `data.win` must be directly inside `gamefiles/` - no extra
   folder, no ZIP. You do not need the Windows executable.
3. Safely eject, boot, go to **PORTS -> UFO50**. Startup reads the game files,
   so the first launch can take a little longer.
4. Use the game's own menu to quit, or hold **Select + Start** to exit cleanly
   (this restores the CPU clock and returns to minui).

## SD folder structure

```
Ports/
  UFO50.pak/                  # MiaUI pak folder
    launch.sh
    butterscotch
    libSDL-1.2.so.0
    libSDL-1.2.so.0.11.4
    gamecontrollerdb.txt
    LICENSE
    NOTICE.MiaUI
    README.md
    licenses/THIRD_PARTY.txt
    gamefiles/                # <- your Windows UFO 50 files go here
      data.win
      audiogroup_*.dat
      textures/
      fonts/
      ext/
    saves/                    # created on first launch
    debug.log                 # created on launch
```

## Controls

| Button | Action |
| --- | --- |
| D-pad | Move / select |
| A / Y | First action / confirm |
| B / X | Second action |
| L1 / R1, L2 / R2 | Shoulders / triggers |
| Start | Pause menu |
| Select | Back / menu |
| **Select + Start** (held) | Quit cleanly back to PORTS |

UFO 50 uses a 16:9 picture: on the 4:3 RG35XX screen there are black bars at
the top and bottom, which is normal. For scanlines use the game's
**Pause -> Settings -> Video Settings -> CRT Effect** (Soft / Hard; Off keeps
the normal picture).

## Build from source

Only needed if you change the runtime or want fresh binaries.

Prerequisites (Windows):

* Hardware virtualisation enabled in BIOS
* WSL 2
* Docker Desktop using the WSL 2 engine

Steps:

1. Open this folder and double-click `build.bat`.
2. Wait for it to finish. Success ends with `=== Built ===` and a listing of
   `out/`.
3. Fresh binaries land in `out/`: `butterscotch`, `libSDL-1.2.so.0`,
   `gamecontrollerdb.txt`.

`package-release.bat` then stages a clean, game-free `out/UFO50.pak` folder
that is ready to copy into `PORTS/`; it does not create a zip. The checks
reject a bundled `libasound*`, game data or `share/alsa`.

What the Dockerfile does:

* starts from `debian:bookworm` and installs the armhf cross compilers;
* cross-builds alsa-lib for ARM **first** (SDL 1.2 configure otherwise
  silently disables its ALSA driver, giving "No available audio device"),
  and hard-fails if the ALSA bootstrap string is absent from libSDL;
* cross-builds SDL 1.2.15 with fbcon + ALSA;
* applies `patches/*.patch` to the vendored pristine `runtime/` (any mismatch
  fails the build) and builds Butterscotch with `PLATFORM=cli BACKEND=sdl1
  AUDIO_BACKEND=sdl1`, software renderer only, WAD17 only;
* prints the binary's `INTERP` (want `/lib/ld-linux-armhf.so.3`) and its
  `NEEDED` libraries.

To install your own build, copy `out/butterscotch`, `libSDL-1.2.so.0*`,
`gamecontrollerdb.txt` and `launch.sh` into the SD card's `UFO50.pak/`, then
put your game files in `UFO50.pak/gamefiles/`.

## Debugging

`launch.sh` writes `debug.log` in the pak folder with startup messages, input
mapping, frame timings and errors. If the game will not start, check that all
game files are in `gamefiles/` (including every `audiogroup*.dat` and the
`textures`, `fonts` and `ext` folders). Hold Select + Start to quit cleanly.

If you encounter any other bugs feel free to submit debug.log on issues, or 
create a pull request for suggested fixes

## Credits

* [Producdevity](https://github.com/Producdevity/ufo50-miyoo-mini-port) - the
  original Miyoo Mini port and the UFO50-specific Butterscotch runtime.
* [cobaltgit / ButterscotchRunner](https://github.com/ButterscotchRunner/Butterscotch)
  - the Butterscotch GameMaker runner (AGPL-3.0, `onion-v2` / `92ed6b8` base).
* DSkywalk for [MiaUI](https://github.com/miaui-cfw/MiaUI-GPU-RG35XX).
* libsdl and ALSA upstreams for the cross-built dependencies.
* Mossmouth and the UFO 50 creators - the game itself (sold separately).

## License

AGPL-3.0 for the runner and this port's source (see `LICENSE`); port and
third-party notices are in `NOTICE.MiaUI`, `runtime/LICENSE` and
`licenses/THIRD_PARTY.txt`. No UFO 50
game assets are distributed. Corresponding source for release binaries is this
repo plus the `Dockerfile`/`build.bat` build instructions.
