# test_package/test.sh — CLI checks for the packaged scws binaries.
# Required env (exported by test_package/conanfile.py):
#   SCWS_PKG  — conan package folder of the tested scws package
#   TEST_SRC  — test_package source dir (dict.txt lives here)
#   TEST_WORK — writable scratch dir
set -euo pipefail

GEN_DICT="$SCWS_PKG/bin/scws-gen-dict"
SCWS_BIN="$SCWS_PKG/bin/scws"
WORK="$TEST_WORK/scws-cli-test"
mkdir -p "$WORK"

echo "=== scws 1.2.3 CLI test ==="

# C1: scws-gen-dict converts a plain-text dict into a loadable xdb
echo "[C1] scws-gen-dict dict.txt -> cli_dict.xdb"
"$GEN_DICT" -c utf8 -i "$TEST_SRC/dict.txt" -o "$WORK/cli_dict.xdb"
if [ -s "$WORK/cli_dict.xdb" ]; then
    echo "[PASS] C1 scws-gen-dict produced non-empty xdb"
else
    echo "[FAIL] C1 scws-gen-dict produced no xdb"
    exit 1
fi

# C2: scws CLI segments a real sentence with the generated xdb
echo "[C2] scws -c utf8 -d cli_dict.xdb segmentation"
out=$("$SCWS_BIN" -c utf8 -d "$WORK/cli_dict.xdb" -i "我爱北京天安门")
echo "       got: $out"
case "$out" in
    *"我 爱 北京 天安门"*)
        echo "[PASS] C2 scws CLI segmentation 我爱北京天安门"
        ;;
    *)
        echo "[FAIL] C2 unexpected segmentation output"
        exit 1
        ;;
esac

echo "=== all CLI checks PASSED ==="
