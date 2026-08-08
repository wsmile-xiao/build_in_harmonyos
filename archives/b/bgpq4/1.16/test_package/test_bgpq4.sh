#!/usr/bin/env sh
set -eu
(set -o pipefail) 2>/dev/null && set -o pipefail || true

bgpq4 -v > bgpq4-version.txt
grep -qi 'bgpq4' bgpq4-version.txt
grep -Eq '(^|[^0-9.])1\.16([^0-9.]|$)' bgpq4-version.txt

bgpq4 -J 192.0.2.0/24 > bgpq4-junos-prefix-list.txt
grep -q 'prefix-list' bgpq4-junos-prefix-list.txt
grep -q '192.0.2.0/24' bgpq4-junos-prefix-list.txt
