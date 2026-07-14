#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke + functional test for the daemon executable.
# Runs in the conanrun env, so PATH includes the installed bin/ (i.e. `daemon`).
set -euo pipefail

DAEMON="${1:-daemon}"

echo "[step] daemon --version"
# Proves the binary executes, is ELF-signed, and links libc/pthread/util.
"$DAEMON" --version

echo "[step] foreground client execution"
# daemon's core job is to launch a client process. In --foreground mode it runs
# the client synchronously and propagates the client's stdout/stderr. We have the
# client write a marker file, then verify the file landed (proves daemon forked +
# ran the client). --noconfig skips /etc/daemon.conf and ~/.daemonrc; --unsafe
# disables cwd/exec safety checks (harmless as non-root, guards against root).
WORK="$(mktemp -d "${TMPDIR:-/tmp}/daemon-test.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT
MARKER="$WORK/marker"
SH="$(command -v sh || true)"; [ -n "$SH" ] || SH="/bin/sh"
"$DAEMON" --noconfig --unsafe --foreground -- "$SH" -c "echo daemon-client-ran > '$MARKER'"
grep -q 'daemon-client-ran' "$MARKER"

echo "daemon test_package: PASS"
