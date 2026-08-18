#!/bin/sh
# test_package/test_stash.sh — L1 smoke test wrapper for perl-package-stash
# Runs test_stash.pl which tests real Package::Stash API.
set -eu

script_dir=$(dirname "$0")

# Package::Stash requires Module::Implementation at runtime, which in turn
# depends on Module::Runtime and Try::Tiny. These are pure-Perl modules
# not available on CI workers. Bundle them in test_package/lib/ so the
# test is self-contained.

# Pass conan PERL5LIB paths as -I flags to ensure the conan package's
# modules are found first. The system perl wrapper may overwrite PERL5LIB,
# so -I flags (command-line args) are more reliable than env vars.
set --
OLDIFS="$IFS"
IFS=':'
for dir in ${PERL5LIB:-}; do
    if [ -d "$dir" ]; then
        set -- "$@" "-I$dir"
    fi
done
IFS="$OLDIFS"

perl "$@" -I"$script_dir/lib" "$script_dir/test_stash.pl"