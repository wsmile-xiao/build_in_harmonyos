# libntru / libntru 0.5.0 前置适配笔记

## 边界

- 本任务只处理 `libntru/0.5.0`。
- 文件落点：`archives/l/libntru/0.5.0/`。
- Conan 包名：`libntru`，版本 `0.5.0`。
- 未修改任何其他库目录或基础设施目录。
- issue 未在任务正文中给出编号，暂记为 `TBD`。

## 版本与源码

- 上游：https://github.com/tbuktu/libntru ，C 实现的 NTRUEncrypt（IEEE P1363.1）。
- 官方 release：`libntru 0.5`（tag `0.5`，2016-05-14 发布，language=C）。
- 任务版本 `0.5.0` 即上游 tag `0.5` 的规范化写法（changelog 首行 `0.5 (5/14/2016)`，Makefile.linux `VERSION=0.5`）。
- 官方 tarball：https://codeload.github.com/tbuktu/libntru/tar.gz/refs/tags/0.5
  SHA-256 `e459c146cab5470e395f35377f14a39ccc5640d98d8a7ddd14bab41d5630d433`
- 纯 Makefile 构建（Makefile 按 uname 选择 Makefile.linux 等），无 configure。

## W0 依赖检查

已执行 `bash ci/scripts/preflight_check.sh libntru/0.5.0`：

- 结果：`[OK] 预检通过（无依赖需要检查）`。
- libntru 仅依赖系统库 `libm`（测试链接 `-lm`）；Makefile.linux 的 `LIBS+=-lrt`
  在 OHOS 上以 `LIBS=-lm` 覆盖（OHOS musl 已将 librt 并入 libc）。
- 无第三方 Conan 依赖，registry 解析为空集。

## 上游测试入口（双口径台账）

官方 tag 0.5 的 `tests/` 用户测试源中，测试框架
`print_result(name, valid)` 每次调用计为 1 个独立上游用户用例，共 **11** 个：

| 用例 | 文件 | 说明 |
|---|---|---|
| test_mult_int / test_mult_tern / test_mult_prod / test_inv / test_arr | tests/test_poly.c | 多项式运算；`test_mult_prod` 被上游显式 `#ifndef NTRU_AVOID_HAMMING_WT_PATENT` 门控 |
| test_keygen / test_encr_decr | tests/test_ntru.c | 密钥生成；encr_decr 内循环 ALL_PARAM_SETS（18 组参数）x (nondet+det) 子验证 |
| test_idxgen | tests/test_idxgen.c | 索引生成（6 组参数 x NUM_ITER） |
| test_bitstring | tests/test_bitstring.c | 聚合 test_append/test_trailing/test_leading |
| test_key | tests/test_key.c | 聚合 test_export_import/test_params_from_key |
| test_hash | tests/test_hash.c | SHA-1/SHA-2 系列各 100 轮比对 |

- `source_declared_total = 11`；`configured_executable_total = 11`（testham 全功能构建）。
- testnoham 变体 = 10 用例（`test_mult_prod` 由上游专利宏门控，属显式上游排除条件）。
- test_util.c/.h 为框架辅助，`src/bench.c`/`src/hybrid.c` 为基准/示例程序，不计入。
- 实测：testham 11/11 通过、testnoham 10/10 通过（OHOS aarch64 本机运行）。

## OHOS 适配（补丁 0001）

- 根因：上游 `src/ntru_endian.h` 仅处理 `__APPLE__/__MINGW32__/__GLIBC__<2.9/__OS2__`，
  OHOS（musl：`__OHOS__`+`__linux__`，无 `__GLIBC__`）下 `htole32/htole64/htole16`
  未声明，共享库链接报 `undefined reference ... htole32`（ld.lld
  `--no-allow-shlib-undefined`）。
- 修复：增加 `#elif defined(__OHOS__) || defined(__linux__) || defined(__FreeBSD__)`
  分支 `#include <endian.h>`（musl 的 htole* 位于该头）。
- 验证：宏探测输出 `__OHOS_DEFINED + __LINUX`；小端平台 `htole32` 恒等
  （鸿蒙专项测试 test_ohos 的端序回归护栏断言通过）。

## 鸿蒙专项测试

新增 `tests/test_ohos.c`（测试源码在 worktree 临时验证，最终以 test_package 消费者
测试 + 断言数形式归档；上游测试以 conanfile build() 内 `make test` 集成）：

- 16 项断言：参数集 EES443EP1 可用性、确定性密钥生成、加密/解密往返、
  密钥导出/导入往返（导出字节流比对）、小端端序恒等。
- 实测 16/16 通过（OHOS aarch64 本机）。

## conan-verify 结果

- G0/G1/G2/G3/G4 与 L2/L4/L5 全部 PASS（详见 reports/conan-verify-report.md）。
- conan create 端到端通过：补丁应用、static-lib 构建、上游 `make test`
  （testham+testnoham）、test_package 消费者 smoke（`libntru api smoke ok`）。

## W3 本地 CI 基线隔离

- W3/JC5 首次失败命中其他库既有基线文件
  `archives/u/util-linux-login/2.42.2/.ci-trigger`（main 提交
  `761df452e5` 已存在，非本次任务引入；SHA-256 `e3b0c442...` 空文件）。
- 已按已知恢复规则 3 执行基线隔离复验：`git rm --cached` 临时从 index 隔离，
  复跑 W3 通过，随后恢复 `git add` 并核对恢复后 SHA-256 与隔离前一致。
- 该基线文件未修改、未提交、未写入知识库或 PR。
---

**编译结束**: 2026-09-07 23:44
**最终状态**: built
