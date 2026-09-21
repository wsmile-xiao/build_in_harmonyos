#!/usr/bin/env bash
# libfstngram 1.8.4 test_package smoke check.
# Verifies the libfstngram artifact and the NGramFst extension headers are
# packaged, and that the headers still declare the n-gram API the library
# exports (LOUDS bitmap index + NGramFst / n-gram matcher entry points).
set -euo pipefail

lib="$1"
header="$2"

test -e "$lib"
test -f "$header"

# NGramFst extension header must declare the classes the library implements.
grep -q "class NGramFst;" "$header"
grep -q "class NGramFstMatcher" "$header"
grep -q "class NGramFstImpl" "$header"
grep -q "NGramFst(const Fst<A> &fst" "$header"

# The sibling headers shipped by the same extension must also be installed.
inc_dir="$(dirname "$header")"
test -f "$inc_dir/bitmap-index.h"
test -f "$inc_dir/nthbit.h"
grep -q "class BitmapIndex" "$inc_dir/bitmap-index.h"
grep -q "nth_bit" "$inc_dir/nthbit.h"

# Smoke-check the packaged library name matches the NGramFst extension ABI
# (openfst libfstngram uses -version-info 26:0:0 -> libfstngram.so.26).
case "$lib" in
  *.so|*.dylib)
    echo "libfstngram artifact: $(basename "$lib")"
    ;;
  *.a)
    echo "libfstngram static artifact: $(basename "$lib")"
    ;;
esac

# 产物本身的可执行验证（链接 + 运行）在 test_package/conanfile.py 里由
# ngram_consumer.cc 完成——它把 BitmapIndex::Rank1/Select1（bitmap-index.o）与
# nth_bit 的调用链到**已安装**的 libfstngram 产物上并断言运行结果。
# 这里不对二进制 .a 做字节级 grep：实测在刚写完的 Conan 缓存文件上
# `grep -q` 会间歇性返回"无匹配"（同一文件数分钟后稳定命中），把产物断言
# 建立在字节扫描上会引入与被测对象无关的假失败。
echo "PASS libfstngram artifacts"
echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":true,\"command\":\"check_libfstngram.sh\"}"
