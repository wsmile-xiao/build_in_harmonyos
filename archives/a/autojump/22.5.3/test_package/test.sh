#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for autojump executable + shell integration
# Runs in conanrun env: PATH includes installed bin/, AUTOJUMP_SHARE_DIR is
# exported by the recipe's runenv_info (VirtualRunEnv aggregates it).
set -euo pipefail

echo "[test] autojump --version"
autojump --version && echo "PASS --version OK" || {
    echo "[test] --version failed, trying --help..."
    autojump --help > /dev/null 2>&1 && echo "PASS --help OK" || {
        echo "FAIL autojump failed both --version and --help"
        exit 1
    }
}

# Shell integration end-to-end: source the packaged etc/profile.d/autojump.sh
# and verify the j() function gets defined (exercises the AUTOJUMP_SHARE_DIR
# branch added by patch 0001 — proves no build-machine path is baked in).
if [ -z "${AUTOJUMP_SHARE_DIR:-}" ]; then
    echo "FAIL AUTOJUMP_SHARE_DIR not set by conanrun environment"
    exit 1
fi
echo "[test] AUTOJUMP_SHARE_DIR=${AUTOJUMP_SHARE_DIR}"
pkg_dir=$(cd "${AUTOJUMP_SHARE_DIR}/../../../.." && pwd)
profile_sh="${pkg_dir}/etc/profile.d/autojump.sh"
if [ ! -s "${profile_sh}" ]; then
    echo "FAIL packaged autojump.sh not found at ${profile_sh}"
    exit 1
fi
# shellcheck disable=SC1090
# Upstream autojump.bash references XDG_DATA_HOME and PROMPT_COMMAND without
# defaults; provide standard/neutral defaults so sourcing under `set -u`
# (stricter than real interactive shells) does not trip on them.
export XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
PROMPT_COMMAND="${PROMPT_COMMAND:-}"
source "${profile_sh}"
if type j >/dev/null 2>&1; then
    echo "PASS shell integration OK (j function defined after source)"
else
    echo "FAIL shell integration: j function not defined after sourcing autojump.sh"
    exit 1
fi
