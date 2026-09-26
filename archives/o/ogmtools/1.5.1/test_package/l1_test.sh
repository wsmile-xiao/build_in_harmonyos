#!/bin/sh
# ogmtools 1.5.1 L1 test (upstream 1.5; R34 实质依赖被测包：实际执行被测二进制)
# 占位符 @BINDIR@ / @WORKDIR@ 由 test_package/conanfile.py test() 运行时替换。
# 1. 6 个工具 --version 输出 1.5（构建产物可执行 + Conan 依赖链解析）
# 2. 最小 OGG 容器 → ogminfo/ogmsplit 数据处理路径（非空壳）
set -e
B="@BINDIR@"
W="@WORKDIR@"
for t in ogmmerge ogmdemux ogminfo ogmsplit ogmcat dvdxchap; do
  out="$("$B/$t" --version 2>&1)" || { echo "FAIL: $t --version rc=$?"; exit 1; }
  case "$out" in *1.5*) ;; *) echo "FAIL: $t version missing 1.5: $out"; exit 1;; esac
  echo "OK: $t --version -> 1.5"
done
# 最小 OGG 页（0 packet 空容器）：ogm 工具走完整 ELF 加载 + 依赖解析 + 文件读取路径
printf 'OggS\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' > "$W/test.ogm"
rm -rf "$W/split-out" && mkdir -p "$W/split-out"
# ogminfo：最小空容器允许正常退出码 0/1，禁止崩溃（139=segfault）
rc=0; "$B/ogminfo" "$W/test.ogm" > "$W/ogminfo.out" 2>&1 || rc=$?
case "$rc" in 0|1) ;; *) echo "FAIL: ogminfo rc=$rc: $(cat "$W/ogminfo.out")"; exit 1;; esac
echo "OK: ogminfo rc=$rc"
# ogmsplit：数据流处理路径
rc=0; "$B/ogmsplit" "$W/test.ogm" "$W/split-out/" > "$W/ogmsplit.out" 2>&1 || rc=$?
case "$rc" in 0|1) ;; *) echo "FAIL: ogmsplit rc=$rc: $(cat "$W/ogmsplit.out")"; exit 1;; esac
echo "OK: ogmsplit rc=$rc"
echo ALL_PASS
