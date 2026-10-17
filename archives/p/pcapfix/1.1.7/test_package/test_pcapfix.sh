#!/data/service/hnp/bin/bash
# pcapfix functional smoke test (consumer view).
#
# Scenarios:
#  1. no arguments -> "Usage:" banner on stdout, non-zero exit
#     (upstream has no -h/--help/--version flags)
#  2. repair a pcap whose 4 global-header magic bytes were zeroed:
#     - pcapfix exits 0 and prints "[+] SUCCESS: 1 Corruption(s) fixed!"
#     - output file exists, first 4 bytes restored to d4 c3 b2 a1
#       (or a1 b2 c3 d4 on the swapped variant)
#     - repair rewrites the header in place: output size == input size
#
# Only bash builtins + coreutils (head/cmp/wc/grep/mkdir/rm) are required.
set -e
set -u

if [ $# -lt 1 ]; then
    echo "usage: test_pcapfix.sh <package_bin_dir>" >&2
    exit 2
fi
BIN="$1"
P="$BIN/pcapfix"

[ -x "$P" ] || { echo "pcapfix binary not found/executable: $P" >&2; exit 1; }

# OHOS /tmp is read-only; runner exports TMPDIR, fall back to $HOME/tmp
tmp="${TMPDIR:-$HOME/tmp}/pcapfix_smoke.$$"
rm -rf "$tmp"
mkdir -p "$tmp"
trap 'rm -rf "$tmp"' EXIT

# ---- Scenario 1: no arguments -> usage banner, non-zero exit ----
if "$P" > "$tmp/noargs.out" 2>&1; then
    echo "pcapfix without arguments unexpectedly exited 0" >&2
    exit 1
fi
grep -q 'Usage' "$tmp/noargs.out" || {
    echo "no usage banner printed; got:" >&2; cat "$tmp/noargs.out" >&2; exit 1; }

# ---- Scenario 2: repair a pcap with zeroed global-header magic ----
# Classic pcap, little endian: 24B global header (magic d4c3b2a1, v2.4,
# thiszone 0, sigfigs 0, snaplen 65535, linktype 1=Ethernet) + 2 packets,
# each 16B packet header (ts 0, caplen=len=60) + 60B payload.
hdr_rest='\x02\x00\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xff\x00\x00\x01\x00\x00\x00'
pkt_hdr='\x5f\xe2\x24\x5f\x00\x00\x00\x00\x3c\x00\x00\x00\x3c\x00\x00\x00'

gen_packets() { # append 2 x (16B header + 60B payload) to $1
    local f="$1" i
    for i in 1 2; do
        printf "$pkt_hdr" >> "$f"
        printf 'A%.0s' {1..60} >> "$f"
    done
}

# intact reference file
printf "\xd4\xc3\xb2\xa1$hdr_rest" > "$tmp/good.pcap"
gen_packets "$tmp/good.pcap"

# damaged copy: identical except the first 4 magic bytes are zeroed
printf "\x00\x00\x00\x00$hdr_rest" > "$tmp/damaged.pcap"
gen_packets "$tmp/damaged.pcap"

# sanity of the fixture itself (24 + 2*(16+60) = 176 bytes)
[ "$(wc -c < "$tmp/damaged.pcap")" -eq 176 ] || {
    echo "test fixture has unexpected size" >&2; exit 1; }

"$P" -o "$tmp/fixed.pcap" "$tmp/damaged.pcap" > "$tmp/fix.out" 2>&1 || {
    echo "pcapfix exited non-zero:" >&2; cat "$tmp/fix.out" >&2; exit 1; }

grep -q 'SUCCESS: 1 Corruption(s) fixed' "$tmp/fix.out" || {
    echo "missing SUCCESS banner; got:" >&2; cat "$tmp/fix.out" >&2; exit 1; }

[ -f "$tmp/fixed.pcap" ] || { echo "fixed output file missing" >&2; exit 1; }

# magic must be restored (either endianness)
head -c 4 "$tmp/fixed.pcap" > "$tmp/got4.bin"
printf '\xd4\xc3\xb2\xa1' > "$tmp/want_le.bin"
printf '\xa1\xb2\xc3\xd4' > "$tmp/want_be.bin"
cmp -s "$tmp/want_le.bin" "$tmp/got4.bin" || cmp -s "$tmp/want_be.bin" "$tmp/got4.bin" || {
    echo "magic bytes not restored in fixed.pcap" >&2; exit 1; }

# repair rewrites header fields in place: the size must not change
[ "$(wc -c < "$tmp/fixed.pcap")" -eq "$(wc -c < "$tmp/damaged.pcap")" ] || {
    echo "fixed.pcap size mismatch" >&2; exit 1; }

echo "pcapfix smoke test OK"
