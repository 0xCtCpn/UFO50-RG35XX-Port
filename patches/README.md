# MiaUI / RG35XX runtime patches

These are applied, in filename order, by the `Dockerfile` to the pristine
vendored `runtime/` (the UFO 50 Miyoo Mini port's Butterscotch fork, base
Butterscotch `92ed6b8` / `onion-v2`). Every patch is generated from exact
anchor edits (`tools/gen_patches.py` for 001-003, `tools/gen_trace_patch.py`
for 004), so `git apply` failing is a hard build error - no silent fallbacks.

| Patch | Why |
|---|---|
| `001-miau-fallback-mapping.patch` | The shipped `gamecontrollerdb.txt` has no Linux entry for MiaUI's `RG35XX Gamepad` (17 buttons, 0 axes, 0 hats), so the pad reports connected but no game button ever goes down. Adds a fallback map using the probe-verified layout: buttons 0..9 = A,B,X,Y,L1,R1,L2,R2,Select,Start (identity), dpad at sdl **13..16** (one slot lower than GP standard), and sdl **12 = volume-down** is never referenced. Hat/axis fallbacks are kept for Garlic-era pads. |
| `002-joyname-cache.patch` | `SDL_JoystickName()` in SDL 1.2 is *not* cached - each call opens the device and issues `EVIOCGNAME`/`JSIOCGNAME` ioctls (~50 ms on this pad). It was called in the per-frame event loop, halving the framerate (30 -> 15 fps). Cache the name per slot; re-query only when the `SDL_Joystick*` handle changes. |
| `003-exit-cursor.patch` | fbcon draws a stub mouse cursor that never moves and sits in a corner: hide it at init and in `platformSetCursor`. Add a clean exit path - **Select (sdl 8) + Start (sdl 9)** held together (and `SDLK_MENU`, where forwarded) make `platformHandleEvents()` return true, so the main loop exits, `launch.sh`'s trap restores the CPU governor and minui returns to the menu. |
| `004-loop-trace.patch` | Six `logError("TRACE: ...")` markers around events/step/swap for the first 8 frames of the main loop. These are the **verified shipping build**: without them the RG35XX intermittently hung between `Runner: Room loaded: rmInit` and the first frame (watchdog kill, `exit code 137`/SIGTERM); with them the same binary runs at a steady 30 FPS and exits cleanly. The markers are harmless (stderr, first 8 frames only) and are kept because removing them reproduces the hang. This points to a timing-sensitive startup race on this device. |

## Regenerating

`tools/gen_patches.py` expects a **pristine** copy of `runtime/` that is a git
repo whose HEAD is the unmodified upstream source:

```
python3 tools/gen_patches.py <path-to-pristine-runtime> <path-to-patches-dir>
```

It edits `src/backends/sdl1.c` with exact, uniqueness-checked anchors, emits
one `git diff` per logical change, stages each, and finally resets the tree
back to pristine (so the generator is idempotent). Verify the whole chain:

```
git -C <pristine-runtime> apply --check patches/001-*.patch
git -C <pristine-runtime> apply --check patches/002-*.patch
git -C <pristine-runtime> apply --check patches/003-*.patch
git -C <pristine-runtime> apply --check patches/004-*.patch
```

`tools/gen_trace_patch.py` uses the same exact-anchor approach for `loop.c`
(`python3 tools/gen_trace_patch.py <pristine-runtime> <patches-dir>`).
