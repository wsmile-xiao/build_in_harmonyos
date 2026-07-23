#!/data/service/hnp/bin/bash
set -euo pipefail

work_dir="${TMPDIR:-${TEMP:-$PWD}}/docx2txt-test-$$"
trap 'rm -rf "$work_dir"' EXIT
mkdir -p "$work_dir"

cat > "$work_dir/sample.docx.b64" <<'EOF'
UEsDBBQAAAAIAHhq8lz/Bso5rgAAAO0AAAARAAAAd29yZC9kb2N1bWVudC54bWxFjjEOwjAMRa8SZacpDAhVbdkQGwscICQGKjV2FBva3p6kDCzPsr71/NvjHEb1gcQDYae3Va0VoCM/4LPTt+tpc9CKxaK3IyF0egHWx76dGk/uHQBFZQFyM3X6JRIbY9i9IFiuKALm7EEpWMlrepqJko+JHDBnfxjNrq73JtgBdVHeyS9lxoJUIP0lW842BcJF5ZfzTmZRjzc6yYXtqARYWlMuC9PKuPJnM/+m/RdQSwMEFAAAAAgAeGryXIYbH592AAAAjAAAABwAAAB3b3JkL19yZWxzL2RvY3VtZW50LnhtbC5yZWxzTYxBDsIgEAC/QvZuQQ/GmNLe+gCjD9jQFYiwEJYY/b0cPU4mM/P6yUm9qUksbOE4GVDEruyRvYXHfTtcQElH3jEVJgtfEliX+UYJ+0gkxCpqPFgshN7rVWtxgTLKVCrxMM/SMvaBzeuK7oWe9MmYs27/D9DLD1BLAQIUABQAAAAIAHhq8lz/Bso5rgAAAO0AAAARAAAAAAAAAAAAAACAAQAAAAB3b3JkL2RvY3VtZW50LnhtbFBLAQIUABQAAAAIAHhq8lyGGx+fdgAAAIwAAAAcAAAAAAAAAAAAAACAAd0AAAB3b3JkL19yZWxzL2RvY3VtZW50LnhtbC5yZWxzUEsFBgAAAAACAAIAiQAAAI0BAAAAAA==
EOF

perl_bin="$(command -v perl 2>/dev/null || true)"
if [ -z "$perl_bin" ] && [ -x /data/service/hnp/bin/perl ]; then
    perl_bin=/data/service/hnp/bin/perl
fi
if [ -z "$perl_bin" ]; then
    echo "[fail] perl not found"
    exit 1
fi

"$perl_bin" -MMIME::Base64 -0777 -ne 'print decode_base64($_)' \
    "$work_dir/sample.docx.b64" > "$work_dir/sample.docx"

docx2txt_bin="${DOCX2TXT_BIN:-$(command -v docx2txt 2>/dev/null || true)}"
if [ -z "$docx2txt_bin" ]; then
    echo "[fail] docx2txt not found"
    exit 1
fi

output="$work_dir/output.txt"
"$perl_bin" "$docx2txt_bin" "$work_dir/sample.docx" "$output"
grep -F "OpenHarmony docx2txt functional test" "$output" >/dev/null
echo "[ok] docx2txt extracted text from a DOCX file"
