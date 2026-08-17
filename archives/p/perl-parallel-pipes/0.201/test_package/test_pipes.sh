#!/bin/sh
# test_pipes.sh — Test script for perl-parallel-pipes 0.201
# Verifies that Parallel::Pipes module files are correctly packaged and loadable.
# Called from test_package/conanfile.py test() method.
# Usage: sh test_pipes.sh <package_folder>

set -e

PKG_FOLDER="${1:-}"
if [ -z "$PKG_FOLDER" ]; then
    echo "FAIL: package folder argument required"
    exit 1
fi

# Find Parallel/Pipes.pm in the package
PIPES_PM=$(find "$PKG_FOLDER" -name "Pipes.pm" -path "*/Parallel/Pipes.pm" 2>/dev/null | head -1)
if [ -z "$PIPES_PM" ]; then
    echo "FAIL: Parallel/Pipes.pm not found in package: $PKG_FOLDER"
    exit 1
fi

# Derive Perl lib root from the .pm file path
# Pipes.pm is at <lib_root>/Parallel/Pipes.pm, so 2x dirname gives <lib_root>
LIB_ROOT=$(dirname "$(dirname "$PIPES_PM")")

# Verify Parallel/Pipes/App.pm exists
APP_PM="${LIB_ROOT}/Parallel/Pipes/App.pm"
if [ ! -f "$APP_PM" ]; then
    echo "FAIL: Parallel/Pipes/App.pm not found: $APP_PM"
    exit 1
fi

# Load test: use Parallel::Pipes and Parallel::Pipes::App, create an instance
PERL5LIB="$LIB_ROOT" perl -e '
    use Parallel::Pipes;
    use Parallel::Pipes::App;
    my $pipes = Parallel::Pipes->new(3);
    print "Parallel::Pipes loaded and instantiated OK\n";
'

echo "test perl-parallel-pipes 0.201: OK"
