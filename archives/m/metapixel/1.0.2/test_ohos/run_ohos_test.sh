#!/bin/sh
# test_ohos/run_ohos_test.sh - metapixel 1.0.2 HarmonyOS PC specific verification.
#
# Self-contained, runs either on a real HarmonyOS PC (aarch64) or on a
# cross-build host that has aarch64 execution wired up.  These checks are
# deliberately different from the test_package consumer cases (which prove the
# software works) - they prove the *delivered artifact* is a well-formed
# HarmonyOS PC binary:
#
#   T1  ELF machine is AArch64
#   T2  no build-host absolute paths leaked into the binary
#   T3  dynamically resolved against the OHOS musl loader, not a host loader
#   T4  every shared object it needs is reachable through its RUNPATH
#   T5  real functional run: a photomosaic built by the packaged binary
#
# usage: sh run_ohos_test.sh <package-folder>
# exit:  0 = all passed, 1 = a check failed, 2 = usage error
set -u

PKG="$1"
[ -n "$PKG" ] && [ -d "$PKG" ] || { echo "usage: $0 <package-folder>"; exit 2; }

METAPIXEL="$PKG/bin/metapixel"
IMAGESIZE="$PKG/bin/metapixel-imagesize"
[ -x "$METAPIXEL" ] || { echo "FAIL: packaged binary missing: $METAPIXEL"; exit 2; }

PASS=0
FAIL=0
ok() { PASS=$((PASS + 1)); printf 'PASS: %s\n' "$1"; }
ko() { FAIL=$((FAIL + 1)); printf 'FAIL: %s\n' "$1"; }

echo "--- metapixel 1.0.2 HarmonyOS specific verification ---"

# ---------------------------------------------------------------- T1
if command -v readelf >/dev/null 2>&1; then
	if readelf -h "$METAPIXEL" 2>/dev/null | grep -q "AArch64"; then
		ok "T1 artifact is an ELF64 AArch64 binary"
	else
		ko "T1 artifact is not AArch64"
	fi
else
	if od -An -tx1 -N20 "$METAPIXEL" 2>/dev/null | grep -q "b7 00"; then
		ok "T1 artifact is an ELF64 AArch64 binary (e_machine=0xb7)"
	else
		ko "T1 artifact e_machine is not AArch64"
	fi
fi

# ---------------------------------------------------------------- T2
# A real leak indicator is the *build source tree* or the developer's home
# directory ending up inside the artifact.  Note that the conan package
# libdirs are legitimately absolute and do appear in RUNPATH (that is how the
# conan link model works, and it is what T4 asserts on purpose), so a conan
# cache prefix is not treated as a leak here.
leak=$(strings "$METAPIXEL" 2>/dev/null | grep -E '^(/storage/|/home/|/Users/)|/metapixel-1\.0\.2/' | head -1)
if [ -n "$leak" ]; then
	ko "T2 build-host path leaked into the binary: $leak"
else
	ok "T2 no build source tree or host home path leaked into the binary"
fi

# ---------------------------------------------------------------- T3
interp=$(readelf -l "$METAPIXEL" 2>/dev/null | sed -n 's/.*program interpreter: \(.*\)]/\1/p' | head -1)
case "$interp" in
*/ld-musl-aarch64.so.1|*/ld-linux-aarch64.so.1)
	ok "T3 resolves against the OHOS aarch64 loader ($interp)" ;;
*)
	ko "T3 unexpected program interpreter: '${interp:-none}'" ;;
esac

# ---------------------------------------------------------------- T4
# The image-format backends must be resolvable through RUNPATH, otherwise the
# binary only runs because of a conan-run environment and a plain consumer
# would get "Error loading shared library".  C runtime / platform objects are
# excluded on purpose: libc.so, libm.so and the C++ runtime are supplied by
# the OHOS loader and sysroot, not by RUNPATH.
need=""
for lib in $(readelf -d "$METAPIXEL" 2>/dev/null | sed -n 's/.*(NEEDED).*\[\(.*\)\]/\1/p'); do
	case "$lib" in
	libc.so*|libm.so*|libdl.so*|libpthread.so*|librt.so*|libunwind.so*|\
	libc++*|libc++abi*|libgcc_s.so*|libclang_rt*|libhilog_ndk.z*|libace_napi.z*)
		continue ;;
	esac
	need="$need $lib"
done
rpath=$(readelf -d "$METAPIXEL" 2>/dev/null | sed -n 's/.*(RUNPATH).*\[\(.*\)\]/\1/p')
missing=""
for lib in $need; do
	found=no
	for d in $(printf '%s' "$rpath" | tr ':' ' '); do
		[ -e "$d/$lib" ] && found=yes && break
	done
	[ "$found" = yes ] || missing="$missing $lib"
done
if [ -n "$need" ] && [ -z "$missing" ]; then
	ok "T4 image backends reachable through RUNPATH ($need)"
elif [ -z "$need" ]; then
	ko "T4 no image-format backend found in DT_NEEDED - is rwimg linked?"
else
	ko "T4 NOT resolvable via RUNPATH:$missing (rpath=$rpath)"
fi

# ---------------------------------------------------------------- T5
# Drive the packaged prepare step over the same mixed-format tile set used by
# test_package, so the OHOS run really decodes PNG + JPEG + GIF.  The fixtures
# come from the standard-library generator rather than from files in the repo:
# a PR is checked out as a text .diff, and a committed binary fixture would
# break the checkout before this script ever runs.
GEN="${GEN:-$(cd "$(dirname "$0")" && pwd)/../test_package/gen_images.py}"
[ -f "$GEN" ] || { echo "FAIL: fixture generator missing: $GEN"; exit 2; }

WORK="${TMPDIR:-$HOME/tmp}/metapixel-ohos.$$"
LIB="$WORK/library"
TILES="$WORK/images"
rm -rf "$WORK"
mkdir -p "$LIB" || { echo "FAIL: cannot create $LIB"; exit 1; }
trap 'rm -rf "$WORK"' EXIT
if ! python3 "$GEN" "$TILES" >/dev/null; then
	echo "FAIL: could not generate test fixtures"
	exit 1
fi

made=0
for f in "$TILES"/tile_*.png "$TILES"/tile_*.jpg "$TILES"/tile_*.gif; do
	[ -f "$f" ] || continue
	stem=$(basename "$f"); stem=${stem%.*}
	"$METAPIXEL" -w 8 -h 8 --prepare "$f" "$LIB/$stem" "$LIB/tables.mxt" \
		>/dev/null 2>&1 && made=$((made + 1))
done
	if [ "$made" -eq 0 ]; then
		ko "T5 no input tile could be prepared from the generated fixtures"
	else
		SRC=$(ls "$TILES"/target.png 2>/dev/null | head -1)
	if [ -z "$SRC" ]; then
		ko "T5 no PNG source image available to mosaic"
	else
		OUT="$WORK/ohos-mosaic.png"
		if "$METAPIXEL" -w 8 -h 8 -d 0 --library "$LIB" \
			--metapixel "$SRC" "$OUT" >/dev/null 2>&1 && [ -s "$OUT" ]; then
			sz=$("$IMAGESIZE" "$OUT" 2>/dev/null)
			if [ -n "$sz" ]; then
				ok "T5 packaged binary built a photomosaic ($made tiles, size $sz)"
			else
				ko "T5 mosaic written but metapixel-imagesize could not read it"
			fi
		else
			ko "T5 packaged binary failed to build a photomosaic"
		fi
	fi
fi

echo "OHOS_TEST_SUMMARY total=$((PASS + FAIL)) passed=$PASS failed=$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
