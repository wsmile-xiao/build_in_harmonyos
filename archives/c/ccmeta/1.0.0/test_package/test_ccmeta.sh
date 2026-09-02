#!/bin/sh
set -eu
PKG="$1"
echo "[ccmeta test] package: $PKG"
# 1. core script exists and syntax ok
if [ ! -f "$PKG/share/ccmeta/shared/ccmeta-core.sh" ]; then
  echo "missing shared/ccmeta-core.sh"
  exit 1
fi
sh -n "$PKG/share/ccmeta/shared/ccmeta-core.sh"
echo "core sh -n: OK"

# 2. skills exist
for d in "skills/ccmeta" "skills/ccmeta-dangerous"; do
  if [ ! -d "$PKG/share/ccmeta/$d" ]; then
    echo "missing $d"
    exit 1
  fi
  echo "$d: OK"
done

# 3. README installed
if [ ! -f "$PKG/share/ccmeta/README.md" ]; then
  echo "missing README.md"
  exit 1
fi
echo "README: OK"

# 4. wrapper binary
if [ ! -x "$PKG/bin/ccmeta" ]; then
  echo "missing bin/ccmeta"
  exit 1
fi
"$PKG/bin/ccmeta" | grep -q "ccmeta 1.0.0"
echo "wrapper: OK"

echo "ccmeta test_package: PASS"
