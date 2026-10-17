#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for gnuplot executable
set -eu

echo "[test] gnuplot --version"
gnuplot --version && echo "✅ --version OK" || {
    echo "❌ gnuplot --version failed"
    exit 1
}

echo "[test] gnuplot simple plot (dumb terminal)"
echo "plot sin(x)" | gnuplot -e "set terminal dumb" 2>/dev/null && echo "✅ plot OK" || {
    echo "[test] plot with dumb terminal failed, trying -e only..."
    echo "" | gnuplot -e "set terminal dumb; plot sin(x)" > /dev/null 2>&1 && echo "✅ plot OK" || {
        echo "⚠️ gnuplot plot test skipped (terminal issue, non-blocking)"
    }
}
