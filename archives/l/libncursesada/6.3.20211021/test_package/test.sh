#!/usr/bin/env bash
# libncursesada test_package -- build the Ada consumer only.
# Signing and execution are done by conanfile.py (OHOS requires signed ELFs).
set -euo pipefail
cd "$(dirname "$0")"

# $1 = Ada include dir (libncursesada's share/ada/adainclude)
# $2 = Ada library dir (libncursesada's lib/ada/adalib)
# conanfile.py passes both explicitly; PREPEND them so the GNAT runtime paths
# contributed by the gcc-ada tool_require are preserved.
if [ -n "${1:-}" ]; then ADA_INCLUDE_PATH="$1${ADA_INCLUDE_PATH:+:$ADA_INCLUDE_PATH}"; fi
if [ -n "${2:-}" ]; then ADA_OBJECTS_PATH="$2${ADA_OBJECTS_PATH:+:$ADA_OBJECTS_PATH}"; fi
export ADA_INCLUDE_PATH ADA_OBJECTS_PATH
LIBDIR="${ADA_OBJECTS_PATH%%:*}"
echo "ADA_INCLUDE_PATH=${ADA_INCLUDE_PATH:-<unset>}"
echo "LIBDIR=${LIBDIR}"

# $3 = ncurses library dir, $4 = ncurses -l flags (from the ncurses cpp_info).
# libAdaCurses.a is static, so the ncurses symbols must be supplied here too,
# AFTER -lAdaCurses (static link order matters).
if [ -n "${3:-}" ]; then
    NCLIBDIR="$3"
else
    NCLIBDIR="$(pkg-config --variable=libdir ncursesw 2>/dev/null || true)"
fi
if [ -n "${4:-}" ]; then
    NCLIBS="$4"
else
    NCLIBS="$(pkg-config --libs ncursesw 2>/dev/null || echo "-lncursesw")"
fi
echo "NCLIBDIR=${NCLIBDIR}"
echo "NCLIBS=${NCLIBS}"

rm -f ncursesada-consumer
gnatmake -o ncursesada-consumer src/main.adb -Isrc \
    -largs "-L${LIBDIR}" -lAdaCurses "-L${NCLIBDIR}" ${NCLIBS}

# Persist the terminfo location for the runner (no guessing in run_pty.py).
if [ -n "${NCLIBDIR}" ] && [ -d "${NCLIBDIR}/terminfo" ]; then
    printf "%s\n" "${NCLIBDIR}/terminfo" > .terminfo_path
fi
echo "BUILD_OK"

