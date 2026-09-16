#!/data/service/hnp/bin/bash
# test_package/test.sh — consumer smoke test for aris (GTK3 application)
# Runs in conanrun env (PATH includes installed bin/)
set -eu

echo "[test] aris --version"
out="$(aris --version)" && echo "$out" || {
    echo "❌ aris --version failed"
    exit 1
}
# Behavioral assertion: the tool must identify its own version.
case "$out" in
    *2.2*)
        echo "✅ aris --version reports 2.2"
        ;;
    *)
        echo "❌ aris --version output does not mention 2.2: $out"
        exit 1
        ;;
esac
