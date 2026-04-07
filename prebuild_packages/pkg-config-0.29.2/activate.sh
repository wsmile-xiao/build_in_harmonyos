#!/bin/sh
# Portable activation script for pkg-config (HarmonyOS)
if [ -n "$_OLD_PKG_PATH" ]; then
    echo "Already activated."
    return 2>/dev/null || exit 0
fi
_PKG_DIR="$(cd "$(dirname "$0")" && pwd)"
_OLD_PKG_PATH="$PATH"
_OLD_LD_PATH="${LD_LIBRARY_PATH:-}"
export PATH="$_PKG_DIR/bin:$PATH"
export LD_LIBRARY_PATH="$_PKG_DIR/lib${_OLD_LD_PATH:+:$_OLD_LD_PATH}"
[ -n "$PS1" ] && _OLD_PS1="$PS1" && export PS1="(pkg-config) $PS1"
deactivate_pkg() {
    export PATH="$_OLD_PKG_PATH"
    export LD_LIBRARY_PATH="$_OLD_LD_PATH"
    unset _PKG_DIR _OLD_PKG_PATH _OLD_LD_PATH
    unset -f deactivate_pkg
    echo "Deactivated."
}
echo "Activated: $_PKG_DIR (pkg-config 0.29.2 for HarmonyOS)"
