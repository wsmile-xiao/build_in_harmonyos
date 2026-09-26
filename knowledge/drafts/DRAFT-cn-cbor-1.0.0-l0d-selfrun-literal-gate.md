# DRAFT-cn-cbor-1.0.0-l0d-selfrun-literal-gate: 远端 CI L0d 门禁按 `self.run` 字面量静态判定 test_package 空壳 — `test()` 必须字面含 `self.run()` 并真实执行消费者二进制

> **Contributor**: pc1-49 | **Status**: Draft（pending editor review）| **Updated**: 2026-09-24
> **Source**: cn-cbor 1.0.0 远端 CI L0d 返工（build_in_harmonyos，archives/c/cn-cbor/1.0.0，PR #11930）
> **拟提升编号：由知识库主编确认** —— 本草稿为未提升草稿，尚未分配正式 E 编号

## 场景

Conan 配方的 `test_package/conanfile.py` 在本机 `conan-verify` / `finish` W3
全绿（本地 pre-commit hook 对 `cmake.test()`/subprocess 放行），但推送到远端
CI（buildbot conan-pr-check）后，`test()` 仅写 `cmake.test()`、无 `self.run`
字面量的配方被 L0d 门禁判为空壳并终止构建，其余步骤（worker-prep /
git-clone / checkout-pr / conan-setup）全部通过。

cn-cbor 1.0.0 实证：连续 3 次构建（#59866/#59959/#59973）稳定失败于同一门禁：

```text
[step] L0: Quality gate checks...
[fail] L0d: test() method has no self.run() call — likely a stub
L0_RESULT=fail: gate failed: stub_test_method
L1_RESULT=skip: blocked_by_L0
L2_RESULT=skip: blocked_by_L0
L4_RESULT=skip: blocked_by_L0
L5_RESULT=skip: blocked_by_L0
exit code 1
```

## 问题

可复用问题签名（日志症状）：

```text
L0_RESULT=fail: gate failed: stub_test_method
[fail] L0d: test() method has no self.run() call — likely a stub
blocked_by_L0
```

真实门禁逻辑（`ci/conan/build_and_test.sh` L0d，纯 shell 静态检查）：

```bash
# L0d: test_package/conanfile.py 必须有 test() 且有 self.run()
if [ -f "$TEST_PKG_DIR/conanfile.py" ]; then
    if ! grep -q "def test" "$TEST_PKG_DIR/conanfile.py" 2>/dev/null; then
        echo "[fail] L0d: test_package/conanfile.py has no test() method"
    elif ! grep -q "self\.run" "$TEST_PKG_DIR/conanfile.py" 2>/dev/null; then
        echo "[fail] L0d: test() method has no self.run() call — likely a stub"
    fi
fi
```

## 根因 (Root Cause)

1. 远端 L0d 门禁是**字面量静态检查**而非**行为检查**：`grep -q "self\.run"`
   只要求 `self.run` 字面量出现在文件里。即使 `test()` 通过
   `cmake.test()` 实际运行了构建出的测试程序（行为上是真实执行），只要文件里
   没有 `self.run` 字面量，就会被判 `stub_test_method`。
2. 本地 pre-commit hook 与远端 CI 门禁**口径不一致**：本地放行
   `cmake.test()` / subprocess 形态，远端要求 `self.run` 字面量 —— 导致
   本地全绿、远端稳定红。
3. 失败发生在 L0 门禁段（`conan create` 之前），因此 L1/L2/L4/L5 全部
   `blocked_by_L0`，CI 无法进入实际构建与测试。

## 方案 (Solution)

`test()` 必须**字面包含** `self.run()` 调用，且该调用**真实执行** `build()`
构建出的消费者测试程序（不得仅 echo/print/true 假运行——那是另一类空壳）。
OHOS 上 ELF 执行用 bash 包装 + `env="conanrun"` 加载被测包运行时环境；
R33 禁止在 `self.run()` 中裸用 `${CC}`/`${CXX}`/`${CFLAGS}`/`${LDFLAGS}`
等 shell 变量（release worker 上为空）：

```python
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CncborTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # OHOS: /system/bin/sh (mksh) 无法直接执行 ELF 二进制。
        # 用 bash 包装消费者测试程序执行，env="conanrun" 加载被测包运行时环境。
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_cn-cbor'", env="conanrun")
```

形态同已通过样例 `archives/z/zlib/1.3.1/test_package/conanfile.py`。
消费者测试源文件必须真实调用被测包公开 API（R34/L1e：test 实质依赖被测包），
cn-cbor 的 `test.c` 覆盖编码/解码往返 12 项 CHECK 断言。

## 验证 (Verification)

本机即 HarmonyOS aarch64（clang 15.0.4，CMake 4.1.2，Conan 2.29.1）：

- **复现**: 按远端 CI 同源逻辑对 r01 的 test_package/conanfile.py 执行
  `grep -q "def test"`（PASS）后 `grep -q "self\.run"`（FAIL）→
  `L0_RESULT=fail: gate failed: stub_test_method`（复现 log SHA-256
  `75f9b4f21b5644af4b7d145c56c89f36a098bae5117a0ae2bc5083d2aefbdb58`）
- **修复后**: `grep -q "self\.run"` PASS，L0d 转绿；CI 同源脚本单包复验
  `L0_RESULT=pass: all checks passed` / `L1_RESULT=pass: upstream tests +
  test_package executed`（log SHA-256 `b6e2593de01615c0f31fef2b40a6f25e3599e
  3292f60ba9eeceb621104d0c547`）
- **消费者实跑**: `conan create` 中 `RUN: /data/service/hnp/bin/bash -c
  './test_cn-cbor'` → `ok:`×12 + `PASS: cn-cbor round-trip (encode/decode) OK`
  （exit 0）
- **上游测试**: `./cbor_test` → `RESULTS: 11 tests (11 ok, 0 failed,
  0 skipped)`（exit 0）

## 适用边界 (Boundary)

- 适用：所有 `test_package test()` 仅用 `cmake.test()` / 无 `self.run` 字面量
  的 Conan 配方，在含 L0d grep 门禁的远端 CI（conan-pr-check）下；
  cross-library 可复用（zlib/1.3.1 已是同形态正例）
- 不适用：纯资源/数据型配方（→ E255，L0 门禁整体不适用，走 resource-data 模式）；
  门禁正则把依赖访问 API 误判为命令调用（→ DRAFT-6052-libnxml，不同根因）
- 反例边界：若配方确无真实消费者测试（纯空壳），`self.run("true")` 假运行仍
  属欺骗（PF3/L1d 会再拦），必须在 `build()` 真实构建并在 `test()` 真实执行
  测试程序

## 查重差异 (vs Existing)

| 条目 | 覆盖 | 差异 |
|------|------|------|
| E255（L0 门禁症状清单，resource-data-package） | L0 门禁对资源包不适用 | 本候选=普通编译库 test() 缺 self.run 字面量被拦，根因是门禁口径差异非资源包 |
| E239（self.run 多用例聚合诊断） | test() 内多个 self.run 的异常聚合写法 | 本候选=是否字面包含 self.run 的门禁判定，不涉及多用例诊断 |
| E241（test_package JSON 摘要形态） | 独立 .py 脚本 + self.run + JSON 摘要比对 | 本候选=最简 bash 包装形态，无 JSON 摘要要求 |
| E301（cmake.ctest vs cmake.test） | 构建期 ctest 参数传递的 API 选择 | 本候选=test() 门禁字面量要求，与构建期 ctest 无关 |
| DRAFT-6052-libnxml（L0o 裸依赖名误报） | CI 门禁把 API 访问当命令调用 | 本候选=L0d 门禁把无 self.run 字面量判空壳；同为 CI 门禁正则类，但门禁与根因不同 |

**查重结论**: combination_novelty=true、boundary_novelty=true（远端 L0d grep
字面量门禁 × 本地 pre-commit 放行口径差异 × bash 包装 + conanrun 的修复形态，
既有条目未覆盖）；causal/trigger/solution 三轴部分重叠。本候选为新增差异且已
由 cn-cbor 1.0.0 真实日志双向验证（复现/修复/CI 同源复验/消费者实跑），可跨库
复用 → 建议提升为正式 E 条目（主编审核）。
