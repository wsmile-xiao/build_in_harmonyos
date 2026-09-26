#!/usr/bin/env python3
"""Consumer tests for the installed LBreakout2 commands, data, and startup.

LBreakout2 has no --version/--help mode and no upstream test suite: the game
prints its banner, initializes SDL and drops into its menu, quitting only on
user input. With the SDL dummy video/audio drivers the whole startup path
(SDL_Init including the joystick subsystem, the 640x480x16 software display,
PNG data loading, the SDL_mixer audio device) runs without a physical
display, so the process must still be alive when the timeout expires. Any
early exit (missing shared library, STK_ABORT, missing/corrupt game data)
fails this test.
"""

import os
import subprocess
import sys

GAME_SECONDS = 12
REQUIRED_DATA = (
    os.path.join("gfx", "loading.png"),
    os.path.join("gui_theme", "font.png"),
    os.path.join("gui_theme", "widget_wallpaper.png"),
)


def check_installed(bindir, datadir):
    """The package must ship both upstream programs and the game data."""
    for name in ("lbreakout2", "lbreakout2server"):
        path = os.path.join(bindir, name)
        if not os.path.isfile(path):
            raise RuntimeError("missing installed command: {}".format(path))
    if not os.path.isdir(datadir):
        raise RuntimeError("missing installed game data directory: {}".format(datadir))
    for relative in REQUIRED_DATA:
        path = os.path.join(datadir, relative)
        if not os.path.isfile(path):
            raise RuntimeError("missing installed game data: {}".format(path))


def run_game(bindir):
    """Run the real game headless and require it to reach the menu loop."""
    environment = dict(os.environ)
    environment["SDL_VIDEODRIVER"] = "dummy"
    environment["SDL_AUDIODRIVER"] = "dummy"
    environment.setdefault("HOME", os.path.expanduser("~"))
    game = os.path.join(bindir, "lbreakout2")
    try:
        completed = subprocess.run(
            [game],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=GAME_SECONDS,
            env=environment,
        )
    except subprocess.TimeoutExpired:
        return  # still running after the window: startup completed
    raise RuntimeError(
        "lbreakout2 exited early with code {}: stdout={!r} stderr={!r}".format(
            completed.returncode, completed.stdout, completed.stderr
        )
    )


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: test_commands.py <bindir> <datadir>")
    bindir, datadir = sys.argv[1], sys.argv[2]
    check_installed(bindir, datadir)
    run_game(bindir)
    print(
        "validated lbreakout2/lbreakout2server commands, installed game data, "
        "and headless game startup through the menu loop"
    )


if __name__ == "__main__":
    main()
