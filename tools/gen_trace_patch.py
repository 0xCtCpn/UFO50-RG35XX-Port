#!/usr/bin/env python3
"""Generate optional 004-loop-trace.patch (diagnostic only, NOT in patches/)."""
import pathlib, subprocess, sys

SRC = pathlib.Path(sys.argv[1]).resolve()   # pristine runtime copy (git repo)
OUT = pathlib.Path(sys.argv[2]).resolve()
LOOP = SRC / "src" / "loop.c"

def run(*a):
    return subprocess.run(a, cwd=SRC, check=True, text=True, capture_output=True)

def once(text, old, new, label):
    n = text.count(old)
    if n != 1:
        raise SystemExit(f"ANCHOR FAIL {label}: {n}")
    return text.replace(old, new, 1)

t = LOOP.read_text(encoding="utf-8")

# Counter just inside the main loop.
t = once(t,
         "        while (true) {\n            if (runner->shouldExit || shouldWindowClose) {",
         "        static int traceFrame = 0;\n"
         "        while (true) {\n"
         "            if (traceFrame < 8) logError(\"TRACE: frame=%d enter\\n\", traceFrame);\n"
         "            if (runner->shouldExit || shouldWindowClose) {",
         "enter")

t = once(t,
         "                Runner_step(runner);\n",
         "                if (traceFrame < 8) logError(\"TRACE: frame=%d pre-step\\n\", traceFrame);\n"
         "                Runner_step(runner);\n"
         "                if (traceFrame < 8) logError(\"TRACE: frame=%d post-step\\n\", traceFrame);\n",
         "step")

t = once(t,
         "                        platformSwapBuffers();\n",
         "                        if (traceFrame < 8) logError(\"TRACE: frame=%d pre-swap\\n\", traceFrame);\n"
         "                        platformSwapBuffers();\n"
         "                        if (traceFrame < 8) logError(\"TRACE: frame=%d post-swap\\n\", traceFrame);\n",
         "swap")

t = once(t,
         "            lastFrameTime = nowNanos();\n            if (perfEnabled && waitStarted) {",
         "            if (traceFrame < 8) { logError(\"TRACE: frame=%d end\\n\", traceFrame); traceFrame++; }\n"
         "            lastFrameTime = nowNanos();\n            if (perfEnabled && waitStarted) {",
         "end")

LOOP.write_text(t, encoding="utf-8", newline="\n")
run("git", "add", "-A")
patch = run("git", "diff", "--cached", "--binary").stdout
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "004-loop-trace.patch").write_text(patch, encoding="utf-8", newline="\n")
print(f"wrote {OUT / '004-loop-trace.patch'} ({len(patch)} bytes)")
run("git", "reset", "--hard", "HEAD")
