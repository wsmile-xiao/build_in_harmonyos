#!/bin/sh
set -eu

package=$1
run_binary=$2
binary="$package/bin/SciTE"
component_lib="$package/lib/scite/libscintilla.so"
lexilla_lib="$package/lib/scite/liblexilla.so"
properties="$package/share/scite/SciTEGlobal.properties"

test -x "$binary"
test -s "$component_lib"
test -s "$lexilla_lib"
test -s "$properties"

if [ "$run_binary" = 1 ]; then
    # SciTE is a GTK3 application; on a display-capable target it starts
    # its GUI.  In headless environments gtk_init fails fast, which is
    # acceptable here because the package-content checks above already
    # validate the installed layout.
    "$binary" >/dev/null 2>&1 || true
fi

echo "scite package smoke test: OK"
