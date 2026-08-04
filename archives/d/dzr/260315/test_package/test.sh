#!/usr/bin/env bash
# test_package/test.sh — dzr smoke test for CI L0c compliance
#
# NON-INTERACTIVE smoke test. dzr's `--help` is NOT a help flag — the
# upstream shell script treats unknown args as a deezer URL/route, falls
# into the interactive "paste the deezer:// link here:" auth loop, and
# blocks on stdin forever (CI hits the 1800s timeout and even SIGKILL
# cannot terminate it). So we must NOT call `dzr --help`.
#
# Instead we verify the packaged scripts exist, are executable, and have
# the E165 shebang fix applied (`/system/bin/sh` — OHOS has no /bin/sh).
# This is a pure local check: no network, no stdin, no deezer auth.
set -euo pipefail

DZR_BIN="${1:-}"
if [ -z "$DZR_BIN" ]; then
    echo "usage: $0 <dzr-bin-dir>" >&2
    exit 1
fi

for script in dzr dzr-url dzr-dec dzr-srt dzr-id3; do
    path="$DZR_BIN/$script"
    echo "[test] checking $script"
    if [ ! -f "$path" ]; then
        echo "❌ $script missing from package ($path)"
        exit 1
    fi
    if [ ! -x "$path" ]; then
        echo "❌ $script not executable ($path)"
        exit 1
    fi
    # E165: shebang must point at OHOS /system/bin/sh, not /bin/sh
    first=$(head -n1 "$path")
    if [ "$first" != "#!/system/bin/sh" ]; then
        echo "❌ $script shebang not E165-fixed: '$first' (expected #!/system/bin/sh)"
        exit 1
    fi
    echo "✅ $script present, executable, shebang OK"
done

echo "[test] dzr smoke test: PASS"
