#!/usr/bin/env python3
"""Headless simulation test for the installed ``achilles`` command.

This runs the *real* simulator: the process enters ``UniverseClass::MainLoop()``,
spawns the requested organisms and food, evolves them frame by frame and draws
every frame through the OSMesa offscreen GL backend.  A windowless SDL video
driver (``SDL_VIDEODRIVER=dummy``) supplies the software surface.

The run is deterministic and bounded: a 4x4 world with a fixed starting
population and a low target FPS, stopped with SIGTERM once a few simulation
seconds have elapsed.  Assertions are made on the process output and on the
fact that it survived the render loop instead of crashing.
"""
import os
import signal
import subprocess
import sys
import time

RESULTS = []


def check(condition, label):
    ok = bool(condition)
    RESULTS.append((ok, label))
    print(f"  [{'ok' if ok else 'fail'}] {label}")
    return ok


def report():
    executed = len(RESULTS)
    failed = sum(1 for ok, _ in RESULTS if not ok)
    print(f"test_simulation: {executed} executed, {failed} failed")
    return 1 if failed else 0


def main():
    exe = sys.argv[1]

    # 4x4 world, 2 food blocks, a single starting organism (values taken from
    # the upstream README's suggested invocation, scaled down), 10 FPS.
    target_fps = 10
    args = [exe, "-x", "4", "-z", "4", "-f", "2", "1", "--fps", str(target_fps)]
    env = {**os.environ, "SDL_VIDEODRIVER": "dummy", "SDL_AUDIODRIVER": "dummy"}

    proc = subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
        cwd=os.path.dirname(exe) or ".",
    )

    # The simulator prints a frame-rate line every 5 seconds; give it time for
    # at least three of them, then ask it to quit.
    time.sleep(16)
    alive_at_stop = proc.poll() is None
    if alive_at_stop:
        proc.send_signal(signal.SIGTERM)

    try:
        out, _ = proc.communicate(timeout=20)
    except subprocess.TimeoutExpired:
        proc.kill()
        out, _ = proc.communicate()

    print("---- simulation output ----")
    print(out.strip())
    print("---------------------------")

    # Reaching the frame-rate report at all means the OpenGL class was
    # constructed successfully: its constructor creates the OSMesa context and
    # calls exit(2) on failure, before MainLoop() can print anything.
    check(alive_at_stop, "simulator was still running after 16s (main loop alive)")
    check("Unable to" not in out, "no SDL/GL initialization error")
    check("Unable to initialize SDL" not in out, "SDL video subsystem initialized")
    check("Unable to create OSMesa context" not in out, "OSMesa offscreen context created")
    check("Unable to make OSMesa context current" not in out, "OSMesa context became current")
    if "Unable to" in out:
        for line in out.splitlines():
            if "Unable to" in line:
                print(f"       error line: {line.strip()}")

    frames = [line for line in out.splitlines() if line.startswith("Frames per second:")]
    check(len(frames) >= 2, f"main loop rendered frames (FPS lines: {len(frames)})")

    fps_values = []
    for line in frames:
        try:
            fps_values.append(float(line.split(":")[-1].strip()))
        except ValueError:
            pass
    check(bool(fps_values), "frame-rate values are parseable")
    # The pacing loop sleeps to hold the requested target; a value far below it
    # would mean frames are being dropped, far above it that the delay is gone.
    check(
        bool(fps_values) and all(v > 0 for v in fps_values),
        f"simulation actually progressed (max FPS: {max(fps_values) if fps_values else 0})",
    )
    check(
        bool(fps_values) and all(v <= target_fps * 1.5 for v in fps_values),
        f"frame pacing honours --fps {target_fps} (max {max(fps_values) if fps_values else 0})",
    )
    # The last window is a full 5s of steady-state rendering, so it must be
    # close to the target rather than merely non-zero.
    check(
        bool(fps_values) and fps_values[-1] >= target_fps * 0.5,
        f"steady-state frame rate is near the target ({fps_values[-1] if fps_values else 0})",
    )

    # Graceful termination: SIGTERM must not leave a crash behind.
    check(
        proc.returncode is not None and proc.returncode >= 0,
        f"process terminated by signal handling, not a crash (exit={proc.returncode})",
    )
    check(
        proc.returncode not in (-signal.SIGSEGV, -signal.SIGABRT, -signal.SIGBUS),
        "no segmentation fault / abort during rendering",
    )

    return report()


if __name__ == "__main__":
    sys.exit(main())
