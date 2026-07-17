#!/data/service/hnp/bin/bash
# defaultbrowser is macOS-only; on OpenHarmony the packaged command must fail clearly.
set -eu

output="$(defaultbrowser 2>&1 || true)"
echo "$output"
case "$output" in
  *macOS-only*|*not\ available\ on\ OpenHarmony*)
    echo "✅ macOS-only diagnostic OK"
    ;;
  *)
    echo "❌ missing macOS-only diagnostic"
    exit 1
    ;;
esac
