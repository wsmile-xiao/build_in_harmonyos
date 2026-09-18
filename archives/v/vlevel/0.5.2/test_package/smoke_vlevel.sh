#!/bin/sh
# vlevel-bin consumer smoke test (R34: runs the packaged binary and asserts
# behavior). Feeds 300000 constant low-amplitude mono int16 samples through
# the filter and checks: exit 0, stream framing preserved (same byte count),
# and the quiet signal got amplified (dynamic normalization actually ran).
BIN="$1"
TMP=$(mktemp -d) || exit 1
trap 'rm -rf "$TMP"' EXIT

python3 -c "
import struct, sys
sys.stdout.buffer.write(struct.pack('<h', 1000) * 300000)
" > "$TMP/in.raw" || exit 1

"$BIN" --channels 1 < "$TMP/in.raw" > "$TMP/out.raw" 2>"$TMP/err.txt"
rc=$?
if [ $rc -ne 0 ]; then
    echo "vlevel smoke: filter exited $rc" >&2
    head -3 "$TMP/err.txt" >&2
    exit 1
fi

python3 - "$TMP/in.raw" "$TMP/out.raw" <<'PYEOF'
import struct, sys
inb = open(sys.argv[1], "rb").read()
outb = open(sys.argv[2], "rb").read()
if len(inb) != len(outb):
    print(f"framing broken: in={len(inb)} out={len(outb)}", file=sys.stderr)
    sys.exit(1)
ins = struct.unpack(f"<{len(inb)//2}h", inb)
outs = struct.unpack(f"<{len(outb)//2}h", outb)
if max(outs) <= max(ins):
    print(f"no amplification: in_max={max(ins)} out_max={max(outs)}", file=sys.stderr)
    sys.exit(1)
print(f"vlevel smoke ok: {len(ins)} samples, in_max={max(ins)} -> out_max={max(outs)}")
PYEOF
