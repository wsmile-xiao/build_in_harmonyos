#!/bin/sh
# vonsh headless smoke test (R34: runs the packaged binary, asserts behavior).
# RES_DIR is compiled as "../share/games/vonsh/", so the game must be started
# from the package bin/ directory (resources live one level up). SDL dummy
# video/audio drivers let it initialize without a display; timeout(1) ends it —
# exit 124 means the game loop stayed alive for 5s. Any earlier non-zero exit
# (asset load failure, SDL init failure, crash) fails the test.
BIN="$1"
BIN_DIR=$(dirname "$BIN")
cd "$BIN_DIR" || exit 1
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy timeout 5 ./vonsh >/dev/null 2>&1
code=$?
if [ "$code" -eq 124 ]; then
    echo "vonsh smoke: game loop alive for 5s (timeout 124)"
    exit 0
fi
if [ "$code" -eq 0 ]; then
    echo "vonsh smoke: exited cleanly (0)"
    exit 0
fi
echo "vonsh smoke failed: exit $code" >&2
exit 1
