#!/usr/bin/env sh
set -euo pipefail

screenresolution="${1:?screenresolution binary path required}"

version_output="$("$screenresolution" -version)"
printf '%s\n' "$version_output"
printf '%s\n' "$version_output" | grep -F "screenresolution version 1.6"

get_output="$("$screenresolution" get)"
printf '%s\n' "$get_output"
printf '%s\n' "$get_output" | grep -E '^Display 0: [1-9][0-9]*x[1-9][0-9]*x32@[1-9][0-9]*$'

list_error_file="$(mktemp)"
if "$screenresolution" list 2>"$list_error_file"; then
    cat "$list_error_file"
    rm -f "$list_error_file"
    echo "screenresolution list unexpectedly succeeded on OHOS" >&2
    exit 1
fi
cat "$list_error_file"
grep -F "list is not supported on OHOS NativeDisplayManager backend" "$list_error_file"
rm -f "$list_error_file"

set_error_file="$(mktemp)"
if "$screenresolution" set 800x600x32 2>"$set_error_file"; then
    cat "$set_error_file"
    rm -f "$set_error_file"
    echo "screenresolution set unexpectedly succeeded on OHOS" >&2
    exit 1
fi
cat "$set_error_file"
grep -F "set is not supported on OHOS NativeDisplayManager backend" "$set_error_file"
rm -f "$set_error_file"
