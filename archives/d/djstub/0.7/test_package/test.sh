#!/usr/bin/env bash
set -euo pipefail

djstubify_path="$(command -v djstubify)"
test_root="${TMPDIR:-.}/djstub-test-$$"
original="$test_root/original"
payload="$test_root/payload"

mkdir -p "$test_root"
trap 'rm -rf "$test_root"' EXIT HUP INT TERM

version="$(djstubify -v)"
test "$version" = "djstubify version 0.7"
test "$(djstubify --version)" = "djstubify version 0.7"

cp "$djstubify_path" "$original"
cp "$original" "$payload"
chmod 755 "$original" "$payload"

# Add the embedded DOS stub in place and verify that the host ELF is detected.
djstubify "$payload"
info="$(djstubify -i "$payload")"
printf '%s\n' "$info" | grep -F "dj64 file format"
printf '%s\n' "$info" | grep -F "aarch64/ELF"

# Removing the stub must reproduce the original ELF byte for byte.
djstubify -r "$payload"
cmp "$original" "$payload"

# The installed wrapper script must resolve the packaged djstubify command.
test "$(djlink -v)" = "djstubify version 0.7"
test "$(djstrip)" = "Usage: djstrip <file_name>"
test "$(djelfextract)" = "Usage: djelfextract <solib_name> <out_elf>"
