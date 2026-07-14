#!/data/service/hnp/bin/bash
# test_package/test.sh — functional test for the mktorrent binary.
# Drives mktorrent to build a real BitTorrent metainfo (.torrent) file from a
# sample payload and validates the output. No network access is needed: the
# announce URL (-a) is only stored in the metainfo, never contacted.
set -euo pipefail

WORK="$(pwd)/_mktorrent_test"
rm -rf "$WORK"
mkdir -p "$WORK"
cd "$WORK"

# sample payload
printf 'hello harmony mktorrent\n' > input.txt

# create the metainfo file (-a sets the tracker URL, -o the output path)
mktorrent -a http://example.com/announce -o out.torrent input.txt

# the metainfo file must exist and be non-empty
test -s out.torrent
# bencode dictionaries start with 'd'
test "$(head -c1 out.torrent)" = "d"

echo "[ok] mktorrent produced out.torrent ($(wc -c < out.torrent) bytes)"
