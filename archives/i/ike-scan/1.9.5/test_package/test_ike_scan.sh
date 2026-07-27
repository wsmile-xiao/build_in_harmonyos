#!/bin/sh
set -eu
(set -o pipefail) 2>/dev/null && set -o pipefail || true
ike-scan --version > ike-scan-version.txt 2>&1
psk-crack --help > psk-crack-help.txt 2>&1
