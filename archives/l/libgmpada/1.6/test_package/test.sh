#!/usr/bin/env bash
# libgmpada test_package -- build the Ada consumer only.
# Signing and execution are done by conanfile.py (OHOS requires signed ELFs).
set -euo pipefail
cd "$(dirname "$0")"

# $1 gnatmake, $2 Ada include dir, $3 Ada library (ALI) dir,
# $4 libgmpada static archive, $5 gmp library dir
GNATMAKE="$1"; ADAINC="$2"; ADALIB="$3"; STATICLIB="$4"; GMPLIBDIR="$5"

echo "gnatmake    = ${GNATMAKE}"
echo "adainclude  = ${ADAINC}"
echo "adalib      = ${ADALIB}"
echo "libgmpada.a = ${STATICLIB}"
echo "gmp libdir  = ${GMPLIBDIR}"

rm -f gmpada-consumer
"${GNATMAKE}" -o gmpada-consumer src/main.adb -Isrc \
    -I"${ADAINC}/gmpada" -aO"${ADALIB}/gmpada" \
    -largs "${STATICLIB}" -L"${GMPLIBDIR}" -lgmp
echo "BUILD_OK"
