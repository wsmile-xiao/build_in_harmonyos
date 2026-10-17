#!/usr/bin/env sh
set -eu

zig_bin=$1
work_dir=$2

version=$("$zig_bin" version)
if [ "$version" != "0.16.0" ]; then
    echo "unexpected Zig version: $version" >&2
    exit 1
fi

mkdir -p "$work_dir"
cd "$work_dir"

export ZIG_GLOBAL_CACHE_DIR="$work_dir/zig-global-cache"
export ZIG_LOCAL_CACHE_DIR="$work_dir/zig-local-cache"

"$zig_bin" build run install --summary all -Doptimize=ReleaseSmall

test -x zig-out/bin/smoke
