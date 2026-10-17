# Source this file from an interactive POSIX shell after putting wcd on PATH.
# WCDHOME should point to a writable state directory on restricted systems.
wcd () {
    _wcd_go="${WCDHOME:-${HOME}}/bin/wcd.go"
    rm -f "$_wcd_go" 2>/dev/null
    command wcd "$@"
    _wcd_rc=$?
    if [ -f "$_wcd_go" ]; then
        . "$_wcd_go"
    fi
    unset _wcd_go
    return "$_wcd_rc"
}
