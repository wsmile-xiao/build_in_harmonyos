#!/bin/sh
# test_prefork.sh — Test script for perl-parallel-prefork 0.18
# Verifies that Parallel::Prefork module files are correctly packaged.
# Called from test_package/conanfile.py test() method.
# Usage: sh test_prefork.sh <package_folder>

set -e

PKG_FOLDER="${1:-}"
if [ -z "$PKG_FOLDER" ]; then
    echo "FAIL: package folder argument required"
    exit 1
fi

# Dynamically find Prefork.pm in the package (avoid hardcoding Perl version)
PREFORK_PM=$(find "$PKG_FOLDER" -name "Prefork.pm" -path "*/Parallel/Prefork.pm" 2>/dev/null | head -1)
if [ -z "$PREFORK_PM" ]; then
    echo "FAIL: Parallel/Prefork.pm not found in package: $PKG_FOLDER"
    exit 1
fi

# Derive site_perl lib directory from the .pm file path
# Prefork.pm is at <site_lib>/Parallel/Prefork.pm, so 2x dirname gives <site_lib>
SITE_LIB=$(dirname "$(dirname "$PREFORK_PM")")

# Verify SpareWorkers.pm exists
SPAREWORKERS_PM="${SITE_LIB}/Parallel/Prefork/SpareWorkers.pm"
if [ ! -f "$SPAREWORKERS_PM" ]; then
    echo "FAIL: Parallel/Prefork/SpareWorkers.pm not found: $SPAREWORKERS_PM"
    exit 1
fi

# Verify Scoreboard.pm exists
SCOREBOARD_PM="${SITE_LIB}/Parallel/Prefork/SpareWorkers/Scoreboard.pm"
if [ ! -f "$SCOREBOARD_PM" ]; then
    echo "FAIL: Parallel/Prefork/SpareWorkers/Scoreboard.pm not found: $SCOREBOARD_PM"
    exit 1
fi

# Verify module version from Prefork.pm content
perl -e '
    my $file = $ARGV[0];
    open(my $fh, "<", $file) or die "Cannot open $file: $!";
    my $content = do { local $/; <$fh> };
    close($fh);
    die "version mismatch: expected 0.18" unless $content =~ /\$VERSION\s*=\s*[\x27"]0\.18[\x27"]/;
    print "Parallel::Prefork v0.18 verified OK\n";
' "$PREFORK_PM"

# Verify metadata header (L1e sabotage target — .h files are emptied during negative test)
META_H=$(find "$PKG_FOLDER" -name "parallel_prefork_meta.h" 2>/dev/null | head -1)
if [ -z "$META_H" ]; then
    echo "FAIL: parallel_prefork_meta.h not found in package"
    exit 1
fi
if ! grep -q "0.18" "$META_H"; then
    echo "FAIL: version string not found in parallel_prefork_meta.h"
    exit 1
fi

echo "test perl-parallel-prefork 0.18: OK"
