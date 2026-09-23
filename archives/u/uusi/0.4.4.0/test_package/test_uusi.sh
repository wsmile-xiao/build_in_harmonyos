#!/bin/sh
# test_uusi.sh - L1 test for uusi 0.4.4.0
# Verifies:
#   1. uusi / gen-setup / uusi-extract binaries exist
#   2. uusi-extract reads package name and version from a cabal file
#   3. uusi removes a dependency in place
#   4. uusi defaults to --all and removes version constraints
#   5. gen-setup writes Setup.hs
set -eu

PASS=0
FAIL=0
ok() { echo "  PASS: $1"; PASS=$((PASS+1)); }
no() { echo "  FAIL: $1"; FAIL=$((FAIL+1)); }

find_bin() {
    name="$1"
    if [ -n "${UUSI_PKG_ROOT:-}" ] && [ -x "${UUSI_PKG_ROOT}/bin/${name}" ]; then
        printf '%s\n' "${UUSI_PKG_ROOT}/bin/${name}"
        return 0
    fi

    for root in "${CONAN_HOME:-$HOME/.cache/conan2}/p" "$HOME/.cache/conan2/p" "$HOME/.conan2/p"; do
        if [ -d "$root" ]; then
            found=$(find "$root" -path "*/bin/${name}" -type f 2>/dev/null | head -n 1 || true)
            if [ -n "$found" ]; then
                printf '%s\n' "$found"
                return 0
            fi
        fi
    done

    return 0
}

UUSI="$(find_bin uusi)"
UUSI_EXTRACT="$(find_bin uusi-extract)"
GEN_SETUP="$(find_bin gen-setup)"

echo "=== uusi L1 test ==="
echo "  uusi: ${UUSI:-<not found>}"
echo "  uusi-extract: ${UUSI_EXTRACT:-<not found>}"
echo "  gen-setup: ${GEN_SETUP:-<not found>}"

if [ -z "$UUSI" ] || [ ! -x "$UUSI" ]; then
    no "uusi binary not found"
fi
if [ -z "$UUSI_EXTRACT" ] || [ ! -x "$UUSI_EXTRACT" ]; then
    no "uusi-extract binary not found"
fi
if [ -z "$GEN_SETUP" ] || [ ! -x "$GEN_SETUP" ]; then
    no "gen-setup binary not found"
fi
if [ "$FAIL" -gt 0 ]; then
    echo ""
    echo "=== Result: PASS=$PASS FAIL=$FAIL ==="
    exit 1
fi
ok "all three binaries exist"

WORKBASE="${TMPDIR:-$HOME/tmp}"
mkdir -p "$WORKBASE"
WORKDIR=$(mktemp -d "${WORKBASE}/uusi-test.XXXXXX" 2>/dev/null || true)
if [ -z "$WORKDIR" ]; then
    WORKDIR="${WORKBASE}/uusi-test"
    mkdir -p "$WORKDIR"
fi
trap 'rm -rf "$WORKDIR"' EXIT INT TERM

write_sample() {
    target="$1"
    cat > "$target" <<'EOF'
cabal-version: 2.4
name: sample
version: 1.2.3.4
build-type: Simple

library
  exposed-modules: Sample
  build-depends: base >=4.8 && <5, text >=1.2, semigroup >=0.9
  default-language: Haskell2010

executable sample
  main-is: Main.hs
  build-depends: base >=4.8 && <5, text >=1.2, semigroup >=0.9
  default-language: Haskell2010
EOF
}

NAME_DIR="$WORKDIR/name"
DELETE_DIR="$WORKDIR/delete"
ALL_DIR="$WORKDIR/all"
GEN_DIR="$WORKDIR/gen"
mkdir -p "$NAME_DIR" "$DELETE_DIR" "$ALL_DIR" "$GEN_DIR"
write_sample "$NAME_DIR/sample.cabal"
cp "$NAME_DIR/sample.cabal" "$DELETE_DIR/sample.cabal"
cp "$NAME_DIR/sample.cabal" "$ALL_DIR/sample.cabal"

OLDPWD="$(pwd)"
cd "$NAME_DIR" || exit 1
if NAME_OUT=$("$UUSI_EXTRACT" --print-name 2>"$WORKDIR/uusi-extract-name.err"); then
    if [ "$NAME_OUT" = "sample" ]; then
        ok "uusi-extract --print-name -> sample"
    else
        no "uusi-extract --print-name mismatch: $NAME_OUT"
    fi
else
    no "uusi-extract --print-name failed: $(head -n 2 "$WORKDIR/uusi-extract-name.err")"
fi
if VERSION_OUT=$("$UUSI_EXTRACT" --print-version 2>"$WORKDIR/uusi-extract-version.err"); then
    if [ "$VERSION_OUT" = "1.2.3.4" ]; then
        ok "uusi-extract --print-version -> 1.2.3.4"
    else
        no "uusi-extract --print-version mismatch: $VERSION_OUT"
    fi
else
    no "uusi-extract --print-version failed: $(head -n 2 "$WORKDIR/uusi-extract-version.err")"
fi
cd "$OLDPWD" || exit 1

if "$UUSI" -dsemigroup "$DELETE_DIR/sample.cabal" >"$DELETE_DIR/uusi.out" 2>"$DELETE_DIR/uusi.err"; then
    if grep -q "semigroup" "$DELETE_DIR/sample.cabal"; then
        no "uusi -dsemigroup still left semigroup in the file"
    else
        ok "uusi -dsemigroup removed semigroup"
    fi
else
    no "uusi -dsemigroup failed: $(head -n 2 "$DELETE_DIR/uusi.err")"
fi

cd "$ALL_DIR" || exit 1
if "$UUSI" >"$WORKDIR/uusi-all.out" 2>"$WORKDIR/uusi-all.err"; then
    if grep -q ">=" "$ALL_DIR/sample.cabal"; then
        no "uusi --all still left version constraints"
    else
        ok "uusi default --all removed version constraints"
    fi
else
    no "uusi default --all failed: $(head -n 2 "$WORKDIR/uusi-all.err")"
fi
cd "$OLDPWD" || exit 1

cd "$GEN_DIR" || exit 1
if "$GEN_SETUP" >"$WORKDIR/gen-setup.out" 2>"$WORKDIR/gen-setup.err"; then
    if [ -f "$GEN_DIR/Setup.hs" ] && grep -q "defaultMain" "$GEN_DIR/Setup.hs"; then
        ok "gen-setup wrote Setup.hs"
    else
        no "gen-setup did not write the expected Setup.hs"
    fi
else
    no "gen-setup failed: $(head -n 2 "$WORKDIR/gen-setup.err")"
fi
cd "$OLDPWD" || exit 1

echo ""
echo "=== Result: PASS=$PASS FAIL=$FAIL ==="
if [ "$FAIL" -gt 0 ]; then exit 1; fi
exit 0
