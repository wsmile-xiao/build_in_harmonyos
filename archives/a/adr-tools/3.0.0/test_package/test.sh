#!/usr/bin/env bash
# test_package/test.sh — smoke test for adr-tools CLI
set -euo pipefail

echo "[test] adr help"
adr help && echo "✅ adr help OK" || {
    echo "❌ adr help failed"
    exit 1
}

echo "[test] adr init"
adr init doc/adr && echo "✅ adr init OK" || {
    echo "❌ adr init failed"
    exit 1
}

echo "[test] adr new"
adr new "Test Decision" && echo "✅ adr new OK" || {
    echo "❌ adr new failed"
    exit 1
}

# Verify the ADR file was created (adr init creates 0001, adr new creates 0002)
if [ -f "doc/adr/0002-test-decision.md" ]; then
    echo "✅ ADR file created: doc/adr/0002-test-decision.md"
else
    echo "❌ ADR file not found"
    exit 1
fi

echo "[test] adr-tools smoke test: PASS"
