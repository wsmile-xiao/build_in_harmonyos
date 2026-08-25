#!/bin/sh
# test_pod2man.sh — smoke test for pod2man (podlators) 6.0.2
# Creates a minimal POD file, converts it with pod2man, and verifies the output.
set -eu

POD2MAN="$1"
TMPDIR_TEST="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_TEST"' EXIT

POD_FILE="$TMPDIR_TEST/test.pod"
OUT_FILE="$TMPDIR_TEST/test.1"

cat > "$POD_FILE" << 'POD'
=head1 NAME

test - A test POD file

=head1 DESCRIPTION

This is a test.

=cut
POD

perl "$POD2MAN" "$POD_FILE" "$OUT_FILE"

# Verify output file exists and contains man page markers
if [ ! -f "$OUT_FILE" ]; then
    echo "FAIL: pod2man did not produce output file"
    exit 1
fi

if ! grep -q '\.TH' "$OUT_FILE"; then
    echo "FAIL: pod2man output missing .TH header"
    exit 1
fi

echo "OK: pod2man conversion test passed"
