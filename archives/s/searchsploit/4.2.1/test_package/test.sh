#!/data/service/hnp/bin/bash
set -euo pipefail

echo "[test] searchsploit -h (help screen, exits with code 2 by design)"
# searchsploit -h exits with code 2 by design, capture output and ignore exit code
output=$(searchsploit -h 2>&1) || true
echo "$output" | grep -q "Usage:" && echo "✅ help screen OK" || {
    echo "❌ searchsploit -h did not show usage"
    exit 1
}

echo "[test] searchsploit basic search: afd windows local"
output=$(searchsploit --disable-colour afd windows local 2>&1)
echo "$output" | grep -qi "afd" && echo "✅ search returned expected results" || {
    echo "❌ search did not return expected results"
    echo "$output" | head -5
    exit 1
}

echo "[test] searchsploit CVE search: CVE-2021-44228 (Log4j)"
output=$(searchsploit --disable-colour --cve 2021-44228 2>&1)
echo "$output" | grep -qi "log4j" && echo "✅ CVE search OK" || {
    echo "❌ CVE search did not return expected results"
    echo "$output" | head -5
    exit 1
}

echo "[test] searchsploit JSON output: -j 55555"
output=$(searchsploit --disable-colour -j 55555 2>&1)
echo "$output" | grep -q '"SEARCH"' && echo "✅ JSON output OK" || {
    echo "❌ JSON output not valid"
    echo "$output" | head -5
    exit 1
}

echo "✅ All searchsploit tests passed"
