#!/bin/sh
# Consumer verification for u-config 0.34.0, exercised as a build system
# would: PKG_CONFIG_PATH discovery, .pc parsing, variable expansion,
# --newlines output, search-path override, and the exit-code contract.
# 10 assertions; every PASS line is a real behavior check on the
# installed pkg-config binary.
set -eu

command -v pkg-config >/dev/null 2>&1 || { echo "FAIL: pkg-config not on PATH"; exit 1; }

work=$(pwd)/testwork
rm -rf "$work"
mkdir -p "$work/lib" "$work/include"

cat > "$work/lib/foo.pc" <<EOF
prefix=$work
libdir=\${prefix}/lib
includedir=\${prefix}/include

Name: foo
Description: sample consumer package
Version: 1.2.3
Libs: -L\${libdir} -lfoo
Cflags: -I\${includedir}
EOF

# missing Version: must not validate
cat > "$work/lib/broken.pc" <<'EOF'
Name: broken
Description: no Version field
EOF

export PKG_CONFIG_PATH="$work/lib"
pass=0

# 1. version
out=$(pkg-config --version)
[ "$out" = "0.34.0" ] || { echo "FAIL 1: --version [$out]"; exit 1; }
pass=$((pass+1)); echo "PASS 1: --version -> $out"

# 2. compiled-in default search path
out=$(pkg-config --variable pc_path pkg-config)
case "$out" in */usr/lib/pkgconfig*) ;; *) echo "FAIL 2: pc_path [$out]"; exit 1;; esac
pass=$((pass+1)); echo "PASS 2: pc_path -> $out"

# 3. modversion from the sample .pc
out=$(pkg-config --modversion foo)
[ "$out" = "1.2.3" ] || { echo "FAIL 3: --modversion [$out]"; exit 1; }
pass=$((pass+1)); echo "PASS 3: --modversion -> $out"

# 4. cflags+libs token order and expansion
out=$(pkg-config --cflags --libs foo)
[ "$out" = "-I$work/include -L$work/lib -lfoo" ] || { echo "FAIL 4: [$out]"; exit 1; }
pass=$((pass+1)); echo "PASS 4: --cflags --libs -> $out"

# 5. valid .pc passes --validate
pkg-config --validate foo || { echo "FAIL 5: --validate foo rc!=0"; exit 1; }
pass=$((pass+1)); echo "PASS 5: --validate foo rc=0"

# 6. .pc missing Version fails --validate
if pkg-config --validate broken 2>/dev/null; then
  echo "FAIL 6: --validate broken rc=0"; exit 1
fi
pass=$((pass+1)); echo "PASS 6: --validate broken rc!=0"

# 7. missing package fails --exists
if pkg-config --exists definitely-not-here 2>/dev/null; then
  echo "FAIL 7: --exists missing package rc=0"; exit 1
fi
pass=$((pass+1)); echo "PASS 7: --exists missing rc!=0"

# 8. --newlines separates arguments by line feeds
out=$(pkg-config --newlines --cflags --libs foo)
n=$(printf '%s\n' "$out" | grep -c . || true)
[ "$n" = "3" ] || { echo "FAIL 8: --newlines produced $n lines [$out]"; exit 1; }
pass=$((pass+1)); echo "PASS 8: --newlines -> 3 lines"

# 9. PKG_CONFIG_LIBDIR replaces the default search path
if PKG_CONFIG_LIBDIR="$work/lib" pkg-config --exists foo; then
  pass=$((pass+1)); echo "PASS 9: PKG_CONFIG_LIBDIR override rc=0"
else
  echo "FAIL 9: PKG_CONFIG_LIBDIR override rc!=0"; exit 1
fi

# 10. single variable expansion
out=$(pkg-config --variable libdir foo)
[ "$out" = "$work/lib" ] || { echo "FAIL 10: --variable libdir [$out]"; exit 1; }
pass=$((pass+1)); echo "PASS 10: --variable libdir -> $out"

echo "test u-config 0.34.0: $pass/10 checks PASS"
exit 0
