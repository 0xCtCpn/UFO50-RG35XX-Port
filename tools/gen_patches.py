#!/usr/bin/env python3
"""Generate the MiaUI/RG35XX patches for the vendored UFO50 runtime.

Run against a pristine copy of the UFO50 `runtime/` tree that is a git repo
whose HEAD is the unmodified upstream source. Each logical change is written
as a separate patch via `git diff` against the staged state, so the diffs are
always well-formed git patches (no hand-written hunk headers).

    python3 gen_patches.py /path/to/pristine/runtime /path/to/patches
"""
import pathlib
import subprocess
import sys

SRC = pathlib.Path(sys.argv[1]).resolve()
OUT = pathlib.Path(sys.argv[2]).resolve()
SDL1 = SRC / "src" / "backends" / "sdl1.c"


def run(*args, check=True):
    return subprocess.run(args, cwd=SRC, check=check, text=True,
                          capture_output=True)


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"ANCHOR FAIL [{label}]: {count} occurrences, wanted 1")
    return text.replace(old, new, 1)


def stage_and_diff(name):
    # The index holds the previous logical state; `git diff` captures only
    # this change. Stage it afterwards so the next patch stays separate.
    patch = run("git", "diff", "--binary").stdout
    if not patch.strip():
        raise SystemExit(f"EMPTY PATCH: {name}")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(patch, encoding="utf-8", newline="\n")
    print(f"wrote {name} ({len(patch)} bytes)")
    run("git", "add", "-A")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    original = SDL1.read_text(encoding="utf-8")
    text = original

    # ---------------------------------------------------------------- 001
    fallback = r'''
/* MiaUI (RG35XX) fallback gamepad mapping. The shipped gamecontrollerdb.txt
 * has no Linux entry matching the gpio-keys "RG35XX Gamepad", so without this
 * the pad reports "connected" but every gp button stays false.
 *
 * Verified SDL1.2 joystick order on MiaUI v2.0.0 (17 buttons, 0 axes, 0 hats):
 *   0:A 1:B 2:X 3:Y 4:L1 5:R1 6:L2 7:R2 8:Select 9:Start 10:L3 11:R3
 *   12:VOL-DOWN(!) 13:dpup 14:dpdown 15:dpleft 16:dpright
 * The dpad sits ONE SLOT LOWER than GP standard order, and sdl button 12 is
 * the system volume key (must never be referenced by any game button).
 */
static void createFallbackMappings(void) {
    for (int i = 0; i < MAX_GAMEPADS; i++) {
        SDL_Joystick* joy = openJoysticks[i];
        if (!joy || joystickMappings[i].valid) continue;
        const char* jname = SDL_JoystickName(i);
        int nbtn = SDL_JoystickNumButtons(joy);
        int nax = SDL_JoystickNumAxes(joy);
        int nhat = SDL_JoystickNumHats(joy);
        GamepadMapping* m = &joystickMappings[i];
        memset(m, 0, sizeof(GamepadMapping));
        for (int k = 0; k < GP_BUTTON_COUNT; k++) {
            m->button_map[k] = -1;
            m->hat_map[k] = -1;
            m->hat_mask[k] = -1;
            m->axis_button_map[k] = -1;
            m->axis_button_sign[k] = 1.0f;
        }
        for (int k = 0; k < GP_AXIS_COUNT; k++) m->axis_map[k] = -1;

        /* 0..9 = A,B,X,Y,L1,R1,L2,R2,Select,Start (identity). */
        int idn = nbtn < 10 ? nbtn : 10;
        for (int k = 0; k < idn; k++) m->button_map[k] = k;
        m->max_button = idn > 0 ? idn - 1 : -1;

        /* This pad: gp 12..15 (dpup..dpright) <- sdl 13..16. */
        if (nbtn > 15) {
            m->button_map[12] = 13; /* gp dpup    <- sdl 13 (phys up)    */
            m->button_map[13] = 14; /* gp dpdown  <- sdl 14 (phys down)  */
            m->button_map[14] = 15; /* gp dpleft  <- sdl 15 (phys left)  */
            m->button_map[15] = 16; /* gp dpright <- sdl 16 (phys right) */
            m->max_button = 16;
        }
        /* Garlic-era pads (12 buttons / 6 axes / 1 hat) keep the old path. */
        if (nhat > 0) {
            m->max_hat = nhat - 1;
            m->hat_map[12] = 0; m->hat_mask[12] = SDL_HAT_UP;
            m->hat_map[13] = 0; m->hat_mask[13] = SDL_HAT_DOWN;
            m->hat_map[14] = 0; m->hat_mask[14] = SDL_HAT_LEFT;
            m->hat_map[15] = 0; m->hat_mask[15] = SDL_HAT_RIGHT;
        }
        if (nax > 1) {
            m->max_axis = nax - 1;
            m->axis_map[0] = 0;
            m->axis_map[1] = 1;
            m->axis_button_map[14] = 0; m->axis_button_sign[14] = -1.0f;
            m->axis_button_map[15] = 0; m->axis_button_sign[15] = 1.0f;
            m->axis_button_map[12] = 1; m->axis_button_sign[12] = -1.0f;
            m->axis_button_map[13] = 1; m->axis_button_sign[13] = 1.0f;
        }
        if (nax > 2) { m->axis_button_map[6] = 2; m->axis_button_sign[6] = 1.0f; }
        if (nax > 3) { m->axis_button_map[7] = 3; m->axis_button_sign[7] = 1.0f; }
        m->valid = true;
        logInfo("Gamepad: MiaUI fallback mapping for '%s' (slot %d) buttons=%d axes=%d hats=%d\n",
            jname ? jname : "(null)", i, nbtn, nax, nhat);
    }
}

'''
    anchor1a = "void platformSetWindowTitle(const char* title) {"
    text = replace_once(text, anchor1a, fallback + anchor1a, "001 insert")
    anchor1b = "    loadGamepadMappings();\n\n    fbWidth = reqW;"
    text = replace_once(text, anchor1b,
                        "    loadGamepadMappings();\n    createFallbackMappings();\n\n    fbWidth = reqW;",
                        "001 platformInit call")
    anchor1c = "    if (needsRemap) {\n        loadGamepadMappings();\n    }"
    text = replace_once(text, anchor1c,
                        "    if (needsRemap) {\n        loadGamepadMappings();\n        createFallbackMappings();\n    }",
                        "001 reset call")
    SDL1.write_text(text, encoding="utf-8", newline="\n")
    stage_and_diff("001-miau-fallback-mapping.patch")

    # ---------------------------------------------------------------- 002
    old2 = """            const char* name = SDL_JoystickName(slotIdx);
            if (name != NULL) {"""
    new2 = """            /* MiaUI perf fix: SDL 1.2's SDL_JoystickName() open()s the
             * device and issues EVIOCGNAME/JSIOCGNAME ioctls on EVERY call
             * (~50 ms on this keymatrix pad); we call it once per frame.
             * Cache the string per slot, refreshing only on joystick reopen. */
            static char joyNameCache[MAX_GAMEPADS][64];
            static SDL_Joystick* joyNameJoy[MAX_GAMEPADS];
            const char* name = NULL;
            if (joyNameJoy[slotIdx] != joy) {
                const char* n = SDL_JoystickName(slotIdx);
                if (n != NULL) {
                    strncpy(joyNameCache[slotIdx], n, sizeof(joyNameCache[slotIdx]) - 1);
                    joyNameCache[slotIdx][sizeof(joyNameCache[slotIdx]) - 1] = '\\0';
                } else {
                    joyNameCache[slotIdx][0] = '\\0';
                }
                joyNameJoy[slotIdx] = joy;
            }
            if (joyNameCache[slotIdx][0] != '\\0') name = joyNameCache[slotIdx];
            if (name != NULL) {"""
    text = replace_once(text, old2, new2, "002 joyname cache")
    SDL1.write_text(text, encoding="utf-8", newline="\n")
    stage_and_diff("002-joyname-cache.patch")

    # ---------------------------------------------------------------- 003
    old3a = "    SDL_EnableKeyRepeat(0, 0);\n\n    return true;"
    new3a = """    SDL_EnableKeyRepeat(0, 0);

    /* fbcon draws a stub mouse cursor that never moves and sits in a corner;
     * hide it for the whole session. */
    SDL_ShowCursor(SDL_DISABLE);

    return true;"""
    text = replace_once(text, old3a, new3a, "003 cursor init")

    old3b = """static void platformSetCursor(int32_t cursorType) {
    // SDL1.2 only supports showing/hiding
    SDL_ShowCursor(cursorType == GML_CR_NONE ? SDL_DISABLE : SDL_ENABLE);
}"""
    new3b = """static void platformSetCursor(int32_t cursorType) {
    /* SDL1.2 only supports showing/hiding. The GML game never uses a real
     * cursor and fbcon's stub sits in a corner: always hide it. */
    (void)cursorType;
    SDL_ShowCursor(SDL_DISABLE);
}"""
    text = replace_once(text, old3b, new3b, "003 cursor setter")

    old3c = """            case SDL_KEYDOWN:
                // SDL1.2 needs to manually intercept Alt+F4 to exit properly
                if (e.key.keysym.sym == SDLK_F4 && (e.key.keysym.mod & KMOD_ALT)) {
                    return true;
                }
                // During playback, suppress real keyboard input"""
    new3c = """            case SDL_KEYDOWN:
                // SDL1.2 needs to manually intercept Alt+F4 to exit properly
                if (e.key.keysym.sym == SDLK_F4 && (e.key.keysym.mod & KMOD_ALT)) {
                    return true;
                }
#ifdef SDLK_MENU
                /* Some firmware builds forward the hardware MENU key. */
                if (e.key.keysym.sym == SDLK_MENU) return true;
#endif
                // During playback, suppress real keyboard input"""
    text = replace_once(text, old3c, new3c, "003 menu key")

    old3d = """            case SDL_QUIT:
                return true;
        }
    }

    return false;
}"""
    new3d = """            case SDL_QUIT:
                return true;
        }
    }

    /* MiaUI has no OS quit path for ports: Select (sdl 8) + Start (sdl 9)
     * held together closes the game cleanly (launch.sh restores the CPU
     * governor and minui returns to the menu). */
    for (int i = 0; i < MAX_GAMEPADS; i++) {
        SDL_Joystick* exj = openJoysticks[i];
        if (exj && SDL_JoystickNumButtons(exj) > 9 &&
            SDL_JoystickGetButton(exj, 8) && SDL_JoystickGetButton(exj, 9))
            return true;
    }

    return false;
}"""
    text = replace_once(text, old3d, new3d, "003 exit combo")
    SDL1.write_text(text, encoding="utf-8", newline="\n")
    stage_and_diff("003-exit-cursor.patch")

    # Restore the pristine tree so the generator is idempotent.
    run("git", "reset", "--hard", "HEAD")
    run("git", "clean", "-fd")
    print("restored pristine runtime")


if __name__ == "__main__":
    main()
