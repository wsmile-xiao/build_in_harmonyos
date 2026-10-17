#!/bin/sh
# Consumer test for the packaged pianobar CLI binary (OHOS-hermetic).
#
# Why no execution: upstream src/main.c enters BarMainLoop() which prompts
# for Pandora credentials via BarReadlineStr() (src/ui_readline.c). On EOF
# stdin (e.g. `< /dev/null`) BarReadline clears stdin from the fd set and
# re-enters select() with an empty set and infinite timeout, blocking
# forever; on the HMBS device the hung (or unsigned interactive) process is
# then reaped as `Signal 9` / exit 137, failing `conan create`. The binary
# also has no --help/--version path (argc/argv are ignored) and a live run
# would need Pandora network credentials, so executing it is inherently
# flaky. This test therefore verifies delivery statically: executable bit,
# linked-in banner/version strings, and the installed man page. No network,
# no terminal, no writes outside $TMPDIR.
set -eu

PIANOBAR=${1:?missing pianobar executable}
PASS=0

ok() {
  PASS=$((PASS + 1))
  printf 'PASS: %s\n' "$1"
}

test -x "$PIANOBAR"
ok "pianobar binary exists and is executable"

# Isolate HOME/XDG_CONFIG_HOME under the HMBS-provided writable TMPDIR so
# no probe ever touches read-only /tmp or the real HOME (POSIX sh: no
# pipefail; TMPDIR/TMP/TEMP are injected by hmbs, fall back to /tmp).
TMPBASE="${TMPDIR:-${TMP:-/tmp}}"
WORK="$(mktemp -d "${TMPBASE}/pianobar-cli-XXXXXX")"
trap 'rm -rf "$WORK"' EXIT INT TERM
export HOME="$WORK"
export XDG_CONFIG_HOME="$WORK"

# Banner / version are linked into the binary via
# BarUiMsg("Welcome to " PACKAGE " (" VERSION ")!") in src/main.c.
if command -v strings >/dev/null 2>&1; then
  strings "$PIANOBAR" | grep -q "Welcome to pianobar"
else
  grep -a -q "Welcome to pianobar" "$PIANOBAR"
fi
ok "welcome banner string is linked into the binary"

if command -v strings >/dev/null 2>&1; then
  strings "$PIANOBAR" | grep -q "2024.12.21"
else
  grep -a -q "2024.12.21" "$PIANOBAR"
fi
ok "binary carries the 2024.12.21 version string"

PKGROOT="$(dirname "$(dirname "$PIANOBAR")")"
test -f "$PKGROOT/share/man/man1/pianobar.1"
ok "man page share/man/man1/pianobar.1 is installed"

printf 'pianobar CLI consumer tests passed (%d assertions)\n' "$PASS"
