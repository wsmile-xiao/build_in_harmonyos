#!/bin/sh
# test_package/test_deprecationmanager.sh — L1 smoke test wrapper for perl-package-deprecationmanager
# Runs test_deprecationmanager.pl which tests real Package::DeprecationManager API.
set -eu

script_dir=$(dirname "$0")

# Extract conan-managed paths from PERL5LIB and prepend them via -I.
# This ensures the module is loaded from the Conan package, not system installs.
# When CI's L1e check sabotages the package lib/, the conan path no longer
# exists, causing the test to fail — proving real dependency (R34).
CONAN_INCLUDES=""
OLDIFS="$IFS"
IFS=':'
for p in ${PERL5LIB:-}; do
    case "$p" in
        *.conan2*)
            if [ -d "$p" ]; then
                CONAN_INCLUDES="$CONAN_INCLUDES -I$p"
            fi
            ;;
    esac
done
IFS="$OLDIFS"

# $CONAN_INCLUDES is intentionally unquoted for word-splitting into separate -I args.
# Conan cache paths do not contain spaces, so this is safe.
# shellcheck disable=SC2086
perl $CONAN_INCLUDES "$script_dir/test_deprecationmanager.pl"
