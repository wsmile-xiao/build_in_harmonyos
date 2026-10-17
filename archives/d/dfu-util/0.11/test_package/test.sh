#!/bin/sh
# dfu-util 0.11 packaged binaries smoke test.
set -e
export LD_LIBRARY_PATH="/storage/Users/currentUser/usr/local/lib:/data/service/hnp/lib:${LD_LIBRARY_PATH:-}"

check_version() {
    command="$1"
    expected="$2"
    output="$("$command" --version 2>&1)"
    case "$output" in
        *"$expected"*) ;;
        *) echo "$command --version unexpected output: $output"; exit 1 ;;
    esac
}

# dfu-util 0.11 的 --version 首行：dfu-util 为 "dfu-util 0.11"，
# dfu-prefix/dfu-suffix 为 "NAME (dfu-util) 0.11"。
check_version dfu-util "dfu-util 0.11"
check_version dfu-prefix "dfu-prefix (dfu-util) 0.11"
check_version dfu-suffix "dfu-suffix (dfu-util) 0.11"