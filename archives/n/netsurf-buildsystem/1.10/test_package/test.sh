#!/bin/sh
set -e

shared=$1
test -f "$shared/makefiles/Makefile.tools"
test -f "$shared/makefiles/Makefile.top"
test -x "$shared/testtools/testrunner.pl"
test -x "$shared/citools/jenkins-build.sh"

# Upstream makefiles produce build directories as:
# build-$(BUILD)-$(HOST)-$(VARIANT)-$(COMPONENT_TYPE)
# with BUILD=release, HOST=linux, VARIANT=release, COMPONENT_TYPE=lib-static
# => build-release-linux-release-lib-static

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

# Run from / to avoid the OHOS virtual filesystem cwd issue.
cd /
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT HUP INT TERM

cat > "$tmp/Makefile" <<EOFMAKE
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
EOFMAKE

cat > "$tmp/smoke.c" <<'EOFSMOKE'
int netsurf_buildsystem_smoke(void)
{
    return 0;
}
EOFSMOKE

make -C "$tmp" all

# Verify the static library was created with the correct dir pattern.
BUILD_DIR=$tmp/build-release-linux-release-lib-static
test -s "$BUILD_DIR/libsmoke.a"

echo "netsurf-buildsystem consumer PASS"
