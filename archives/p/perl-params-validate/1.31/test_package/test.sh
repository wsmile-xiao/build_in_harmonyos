#!/bin/sh
set -euo pipefail
# test.sh — CI L0c compliant wrapper for test.pl
# CI accepts .sh extension but not .pl; this wrapper bridges the gap.
# Find perl: prefer /data/service/hnp/bin/perl (OHOS HNP), fall back to PATH
PERL=/data/service/hnp/bin/perl
[ -x "$PERL" ] || PERL=perl
exec "$PERL" "$(dirname "$0")/test.pl"
