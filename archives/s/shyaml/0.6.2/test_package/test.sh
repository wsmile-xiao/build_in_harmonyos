#!/bin/sh
set -eu

command -v shyaml >/dev/null
version=$(shyaml --version)
printf '%s\n' "$version" | grep -F 'version: 0.6.2' >/dev/null

value=$(printf 'outer:\n  inner: value\n' | shyaml get-value outer.inner)
test "$value" = value

value=$(printf 'items:\n  - alpha\n  - beta\n' | shyaml get-value items.1)
test "$value" = beta

value=$(printf 'enabled: true\n' | shyaml get-type enabled)
test "$value" = bool