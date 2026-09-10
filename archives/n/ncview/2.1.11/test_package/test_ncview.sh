#!/bin/sh
# Functional smoke test for the packaged ncview executable.
#
# ncview is an X11 GUI tool and the CI/device test environment is headless:
# ncview initializes the X toolkit during argument handling (in_parse_args)
# BEFORE it reports anything about input files. Without a display it must
# therefore exit non-zero, printing its version banner and Xt's
# "Can't open display" diagnostic. That still exercises: ELF loading of the
# whole dynamic dependency chain (libnetcdf, libX11, libXt, libXext, libXpm —
# the vendored Xaw/Xmu/udunits/expat are static), ncview's runtime banner,
# and the X11 error path.
#
# Usage: test_ncview.sh <ncview-binary> <bogus-file> <errlog> <ld-library-path>
set -eu

ncview_bin=$1
bogus=$2
errlog=$3
ldpath=$4

LD_LIBRARY_PATH="$ldpath${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export LD_LIBRARY_PATH

set +e
"$ncview_bin" "$bogus" > "$errlog" 2>&1
rc=$?
set -e

if [ "$rc" -eq 0 ]; then
    echo "FAIL: ncview unexpectedly succeeded without an X display" >&2
    exit 1
fi

ok=1
grep -q "Ncview 2.1.11" "$errlog" || { echo "FAIL: version banner missing" >&2; ok=0; }
grep -qi "can't open display" "$errlog" || { echo "FAIL: X11 display diagnostic missing" >&2; ok=0; }

if [ "$ok" -eq 1 ]; then
    echo "ncview smoke test OK (exit=$rc, banner + X11 diagnostic present, dynamic deps resolved)"
else
    echo "--- ncview output ---" >&2
    cat "$errlog" >&2
    exit 1
fi
