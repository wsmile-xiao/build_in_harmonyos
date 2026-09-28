# DRAFT: 上游测试数据缺失导致 gtest 二进制中途 SIGTRAP，通过率被严重低估

> Status: **Draft**（待审核 promote）| severity: `2` | category: `testing|upstream-tests|testdata|pass-rate` | Updated: 2026-09-25
> 对应: `knowledge/drafts/DRAFT-libjxl-tools-0.11.2-upstream-testdata-compile-time-path.kv`

---

**匹配关键词**：TEST_DATA_PATH, JPEGXL_TEST_DATA_PATH, testdata, git-lfs, SIGTRAP, ReadTestData, gtest, pass-rate, gh-proxy

## 错误签名（error_signature）

```text
Signal 5 \(core dumped\)|ReadTestData .*testdata/|SIGTRAP.*_test|error running test executable
```

## 错误摘录（error_excerpt）

```text
[ RUN      ] SplinesTest.Drawing
ReadTestData /storage/.../libjxd0323df58ee96/s/testdata/jxl/splines.pfm
Signal 5 (core dumped)            # JXL_CRASH() → 整个测试二进制中止

# compile_commands.json 中的编译期宏（运行时 env 无效）
-DTEST_DATA_PATH=\"/storage/Users/currentUser/.conan2/p/libjxd0323df58ee96/s/testdata\"
```

## 根因（root_cause）

上游 libjxl 的测试数据位于**独立仓库** `libjxl/testdata`，发布 tarball
（`archive/refs/tags/vX.Y.Z.tar.gz`）**不含该 git 子模块**。`lib/jxl/test_utils.cc` 的
`GetTestDataPath()` 在**编译期**由宏 `-DTEST_DATA_PATH`（CMake 变量 `JPEGXL_TEST_DATA_PATH`，
默认 `<conan source folder>/testdata`）固化，因此运行时设置 `TEST_DATA_PATH` 环境变量**完全无效**。
数据缺失时 `ReadTestData()` 触发 `JXL_CRASH()` → `SIGTRAP`，整个二进制中止、后续用例不再执行。

**影响**：libjxl-tools/0.11.2 实测 —— 未补数据 `409/4778 = 8.6%`（假象），补齐后
`4778/4782 = 99.92%`，断言失败 0。若只看 8.6% 会误判适配失败。

## 推荐方案（rec_approach: `fetch-testdata-to-compile-time-path`）

1. 先确认编译期期望路径：`grep -o 'DTEST_DATA_PATH=[^ ]*' <build>/compile_commands.json`。
2. 取回上游 testdata 到该路径。`libjxl/testdata` **未使用 git-lfs**（`.gitattributes` 仅 `binary`
   属性），raw 内容可直接下载；本机 `git-lfs` 为失效软链、`raw.githubusercontent.com` 直连超时，
   改用本仓库 CI 既有代理镜像 `gh-proxy.com`（284 文件 / 约 112 MiB，实测全部成功）。
3. 逐个运行测试二进制统计；通过率须分开报告「定义用例 / 已执行 / 通过 / 断言失败」四项。
4. 若确实无法取回数据，**如实**给出通过率口径与受阻原因（禁止把崩溃计为通过/跳过）。

**替代方案**：重配测试构建时显式 `-DJPEGXL_TEST_DATA_PATH=<dir>`（需重跑全部测试构建）。

---

*本文件由同名 `.kv` 字段派生生成（kv↔md 配套）；内容与 kv 一致，待主编审核 promote 后转入 `knowledge/doc/`。*
