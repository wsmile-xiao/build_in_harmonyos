#!/bin/bash
# build_alcotest.sh — Build alcotest 1.9.1 from source on HarmonyOS (arm64)
# Called by conanfile.py build() with: bash build_alcotest.sh <src_dir> <pkg_dir> <ocaml_root>
set -euo pipefail

SRC_DIR="$1"     # monorepo root (= self.source_folder)
PKG_DIR="$2"     # package output folder (= self.package_folder)

# ── Step 0: Set up OCaml environment ──
# tool_requires adds ocamlc to PATH; derive OCaml root from binary location
# (ocamlc -where returns build-time path on HMDFS, so we derive from binary path instead)
OCAML_ROOT=$(dirname "$(dirname "$(which ocamlc)")")
OCAMLLIB="$OCAML_ROOT/lib/ocaml"
export PATH="$OCAML_ROOT/bin:$PATH"
export OCAMLLIB
export CAML_LD_LIBRARY_PATH="$OCAML_ROOT/lib/ocaml/stublibs"
export OCAML_ROOT_DIR="$OCAML_ROOT"
export TMPDIR="${TMPDIR:-/tmp}"

# Fix 'ocaml' script shebang — conan OCaml package is not relocatable:
# the shebang points to the build-machine path, not the install path.
# Rewrite it to use the correct ocamlrun location derived from OCAML_ROOT.
OCAML_SCRIPT="$OCAML_ROOT/bin/ocaml"
OCAMLRUN="$OCAML_ROOT/bin/ocamlrun"
if [ -f "$OCAML_SCRIPT" ] && [ -f "$OCAMLRUN" ]; then
  sed -i "1s|#!.*|#!$OCAMLRUN|" "$OCAML_SCRIPT"
  echo "[build] Fixed ocaml shebang → $OCAMLRUN"
fi

echo "[build] OCAMLLIB=$OCAMLLIB"
echo "[build] ocamlc=$(which ocamlc)"
ocamlc -version

# ── Step 1: Build dune from source ──
DUNE_SRC="$SRC_DIR/.dune"
echo "[build] Step 1: Building dune from source..."
cd "$DUNE_SRC"

# Fix: pthread not linked on HarmonyOS (SYSTEM=linux)
sed -i 's/; (\[ "beos" \], \[ "-cclib"; "-lbsd" \])$/; (["beos"], ["-cclib"; "-lbsd"]); (["linux"], ["-ccopt"; "-pthread"; "-cclib"; "-pthread"])/' boot/libs.ml
# Fix: spawn_stubs.c uses pthread_setcancelstate which is unavailable on HarmonyOS
# Replace calls with no-ops (cancellation is not critical for dune build)
sed -i 's/pthread_setcancelstate(PTHREAD_CANCEL_DISABLE, \&cancel_state);/(void)0;/g' vendor/spawn/src/spawn_stubs.c
sed -i 's/pthread_setcancelstate(cancel_state, NULL);/(void)0;/g' vendor/spawn/src/spawn_stubs.c

# Compile the dune bootstrap binary directly.
# NOTE: Do NOT use "ocaml boot/bootstrap.ml" — it passes the script name as
# a spurious argument to .duneboot.exe, causing Arg.parse to error out and
# skip the actual dune build (silently exits 0 on some platforms).
ocamlc -output-complete-exe -w -24 -g -o .duneboot.exe -I boot unix.cma boot/libs.ml boot/duneboot.ml 2>&1 \
  || { echo "[build] dune bootstrap compile failed"; exit 1; }
echo "[build] Running dune bootstrap..."
./.duneboot.exe || { echo "[build] dune bootstrap build failed"; exit 1; }
rm -f .duneboot.exe

# duneboot.ml uses build_dir="_boot" and outputs to _boot/dune.exe
DUNE_BIN="$DUNE_SRC/_boot/dune.exe"
if [ ! -f "$DUNE_BIN" ]; then
  echo "[build] ERROR: dune binary not found at $DUNE_BIN"
  exit 1
fi
echo "[build] dune built: $($DUNE_BIN --version)"

# ── Step 2: Create dune-project and dune files for packages without dune support ──
# fmt 0.9.0 (uses _tags/ocamlbuild, needs dune files)
echo "[build] Step 2: Creating dune files for ocamlbuild packages..."

cat > "$SRC_DIR/fmt/dune-project" << 'EOF'
(lang dune 3.0)
(name fmt)
(implicit_transitive_deps false)
(generate_opam_files true)
(package (name fmt) (synopsis "OCaml pretty-printing"))
(package (name fmt_tty) (synopsis "Fmt tty") (allow_empty))
(package (name fmt_cli) (synopsis "Fmt cli") (allow_empty))
EOF

cat > "$SRC_DIR/fmt/src/dune" << 'EOF'
(library
 (name fmt)
 (public_name fmt)
 (modules fmt))

(library
 (name fmt_tty)
 (public_name fmt.tty)
 (libraries fmt unix)
 (modules fmt_tty))

(library
 (name fmt_cli)
 (public_name fmt.cli)
 (libraries fmt fmt_tty unix cmdliner)
 (modules fmt_cli)
 (ocamlc_flags (:standard -alert -deprecated))
 (ocamlopt_flags (:standard -alert -deprecated)))
EOF

# astring 0.8.5 (uses _tags/ocamlbuild, needs dune files)
cat > "$SRC_DIR/astring/dune-project" << 'EOF'
(lang dune 3.0)
(name astring)
(implicit_transitive_deps false)
(generate_opam_files true)
(package (name astring) (synopsis "Alternative String type for OCaml"))
EOF

cat > "$SRC_DIR/astring/src/dune" << 'DUNEEOF'
(library
 (name astring)
 (public_name astring)
 (modules astring_base astring_char astring_escape astring_string astring_sub astring_unsafe astring)
 (flags -w -27-32))
DUNEEOF

# uutf 1.0.4 (uses _tags/ocamlbuild, needs dune files)
cat > "$SRC_DIR/uutf/dune-project" << 'EOF'
(lang dune 3.0)
(name uutf)
(implicit_transitive_deps false)
(generate_opam_files true)
(package (name uutf) (synopsis "Unicode codec"))
EOF

cat > "$SRC_DIR/uutf/src/dune" << 'DUNEEOF'
(library
 (name uutf)
 (public_name uutf)
 (flags -w -27-32))
DUNEEOF

# ── Step 3: Remove unwanted packages and apply source-level fixes ──
echo "[build] Step 3: Removing unwanted packages and applying source fixes..."

# Remove alcotest sub-packages that need unavailable dependencies (async, lwt, mirage)
rm -rf "$SRC_DIR/src/alcotest-async" "$SRC_DIR/src/alcotest-lwt" "$SRC_DIR/src/alcotest-mirage"
# Mark them as allow_empty in dune-project (directories gone, but dune still expects the package defs)
sed -i '/name alcotest-async)/a\ (allow_empty)' "$SRC_DIR/dune-project"
sed -i '/name alcotest-lwt)/a\ (allow_empty)' "$SRC_DIR/dune-project"
sed -i '/name alcotest-mirage)/a\ (allow_empty)' "$SRC_DIR/dune-project"
# Remove cppo's ocamlbuild plugin (requires ocamlbuild library)
rm -rf "$SRC_DIR/cppo/ocamlbuild_plugin"
echo "[build] Removed alcotest-async/lwt/mirage dirs, cppo/ocamlbuild_plugin"

# fmt.mli: remove deprecated docstring (warning 50 on HarmonyOS)
sed -i 's/| color (\*\* deprecated \*) ]/| color ]/' "$SRC_DIR/fmt/src/fmt.mli"
# fmt.ml: remove deprecated docstring (same warning 50 issue)
sed -i 's/| color (\*\* deprecated \*) ]/| color ]/' "$SRC_DIR/fmt/src/fmt.ml"

# fmt.ml: add warning suppression annotations for HarmonyOS clang-built OCaml
python3 - "$SRC_DIR/fmt/src/fmt.ml" << 'PYEOF'
import sys
path = sys.argv[1]
with open(path, "r") as f:
    lines = f.readlines()

replacements = {
    "let invalid_arg' = invalid_arg\n": "let invalid_arg' = invalid_arg [@@warning \"-32\"]\n",
    'let err_str_formatter = "Format.str_formatter can\'t be set."\n': 'let err_str_formatter = "Format.str_formatter can\'t be set." [@@warning "-32"]\n',
    "let nop fmt ppf = ()\n": "let nop fmt ppf = () [@@warning \"-27\"]\n",
    "let queue ?sep pp_elt = iter Queue.iter pp_elt\n": "let queue ?sep pp_elt = iter Queue.iter pp_elt [@@warning \"-27\"]\n",
    "let stack ?sep pp_elt = iter Stack.iter pp_elt\n": "let stack ?sep pp_elt = iter Stack.iter pp_elt [@@warning \"-27\"]\n",
    "let attr (type a) enc dec = incr id; (!id, enc, dec)\n": "let attr (type a) enc dec = incr id; (!id, enc, dec) [@@warning \"-34\"]\n",
}

result = []
for line in lines:
    result.append(replacements.get(line, line))

with open(path, "w") as f:
    f.writelines(result)

print(f"[fmt.ml] Applied {sum(1 for l in lines if l in replacements)} warning annotations")
PYEOF

# fmt_tty.ml: add ~affix: label to is_infix call (warning 6 labels-omitted)
sed -i 's/is_infix "UTF-8"/is_infix ~affix:"UTF-8"/g' "$SRC_DIR/fmt/src/fmt_tty.ml"

# stdlib-shims: replace OCaml-syntax dune file (Jbuild_plugin.V1 requires 'ocaml' binary)
# The CI OCaml package lacks a working 'ocaml' interpreter, so we precompute the
# output for OCaml 4.14.1: missing_modules=[], library has no explicit modules,
# pervasives.ml is kept for backward compat and auto-discovered by dune.
cat > "$SRC_DIR/stdlib-shims/src/dune" << 'EOF'
(library
 (wrapped false)
 (name stdlib_shims)
 (public_name stdlib-shims))
EOF
# Also ensure dune-project and opam are S-expression compatible
cat > "$SRC_DIR/stdlib-shims/dune-project" << 'EOF'
(lang dune 2.0)
(name stdlib-shims)
(generate_opam_files true)
(package (name stdlib-shims))
EOF
touch "$SRC_DIR/stdlib-shims/stdlib-shims.opam"

# alcotest: remove (modes exe js) — js_of_ocaml not available on HarmonyOS
find "$SRC_DIR" -path "$SRC_DIR/.dune" -prune -o \( -name "dune" -o -name "dune.inc" \) -print | while read f; do
  if grep -q "(modes exe js)" "$f"; then
    sed -i 's/(modes exe js)/(modes exe)/g' "$f"
    echo "[build] Fixed (modes exe js) in $f"
  fi
done

# ── Step 4: Build alcotest + dependencies in monorepo workspace ──
echo "[build] Step 4: Building alcotest + dependencies..."
cd "$SRC_DIR"

# Use -j1 to avoid OOM on HarmonyOS
"$DUNE_BIN" build @install --root . -j1 2>&1 || { echo "[build] dune build failed"; exit 1; }

# ── Step 5: Copy artifacts to package folder ──
echo "[build] Step 5: Packaging artifacts..."
mkdir -p "$PKG_DIR/lib/alcotest"
cp -rL "$SRC_DIR/_build/install/default/lib/alcotest/"* "$PKG_DIR/lib/alcotest/"

# Verify key files
PASS=0; MISSING=0
for f in \
  lib/alcotest/alcotest.cma lib/alcotest/alcotest.cmxa lib/alcotest/alcotest.a \
  lib/alcotest/alcotest.cmi lib/alcotest/libalcotest_stubs.a lib/alcotest/META \
  lib/alcotest/engine/alcotest_engine.cma lib/alcotest/engine/alcotest_engine.cmxa \
  lib/alcotest/engine/alcotest_engine.a lib/alcotest/stdlib_ext/alcotest_stdlib_ext.cma \
  lib/alcotest/stdlib_ext/alcotest_stdlib_ext.cmxa lib/alcotest/stdlib_ext/alcotest_stdlib_ext.a; do
  if [ -f "$PKG_DIR/$f" ]; then
    PASS=$((PASS + 1))
  else
    MISSING=$((MISSING + 1))
    echo "[build] MISSING: $f"
  fi
done

echo "[build] alcotest artifact check: $PASS passed, $MISSING missing"
if [ "$MISSING" -gt 0 ]; then
  echo "[build] ERROR: Some key artifacts are missing!"
  exit 1
fi

echo "[build] Build completed successfully!"
