# libpopcnt 2.0 — Test Report

- task_id: libpopcnt-2.0-r07-recoverable-shared-finish-repair-and-local-delivery-preview-pc1-22-20260901T040537Z
- executor: pc1-22
- worktree: /storage/Users/currentUser/runnerljs002/build_in_harmonyos-libpopcnt-2.0
- branch: feat/libpopcnt-2.0 / HEAD: 369a6e53d39022be53f2e93a0a05fd5ca03d3c1b
- 官方源: https://github.com/kimwalisch/libpopcnt/archive/refs/tags/v2.0.tar.gz
- SHA-256: 510f7a3d12b3a7245507ba8c348b69f3c8b4a15a303b129dc402b0cc8e996ff4
- 库类型: header-only（单文件 `libpopcnt.h`，无二进制产物、无 bin/、无需 packaging/ 与 .staging-verified）

## 1. 上游测试（host 真实运行）

上游 `test/CMakeLists.txt` 以 `file(GLOB "*.cpp" "*.c")` 发现 2 个独立测试源，注册 2 个 CTest：
`test1`（C++）与 `test2`（C）。

| 入口 | 命令 | 工作目录 | 退出码 | 输出摘要 |
|------|------|----------|--------|----------|
| test/test1.cpp | `./test/test1` | `/storage/Users/currentUser/tmp/libpopcnt-2.0-check/libpopcnt-src/build-host` | 0 | `Status: 100% / libpopcnt tested successfully!` |
| test/test2.c | `./test/test2` | 同上 | 0 | `Status: 100% / libpopcnt tested successfully!` |

两者均 runnable-and-run（exit 0），未跳过、未将不可用条目计为通过。

## 2. Conan test_package（OHOS aarch64 profile，真实执行）

`conan create` 的 test() 阶段实际构建并运行 2 个消费者测试。日志：`archives/l/libpopcnt/2.0/reports/conan-create.log`
（SHA-256 `c5c20e1c90a0dc5bf9d6c066c03983072f65f79d2198e78bbca836c33b40a197`）。

| 入口 | 命令 | 退出码 | 输出摘要 |
|------|------|--------|----------|
| test_package/test.c | `./test_libpopcnt` | 0 | `Status: 100% / libpopcnt test_package consumer PASSED` |
| test_package/test_hmos.c | `./test_libpopcnt_hmos` | 0 | `[hmos] libpopcnt real popcnt API checks PASSED (crafted + large-array) / ALL HARMONYOS-SPECIFIC TESTS PASSED` |

- 构建命令（conan create 日志）：`cmake --build <test_package>/build/clang-15-armv8-17-release -- -j20` → `test_libpopcnt` + `test_libpopcnt_hmos` 均 100% 构建。
- OHOS 覆盖：`test_hmos.c` 真实调用 `popcnt`/`popcnt64`，含 crafted 字节模式（0x0f/0xff/0x1d）与 4096 字节大数组向量路径；断言精确置位计数。
- host 复核：`$HOME/tmp/libpopcnt-tp/` 下 `./test_libpopcnt` exit 0、`./test_libpopcnt_hmos` exit 0（R02 已实测）。

## 3. W3 本地 CI 门禁（双非变更控制）

`run_local_ci('libpopcnt','2.0')`（`OHC_PREDL_NONMUTATING=1` + `OHC_CONAN_NONMUTATING=1` + libpopcnt-only PR-diff 作用域），
退出码 0。日志：`archives/l/libpopcnt/2.0/reports/w3-local-ci.log`
（SHA-256 `96e8630ae675cff94e9845ea0bba2ed6da55d33571990142aa05905e408b02a0`）。

| 门禁 | 结果 |
|------|------|
| JC junk check | pass |
| L0 结构 | pass (all checks passed) |
| L1 test_package 执行 | pass (test_package executed) |
| L2 | skip: no bin/ 目录（header-only，产物无可执行二进制） |
| L4 安全扫描 | pass (patches clean) |
| L5 产物基线 | warn: no artifacts found（header-only，无 .so/.a 产物，属预期） |

## 4. 统计汇总

- 上游独立测试：2/2（test1、test2），均 exit 0。
- test_package 消费者 + OHOS 特定：2/2（test_libpopcnt、test_libpopcnt_hmos），均 exit 0。
- 真实测试入口数：4（上游 2 + 消费者 2）；重复模式（shared/static、W3 重跑）不计重复。

## 5. header-only 适用性证明（packaging/ 与 .staging-verified）

- libpopcnt 为 header-only：`CMakeLists.txt` 仅 `install(FILES libpopcnt.h DESTINATION include)`，无库/二进制产物。
- 因此 `packaging/`（预编译 tarball）与 `.staging-verified`（staging 隔离验证标记）对 header-only 库不适用，
  不应作为 submit 就绪阻塞项；`.build-closed` 与本文档（真实 test-report）为必需。

## 6. 测试证据日志清单

| 文件 | SHA-256 |
|------|---------|
| reports/conan-create.log | c5c20e1c90a0dc5bf9d6c066c03983072f65f79d2198e78bbca836c33b40a197 |
| reports/conan-verify-report.md | fc8665365144df776bd3dc553f484ec09389eceb94bb2e2d2889eead74d217b4 |
| reports/w3-local-ci.log | 96e8630ae675cff94e9845ea0bba2ed6da55d33571990142aa05905e408b02a0 |
| reports/r03-baseline-noise-exemption.md | 7be9e21bc4bfaa22c3b82f9fa82a958119afbf35e76117e82ec70cd0f38d095f |
