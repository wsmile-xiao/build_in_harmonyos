#!/bin/sh
set -eu

binary="$1"
target_os="$2"
help_output=$("$binary" --help 2>&1)
case "$help_output" in
    *"Usage:"*"--help"*) ;;
    *)
        printf '%s\n' "FAIL: packaged help output is incomplete" >&2
        exit 1
        ;;
esac

if [ "$target_os" = "OHOS" ]; then
    fullname=$(param get const.ohos.fullname)
    case "$fullname" in
        *HarmonyOS*|*OpenHarmony*) ;;
        *)
            printf 'FAIL: expected HarmonyOS system fullname, got: %s\n' "$fullname" >&2
            exit 1
            ;;
    esac
    printf 'PASS: packaged CLI help and HarmonyOS system property (%s)\n' "$fullname"
else
    printf 'PASS: packaged CLI help\n'
fi
