#!/bin/sh
set -eu

source_root=$1
build_root=$2
output=$3
configure_shell=${CONFIG_SHELL:-/bin/sh}

test -x "$configure_shell"
rm -rf "$build_root"
cp -R "$source_root" "$build_root"
cd "$build_root"
CONFIG_SHELL="$configure_shell" "$configure_shell" ./configure \
  --prefix=/ \
  --syslibdir=/lib
make -j2 lib/libc.so
test -f lib/libc.so
mkdir -p "$(dirname "$output")"
cp lib/libc.so "$output"
chmod 755 "$output"
