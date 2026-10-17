# lz4 1.10.0.3 上游测试报告

> 状态：**已执行**（2026-09-10 真机复跑关键目标 + 引用同源 1.10.0 全量报告）

## 本版真机复跑（2026-09-10）

环境：HarmonyOS PC aarch64（kernel 1.12.0），clang（usr/local/bin），
隔离 Conan 作业，`make -C tests <target> POSIX_ENV=Yes CC=clang`（CC 必须显式，
tests/Makefile 用裸 cc）：

| 测试目标 | 结果 | 说明 |
|---|---|---|
| test-lz4-basic | PASS | CLI 基础压缩/解压往返（含负向用例输出为预期行为） |
| test-frametest | PASS | 帧格式全量用例（含 wrong frameSize 等 Error correctly detected 负向用例） |
| test-fuzzer | PASS | `5122/5122 - all tests completed successfully`，ratio 53.771% / HC 50.615% / dict 33.815% |

## 与 1.10.0 共用的测试结论（同源全量，2026-08-31）

同一源码的上游测试已于 2026-08-31 在 HarmonyOS PC (aarch64) 真机全量执行，
详细报告见 `../../1.10.0/reports/upstream-test-report.md`。摘要：

- **25 PASS / 4 SKIP / 1 FAIL**
- SKIP：abiTests、versionsTest、mesonbuild、valgrind 系（环境缺 ldd / 32 位
  loader / meson / valgrind，平台限制）
- FAIL：test-install——缺 coreutils install(1)，配方 package() 已用 conan
  copy() 等价实现，非功能缺陷
- 关键环境要点：必须显式 `POSIX_ENV=Yes`（否则 make 隐式规则产生幻影通过）；
  执行前清理 `make usan` 残留的 UBSan 插桩 .o

## test_package 与 conan create（2026-09-10 真机）

| 项 | 结果 |
|---|---|
| conan create static + test_package | PASS（`LZ4 compress=52 decompress=50 round-trip OK`） |
| conan create shared（-o shared=True，本版修复点）+ test_package | PASS |
| CLI `lz4 --version` | `v1.10.0 64-bit multithread` 正常 |
