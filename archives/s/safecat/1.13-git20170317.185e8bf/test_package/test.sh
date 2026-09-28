#!/usr/bin/env bash
set -eu
root="$(mktemp -d)"
trap 'rm -rf "$root"' EXIT
mkdir -p "$root/tmp" "$root/new"
printf 'safecat-ohos\n' | safecat "$root/tmp" "$root/new" > "$root/name"
name="$(cat "$root/name")"
test -n "$name"
test -f "$root/new/$name"
test "$(cat "$root/new/$name")" = 'safecat-ohos'
test "$(find "$root/tmp" -type f | wc -l)" -eq 0
if printf 'bad\n' | safecat "$root/tmp" "$root/missing" >/dev/null 2>&1; then
  echo 'invalid destination unexpectedly succeeded' >&2
  exit 1
fi
echo 'safecat smoke: 6 assertions passed'
