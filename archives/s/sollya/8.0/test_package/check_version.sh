#!/bin/sh
# test_package/check_version.sh —— sollya 8.0 消费者级测试源
#
# 为什么需要本文件（CI L0c 门禁，build_and_test.sh:344-358）：
#   for ext in c cpp cc cxx sh py; find test_package -name "*.$ext"
#     -not -name conanfile.py … → 若为空即
#   [fail] L0c: No test source files in test_package/  ⇒ no_test_sources
# 第一版把 4 条断言全写在 conanfile.py 里，导致 test_package/ 下没有任何
# 独立测试源文件而被 L0 拦下（finish Step5 W3 本地 CI 模拟失败）。
# 本脚本是**真被调用**的（conanfile.py::test() → self.run("sh …")），
# 不是为过门禁而放的死文件。
#
# 鸿蒙特有测试（rule12，≥1）：本脚本在 **OHOS/aarch64/musl** 目标平台直跑
# 已安装的 `bin/sollya --version`，断言 4 重「产物自报指纹」——上游与 x86 CI
# 均不产生此运行时证据。
#
# 判定口径：4 条指纹逐条 grep，任一缺失即非 0 退出（= conan test 失败）。
# 原始输出另存 sollya-version.txt 供 W4/审方复核（与轮 B 实读 3085 字符对齐）。

set -u
OUT="${1:-sollya-version.txt}"

echo "== sollya --version（OHOS/aarch64/musl 目标平台直跑）=="
sollya --version > "$OUT" 2>&1
rc=$?
if [ "$rc" -ne 0 ]; then
    echo "FAIL: sollya --version exited rc=$rc（loader 或运行期共享库问题）"
    cat "$OUT"
    exit 1
fi
echo "captured $(wc -c < "$OUT") bytes -> $OUT"

fail=0

check() {
    # $1 = 必须出现的指纹子串, $2 = 断言说明
    if grep -qF -- "$1" "$OUT"; then
        echo "PASS: $2"
    else
        echo "FAIL: $2  (missing: $1)"
        fail=1
    fi
}

# 4 重产物自报指纹（与 test_package/MANIFEST.yml 的 assertion_count: 4 对齐）
check "This is sollya 8.0" \
      "① PACKAGE_STRING 版本自报 = sollya 8.0"
check "based on GMP 6.3.0, MPFR 4.2.2 and MPFI 1.5.4." \
      "② 三个实链依赖库版本自报（gmp/mpfr/mpfi 真链非空壳）"
check "It uses FPLLL as:" \
      "③ --with-fplll 注入生效自证（fplll.h 直接命中/lfplll 兼容/std=c++11/standard API）"
check "CeCILL-C" \
      "④ license 自报 CeCILL-C，与配方 license 字段互证"

if [ "$fail" -ne 0 ]; then
    echo "== 失败时打印全文（便于定位） =="
    cat "$OUT"
    exit 1
fi
echo "check_version.sh: all 4 fingerprint assertions passed"
exit 0
