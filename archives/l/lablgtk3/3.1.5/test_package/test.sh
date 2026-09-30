#!/bin/sh
# lablgtk3/3.1.5 test_package probes (OHOS aarch64).
# Invoked with an EXPLICIT interpreter from test_package/conanfile.py
# (OHOS hmmac refuses direct shebang execution — findlib/1.9.8 pattern).
#
# Usage: /bin/sh test.sh <pkg_lib> <ocaml_bin> <ocaml_stdlib> \
#                       <findlib_bin> <findlib_sitelib> <build_dir>
#
# T0  package structure assertions (findlib tree + vendored deps)
# T1  ocamlfind resolution of lablgtk3 / cairo2 / camlp-streams
# T2  OHOS no-display API probe: compile+RUN a native consumer linking
#     lablgtk3 stubs + cairo2 + glib; pure-glib calls, no gtk_init/display
#     (E463/E471 display-test classification, OHOS-specific added test)
# T3  upstream run-test parity: compile a GTK window consumer (build only;
#     running needs a display server, unavailable on OHOS)
set -e

PKG_LIB="$1"
OCAML_BIN="$2"
OCAML_STDLIB="$3"
FINDLIB_BIN="$4"
FINDLIB_SITELIB="$5"
BUILD_DIR="$6"

# ── T0: package structure assertions ──
for f in \
    "$PKG_LIB/lablgtk3/META" \
    "$PKG_LIB/lablgtk3/lablgtk3.cma" \
    "$PKG_LIB/lablgtk3/lablgtk3.cmxa" \
    "$PKG_LIB/lablgtk3/lablgtk3.a" \
    "$PKG_LIB/lablgtk3/wrappers.h" \
    "$PKG_LIB/camlp-streams/META" \
    "$PKG_LIB/cairo2/META" \
    "$PKG_LIB/stublibs/dllcairo_stubs.so"
do
    if [ ! -f "$f" ]; then
        echo "[fail] T0: missing artifact: $f"
        exit 1
    fi
done
echo "T0 PASS: package structure complete (8 artifacts)"

# ── explicit findlib configuration (no ambient device state) ──
LD_CONF="$BUILD_DIR/ld.conf"
printf '%s\n' "$OCAML_STDLIB/stublibs" > "$LD_CONF"
FINDLIB_CONF="$BUILD_DIR/ocamlfind.conf"
{
    printf 'destdir = "%s"\n' "$BUILD_DIR"
    # findlib.conf: directory list separated by newlines
    printf 'path = "%s\n%s\n%s"\n' \
        "$OCAML_STDLIB" "$FINDLIB_SITELIB" "$PKG_LIB"
    printf 'ldconf = "%s"\n' "$LD_CONF"
} > "$FINDLIB_CONF"

OCAMLLIB="$OCAML_STDLIB"
OCAMLRUN="$OCAML_BIN/ocamlrun"
OCAMLPATH="$OCAML_STDLIB:$FINDLIB_SITELIB:$PKG_LIB"
OCAMLFIND_CONF="$FINDLIB_CONF"
OCAMLFIND_LDCONF="$LD_CONF"
PATH="$OCAML_BIN:$FINDLIB_BIN:$PATH"
export OCAMLLIB OCAMLRUN OCAMLPATH OCAMLFIND_CONF OCAMLFIND_LDCONF PATH

# ── T1: ocamlfind resolution ──
for pkg in lablgtk3 cairo2 camlp-streams; do
    "$FINDLIB_BIN/ocamlfind" query "$pkg"
done
echo "T1 PASS: ocamlfind resolves lablgtk3/cairo2/camlp-streams"

# ── T2: OHOS no-display API probe (compile + RUN, native ELF) ──
cat > "$BUILD_DIR/probe_glib.ml" <<'PROBE_EOF'
let () =
  let is_utf8, charset = Glib.Convert.get_charset () in
  Printf.printf "OHOS probe: charset=%s utf8=%b\n" charset is_utf8;
  assert (charset <> "");
  (* pure UTF-8 round trip inside glib, no display server involved *)
  let s = Glib.Utf8.from_unichar 0x4e2d in
  assert (s = "\xe4\xb8\xad");
  assert (Glib.Utf8.validate s);
  assert (Glib.Utf8.length s = 1);
  let pos = ref 0 in
  let u = Glib.Utf8.to_unichar s ~pos in
  assert (u = 0x4e2d);
  assert (!pos = 3);
  assert (Glib.Utf8.validate (Glib.Utf8.from_unichar 0xe9));
  print_endline "OHOS probe: Glib UTF-8 round-trip OK (lablgtk3 stubs + glib linked and executed)"
PROBE_EOF
cd "$BUILD_DIR"
"$FINDLIB_BIN/ocamlfind" ocamlopt -package lablgtk3 -linkpkg probe_glib.ml -o probe_glib
# conanrun env (VirtualRunEnv) provides LD_LIBRARY_PATH for gtk/cairo libs
./probe_glib
echo "T2 PASS: no-display API probe executed on OHOS"

# ── T3: upstream run-test parity (build-only, E471 classification) ──
cat > "$BUILD_DIR/gtk_window_probe.ml" <<'GTK_EOF'
let () =
  let win = GWindow.window ~title:"OHOS build probe" ~border_width:8 () in
  let btn = GButton.button ~label:"Hello OHOS" ~packing:win#add () in
  ignore (btn#connect#clicked ~callback:(fun () -> prerr_endline "clicked"));
  ignore (win#connect#destroy ~callback:GMain.Main.quit);
  ignore win#show;
  print_endline "GTK window consumer compiled and linked (not run: display required)"
GTK_EOF
"$FINDLIB_BIN/ocamlfind" ocamlopt -package lablgtk3 -linkpkg gtk_window_probe.ml -o gtk_window_probe
echo "T3 PASS: GTK window consumer compiled+linked (build-only; display-dependent execution excluded per E471)"
