#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for arttime (R34)
#
# arttime is a zsh shell-script CLI tool. On OHOS, the zsh installation
# may lack the standard autoload function `is-at-least` (used by arttime
# for version checking). This script creates a minimal `is-at-least`
# function in a temporary fpath directory so that arttime can start,
# then runs `arttime --version` to verify the packaged executable.
set -eu

# --- Create minimal is-at-least zsh autoload function ---
FPATH_DIR="$HOME/.local/share/zsh/site-functions"
mkdir -p "$FPATH_DIR"

if ! zsh -c 'autoload -Uz is-at-least && is-at-least 5.7' 2>/dev/null; then
    cat > "$FPATH_DIR/is-at-least" << 'ZSHFUNC'
emulate -L zsh
local i
if [[ "$1" == *.* ]]; then
  local IFS=.
  local -a v1 v2
  v1=(${=1})
  v2=(${=ZSH_VERSION})
  for ((i = 1; i <= ${#v1}; i++)); do
    if (( ${v2[i]:-0} > ${v1[i]:-0} )); then
      return 0
    elif (( ${v2[i]:-0} < ${v1[i]:-0} )); then
      return 1
    fi
  done
  return 0
else
  [[ ${ZSH_VERSION} -ge $1 ]]
fi
ZSHFUNC
    echo "[setup] Created is-at-least function in $FPATH_DIR"
else
    echo "[setup] is-at-least already available"
fi

export FPATH="$FPATH_DIR:${FPATH:-}"

# --- R34: Run the packaged arttime binary ---
echo "[test] arttime --version"
OUTPUT=$(arttime --version 2>&1 || true)
echo "$OUTPUT"

if echo "$OUTPUT" | grep -q "2.5.0"; then
    echo "OK: arttime --version outputs 2.5.0"
else
    echo "FAIL: arttime --version did not output expected version"
    exit 1
fi

echo "All tests passed."
