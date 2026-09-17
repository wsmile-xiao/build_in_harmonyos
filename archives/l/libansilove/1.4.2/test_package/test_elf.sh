#!/usr/bin/env bash
# libansilove 鸿蒙 PC ELF 专项检查（test_package/conanfile.py test() 调用）
# 用法: test_elf.sh <package_dir> <bindir>
# 断言: AArch64 ELF、SONAME、直接 NEEDED (png/libc)、.codesign 段、无 RPATH/RUNPATH
set -u
PKG="$1"
SO="$PKG/lib/libansilove.so"
fails=0

[ -f "$SO" ] || { echo "FAIL: $SO not found"; exit 1; }

RE="${READELF:-}"
if [ -z "$RE" ]; then
  for c in /data/service/hnp/bin/llvm-readelf /data/service/hnp/bin/readelf llvm-readelf readelf; do
    command -v "$c" >/dev/null 2>&1 && RE="$c" && break
  done
fi
[ -n "$RE" ] || { echo "FAIL: no readelf available"; exit 1; }

# 1) AArch64 ELF
if "$RE" -h "$SO" | grep -q "Machine:.*AArch64"; then
  echo "PASS: ELF Machine is AArch64"
else
  echo "FAIL: ELF Machine is not AArch64"; fails=$((fails+1))
fi

# 2) SONAME
if "$RE" -d "$SO" | grep -q "(SONAME).*libansilove\.so"; then
  echo "PASS: DT_SONAME = libansilove.so"
else
  echo "FAIL: DT_SONAME missing"; fails=$((fails+1))
fi

# 3) Direct NEEDED: libpng16 + libc.
# zlib may be retained transitively by libpng16 under --as-needed, so
# libansilove.so is not required to carry a direct DT_NEEDED entry for libz.
dyn=$("$RE" -d "$SO")
for lib in libpng16 libc; do
  if echo "$dyn" | grep -q "(NEEDED).*${lib}"; then
    echo "PASS: NEEDED ${lib}"
  else
    echo "FAIL: NEEDED ${lib} missing"; fails=$((fails+1))
  fi
done

# 4) 无 RPATH/RUNPATH（库不得携带构建机绝对路径）
if echo "$dyn" | grep -qE "(RPATH|RUNPATH)"; then
  echo "FAIL: RPATH/RUNPATH present"; fails=$((fails+1))
else
  echo "PASS: no RPATH/RUNPATH"
fi

# 5) .codesign 段（鸿蒙 .so 加载要求）
if "$RE" -S "$SO" | grep -q "\.codesign"; then
  echo "PASS: .codesign section present"
else
  echo "FAIL: .codesign section missing"; fails=$((fails+1))
fi

# 6) musl 判定: 依赖 libc.so（无 libc.so.6 / ld-linux）
if echo "$dyn" | grep -q "ld-linux"; then
  echo "FAIL: gnu ld-linux present (not musl)"; fails=$((fails+1))
else
  echo "PASS: musl-style libc.so (no ld-linux)"
fi

if [ "$fails" -gt 0 ]; then
  echo "$fails ELF CHECK(S) FAILED"
  exit 1
fi
echo "ALL ELF CHECKS PASSED"
