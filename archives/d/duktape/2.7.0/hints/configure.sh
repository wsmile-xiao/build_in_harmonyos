#!/bin/sh
# Hints for duktape - Makefile project, no autotools configure
# Duktape uses Makefile.sharedlibrary for building

# For G0 clean-verify: create a dummy configure script that accepts --prefix
# and exits 0, since duktape doesn't use autotools

PREFIX=""
for arg in "$@"; do
    case "$arg" in
        --prefix=*) PREFIX="${arg#--prefix=}" ;;
        *) ;;
    esac
done

echo "configure: duktape uses Makefile.sharedlibrary (no configure needed)"
echo "Configured for prefix: $PREFIX"
exit 0
