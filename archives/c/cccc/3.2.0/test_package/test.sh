#!/data/service/hnp/bin/bash
# test_package/test.sh — behavioral test for the cccc executable (R34)
# Runs in conanrun env (PATH includes the installed bin/): feeds a small C++
# sample through the counter and asserts the metric reports are produced.
set -euo pipefail

OUT=$(mktemp -d)
trap 'rm -rf "$OUT"' EXIT

cat > "$OUT/sample.cpp" << "EOC"
#include <string>
int main() {
    std::string s = "hello";
    return s.size() == 5 ? 0 : 1;
}
EOC

echo "[test] cccc parses the sample and writes reports"
cccc --lang=c++ --outdir="$OUT/report" "$OUT/sample.cpp" > "$OUT/run.txt" 2>&1
cat "$OUT/run.txt"

echo "[test] asserting metric report outputs"
test -f "$OUT/report/cccc.html"
test -f "$OUT/report/cccc.xml"
test -f "$OUT/report/cccc.db"
grep -q "Primary HTML output" "$OUT/run.txt"
grep -q "sample.cpp" "$OUT/report/cccc.html"
echo "OK: cccc generated HTML/XML/DB metric reports for the sample"
