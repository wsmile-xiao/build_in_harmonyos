#!/usr/bin/env bash
set -euo pipefail

binary="${MENCODER_BIN:-mencoder}"
output="$($binary -ovc help 2>&1)"
printf '%s\n' "$output"
grep -q "Available codecs:" <<<"$output"
grep -q "lavc" <<<"$output"

tmpbase="${TMPDIR:-$HOME/tmp}"
mkdir -p "$tmpbase"
tmpdir="$(mktemp -d "$tmpbase/mencoder-test.XXXXXX")"
trap 'rm -rf "$tmpdir"' EXIT
python3 -c 'import sys; w=h=16; sys.stdout.buffer.write(bytes([16])*(w*h)); sys.stdout.buffer.write(bytes([128])*((w//2)*(h//2)*2))' > "$tmpdir/frame.yuv"
"$binary" "$tmpdir/frame.yuv" -demuxer rawvideo \
    -rawvideo fps=1:w=16:h=16:format=i420 \
    -ovc lavc -lavcopts vcodec=mpeg4 -nosound -of avi \
    -o "$tmpdir/output.avi" >/dev/null 2>&1
[ -s "$tmpdir/output.avi" ]
