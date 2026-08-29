# DRAFT-zstd-upstream-test-evidence-boundary — zstd 上游测试证据边界（OHOS）

> **Contributor**: pc3-23 | **Status**: DRAFT | **Updated**: 2026-08-28
> **Severity**: medium | **Category**: ohos / testing / cmake / evidence-boundary
> **Audience**: zstd/libzstd 系列版本，以及所有在 OHOS 上用 CMake BUILD_TESTS=OFF 且依赖 shell 脚本 / 录制数据 / OSS-Fuzz 的库

## Scope
在 OHOS 平台上用 CMake 构建 zstd（或任何用 `BUILD_TESTS=OFF` 跳过上游测试的库）时，
如何正确记录上游测试证据，避免把"未运行"写成"通过"或泛化为"质量豁免"。

## 背景
- zstd 1.5.7 上游测试套件共 222 个文件，入口由 CMake 的 `ZSTD_BUILD_TESTS` 开关控制。
- OHOS 环境限制：无 `/bin/sh`（Toybox）、无 OSS-Fuzz 运行时、部分录制数据为 x86/glibc 环境生成。
- 若 `ZSTD_BUILD_TESTS=OFF` 就停止证据收集，后续报告可能把"未运行"写成"通过"（0/0 假象）。
- 正确做法：**逐组检查**测试入口的前置条件，区分三类状态：
  - **可运行但未运行**（runable but not run）：有前置条件但未满足，不运行
  - **不可运行**（genuinely not runnable）：前置条件在 OHOS 上不存在
  - **已运行**（actually run）：实际执行并得到 exit code

## 逐组测试证据（以 zstd 1.5.7 为例）

| 测试组 | 文件数 | 状态 | 不可运行原因 |
|--------|--------|------|------------|
| tests/ 根目录（playTests.sh + fuzzer + zstreamtest + 6 .py） | 32 | not_run | playTests.sh 依赖 /bin/sh；fuzzer.c 需 OSS-Fuzz；zstreamtest 长时间模糊 >
| tests/cli-tests/（12 子目录，45 个 .sh 脚本） | 102 | not_run | CLI 端到端测试，run.py 驱动 45 个 .sh，依赖 /bin/sh + GNU diff/sed/grep |
| tests/fuzz/（26 个 .c fuzz harness + 5 .h） | 37 | not_run | OSS-Fuzz 专用，需 libFuzzer/AFL 运行时，OHOS clang 15 不支持 `-fsanitize=fuzzer` |
| golden-compression / golden-decompression / golden-errors / golden-dictionaries | 4 dirs | not_run | 黄金样本为 x86/glibc 录制，需 zstreamtest 消费；zstreamtest 未构建 |
| tests/regression/（5 .c + 5 .h + CSV） | 14 | not_run | 依赖 playTests.sh 入口，OHOS 无 /bin/sh |
| tests/gzip/（20 个 .sh 互操作测试） | 23 | not_run | gzip 兼容性脚本，依赖 /bin/sh 与系统 gzip 二进制，两者均无 |

## 已运行测试
| 测试 | 文件 | 命令 | 结果 | 断言 |
|------|------|------|------|------|
| test_package 鸿蒙特有测试 | `test_package/test.c` | `./test_probe` | PASS — `zstd: version=10507, dlopen libzstd.so ok` | 2（ZSTD_versionNumber 返回值 + ZSTD_compress 符号存在） |

## 正确处理方式
1. **conanfile.py 中设 ZSTD_BUILD_TESTS=OFF**：允许（构建开关），但必须同时记录证据。
2. **test_package/MANIFEST.yml 记录**：`upstream_test_in_build: false` + `upstream_tests` 逐组列表 + `test_package_tests` 已运行测试。
3. **test_package 必须包含实质 API 调用**（R34）：dlopen + dlsym 真实库符号（如 `ZSTD_versionNumber`、`ZSTD_compress`）。
4. **报告口径**：已运行 → 按 exit code 报告；未运行 → 报告 `not_run` + 不可运行证据；禁止写 0/0 通过率。

## 验证
- `grep ZSTD_BUILD_TESTS archives/l/libzstd/1.5.7/conanfile.py` → 确认开关值。
- `grep -c "not_run" archives/l/libzstd/1.5.7/test_package/MANIFEST.yml` → 6 组（222 个文件）。
- `grep -c "test_package_tests" archives/l/libzstd/1.5.7/test_package/MANIFEST.yml` → 1 组（test_probe，2 断言）。

## 平台边界
- OHOS 无 `/bin/sh`（Toybox 不支持 bash 语法）→ shell 脚本不可运行。
- OHOS 无 OSS-Fuzz 运行时 → fuzz harness 不可运行。
- 黄金数据为 x86/glibc 录制 → 不能直接用于 OHOS arm64 验证。
- 这些是**平台限制**，不是"质量豁免"——必须如实记录，不能泛化为"质量不可考察"。

## 不能宣称的结论
- ❌ "222 个上游测试全部通过"（实际未运行）。
- ❌ "0/0 (100%) 通过率"（0/0 表示无测试可评估，不是通过率）。
- ❌ "OHOS 与 zstd 不兼容"（平台限制不等于兼容性问题，只是某些测试入口不可用）。
- ❌ "质量豁免"（平台限制只说明本环境不可运行，不说明质量不可考察）。

## 与既有条目的关系
- 类似：E228（OHOS /bin/sh 缺失对 make check 的影响，Libtool 场景）、E294（shared 包与静态-only 上游测试的关系）、E270（FFTW 测试运行时问题）
- 本条目聚焦于 `BUILD_TESTS=OFF` 开关下的证据**报告规范**，不是具体测试运行技术

## Source
- Package: `archives/l/libzstd/1.5.7`（r02 adapt 报告）
- 证据文件：`test_package/MANIFEST.yml`、`conanfile.py`（ZSTD_BUILD_TESTS=OFF）
- 证据命令：`conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing`（rc=0）
- 鸿蒙测试：`test_package/test.c`，dlopen + dlsym ZSTD_versionNumber（version=10507），PASS