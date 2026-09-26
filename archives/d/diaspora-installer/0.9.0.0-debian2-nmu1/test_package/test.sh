#!/bin/sh
# diaspora-installer smoke test — real `sh` invocation of the packaged scripts.
# Runs only side-effect-free checks (R34): shell syntax validation of every
# shipped .sh plus running diaspora-versions.sh to assert the version.
set -eu

SHARE_DIR="$1"

# Normalize Windows-style "C:\..." paths to POSIX when running under
# git-bash (local Windows verification). No-op on Linux CI workers.
case "$SHARE_DIR" in
  [A-Za-z]:*)
    if command -v cygpath >/dev/null 2>&1; then
      SHARE_DIR=$(cygpath -u "$SHARE_DIR")
    fi
    ;;
esac

[ -d "$SHARE_DIR" ] || { echo "FATAL: share dir missing: $SHARE_DIR" >&2; exit 1; }

script_count=0
for s in "$SHARE_DIR"/*.sh; do
  [ -f "$s" ] || continue
  # syntax-check every script without executing it
  sh -n "$s" || { echo "FATAL: syntax error in $s" >&2; exit 1; }
  script_count=$((script_count + 1))
done
[ "$script_count" -ge 5 ] || { echo "FATAL: unexpected script count $script_count" >&2; exit 1; }

# diaspora-versions.sh is designed to be embedded (it reads $2 = installed
# version and $diaspora_version from diaspora-common.conf). Simulate that
# context: source it with an installed-version argument and the config var.
. "$SHARE_DIR/diaspora-common.conf"  # exports diaspora_version=0.9.0.0
installed_ver="$diaspora_version"
# shellcheck disable=SC1091
. "$SHARE_DIR/diaspora-versions.sh" "$installed_ver" "$installed_ver"
[ "$installed_diaspora_version" = "0.9.0.0" ] || { echo "FATAL: wrong installed version" >&2; exit 1; }
[ "$diaspora_minor_version" = "0.0" ] || { echo "FATAL: wrong minor version" >&2; exit 1; }

echo "DIASPORA_INSTALLER_VALIDATION_PASS version=$diaspora_version scripts=$script_count"
echo "[diaspora-installer test] PASS"