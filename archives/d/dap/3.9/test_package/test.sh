#!/data/service/hnp/bin/bash
# test_package/test.sh — consumer smoke test for dap (statistics tool)
# Runs in conanrun env (PATH includes installed bin/)
set -eu

# Upstream quirk (documented in notes.md): dap's --version handler prints the
# banner "Dap 3.6" to STDERR and exits with code 1 — capture both streams and
# accept the upstream exit code while requiring the version banner.
out="$(dap --version 2>&1)" || true
echo "$out"

case "$out" in
    *"Dap 3"*)
        echo "✅ dap --version printed its version banner"
        ;;
    *)
        echo "❌ dap --version output has no version banner"
        exit 1
        ;;
esac
