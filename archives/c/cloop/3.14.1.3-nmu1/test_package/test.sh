#!/usr/bin/env bash
set -euo pipefail

work="$(pwd)/cloop-consumer-data"
rm -rf "$work"
mkdir -p "$work"
input="$work/input.bin"
image="$work/input.cloop"
output="$work/output.bin"

python3 - "$input" <<'PY'
from pathlib import Path
import sys
Path(sys.argv[1]).write_bytes((b"HarmonyOS cloop consumer regression\\n" * 256)[:8192])
PY

create_compressed_fs -m -B 65536 -s 8192 "$input" "$image"
extract_compressed_fs "$image" "$output"

python3 - "$input" "$output" <<'PY'
from pathlib import Path
import sys
input_data = Path(sys.argv[1]).read_bytes()
output_data = Path(sys.argv[2]).read_bytes()
assert output_data[:len(input_data)] == input_data
assert len(output_data) == 65536
assert output_data[len(input_data):] == bytes(len(output_data) - len(input_data))
PY

echo "cloop HarmonyOS consumer round-trip: PASS"
