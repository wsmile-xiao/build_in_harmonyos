#!/bin/sh
set -eu

shared=$1
test -f "$shared/makefiles/Makefile.tools"
test -f "$shared/makefiles/Makefile.top"
test -x "$shared/testtools/testrunner.pl"
test -x "$shared/citools/jenkins-build.sh"

# Prefer the target clang toolchain, but keep the consumer test runnable in
# the Windows host environment used by local Conan verification.
if command -v clang >/dev/null 2>&1 && \
   command -v clang++ >/dev/null 2>&1 && \
   command -v llvm-ar >/dev/null 2>&1; then
    CC=clang
    CXX=clang++
    AR=llvm-ar
elif command -v gcc >/dev/null 2>&1 && \
     command -v g++ >/dev/null 2>&1 && \
     command -v ar >/dev/null 2>&1; then
    CC=gcc
    CXX=g++
    AR=ar
else
    echo 'No supported C compiler and archiver found' >&2
    exit 1
fi

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT HUP INT TERM

cat > "$tmp/Makefile" <<EOF
COMPONENT := smoke
COMPONENT_TYPE := lib-static
COMPONENT_VERSION := 1.0.0
HOST := linux
TARGET := linux
BUILD := release
CC_CAN_BUILD_AND_DEP := yes
CC := $CC
CXX := $CXX
AR := $AR
SOURCES := smoke.c
NSSHARED := $shared
include $shared/makefiles/Makefile.tools
include $shared/makefiles/Makefile.top
EOF

cat > "$tmp/smoke.c" <<'EOF'
int netsurf_buildsystem_smoke(void)
{
    return 0;
}
EOF

make -C "$tmp" all
test -s "$tmp/build-linux-linux-release-lib-static/libsmoke.a"
printf '%s\n' 'netsurf-buildsystem consumer PASS'
