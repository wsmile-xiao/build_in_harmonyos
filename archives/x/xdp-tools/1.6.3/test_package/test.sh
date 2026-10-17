#!/usr/bin/env bash
# xdp-tools CLI smoke test.
#
# Exercises the installed xdp-loader / xdp-filter / xdpdump entry points that
# do not touch the BPF syscall, so it works on OHOS:
#   * xdp-loader / xdp-filter are subcommand CLIs: 'help' and '<cmd> --help'
#     print usage (they have no --version option -- verified on the built
#     binaries);
#   * xdpdump uses the shared option parser and does support --help/--version.
# Every assertion is checked; any failure makes the script exit non-zero, so
# the conan test() really fails instead of reporting a false pass.
set -euo pipefail

loader="${1:?missing xdp-loader}"
filter="${2:?missing xdp-filter}"
dump="${3:?missing xdpdump}"

failed=0

for tool in "$loader" "$filter" "$dump"; do
    if [ -x "$tool" ]; then
        echo "[ok] executable: $tool"
    else
        echo "FAIL: missing or non-executable package binary: $tool" >&2
        failed=$((failed + 1))
    fi
done

check() {
    # check <label> <tool> <needle> <args...>
    local label="$1" tool="$2" needle="$3"
    shift 3
    local out
    out="$("$tool" "$@" 2>&1)" || true
    printf '[run] %s:\n%s\n' "$label" "$out"
    case "$out" in
        *"$needle"*) return 0 ;;
        *) echo "FAIL: $label did not print '$needle'" >&2; return 1 ;;
    esac
}

check "xdp-loader help"        "$loader" "Usage: xdp-loader COMMAND" help        || failed=$((failed + 1))
check "xdp-filter help"        "$filter" "Usage: xdp-filter COMMAND" help        || failed=$((failed + 1))
check "xdpdump --help"         "$dump"   "Usage: xdpdump"            --help      || failed=$((failed + 1))
check "xdpdump --version"      "$dump"   "version 1.6.3 using libbpf version" --version || failed=$((failed + 1))
check "xdp-loader load --help" "$loader" "Usage: xdp-loader load"    load --help || failed=$((failed + 1))
check "xdp-filter load --help" "$filter" "Usage: xdp-filter load"    load --help || failed=$((failed + 1))

if [ "$failed" -ne 0 ]; then
    echo "[fail] $failed of 9 assertions failed" >&2
    exit 1
fi

echo "[ok] xdp-tools CLI smoke test passed (3 binaries, 9 assertions)"
