# sexpp 0.8.7 适配笔记（2026-09-19）

## 任务信息
- 平台任务号 10516（待领取 → 已认领），分支 `feat/sexpp-0.8.7`
- 上游 https://github.com/rnpgp/sexpp tag `v0.8.7`
  tarball https://codeload.github.com/rnpgp/sexpp/tar.gz/refs/tags/v0.8.7
  sha256=d877a2a39f38d3e0d84f74cb5e4bb3c180b8ee68086ccc43117e09364d66ba2b
- 依赖：运行期 0 个；`gtest/1.17.0` 仅作 `test_requires`（跑上游单元测试用，不进消费方闭包）

## 适配决策
1. **取源码走 codeload 官方端点**：真机直连 `github.com` 常超时，codeload 稳定；
   codeload URL 末段没有 `.tar.gz`，`get()` 必须显式传 `filename="sexpp-0.8.7.tar.gz"`，
   否则被当成 zip 报 `BadZipFile`。不使用任何第三方加速镜像（PF7）。
2. **上游测试真的跑起来**：上游 `WITH_SEXP_TESTS=ON` 时用 CMake `FetchContent` 从
   `github.com/google/googletest.git` 拉 googletest，真机不可达。改为
   `DOWNLOAD_GTEST=OFF` + `find_package(GTest REQUIRED)`，googletest 由制品仓的
   `gtest/1.17.0` 提供（`test_requires`，abseil/20260526 同款写法），并在
   `generate()` 里把 `GTest_DIR` 指向 conan 包内的 `lib/cmake/GTest`。
3. **CaptureStdout 的临时目录只看 `TMPDIR`**：上游 2 个 warning 用例用
   `testing::internal::CaptureStdout()/CaptureStderr()`，其 scratch 目录在制品仓的
   gtest 包里被改成 `getenv("TMPDIR") ?: "/data/local/tmp/"`
   （`archives/g/gtest/1.17.0/patches/0001-tmpdir-ohos-sandbox.patch` 替换了
   googletest `gtest-port.cc` `#else` 分支的硬编码 `"/tmp/"`）。OHOS 上 `/tmp`
   （erofs ro）与 `/data/local/tmp` 都不可写，所以在 `build()` 里用 `Environment()`
   只导出 `TMPDIR` 到 build 目录下的可写子目录，再执行 `cmake.test()`，
   68 个上游用例全部真跑，不靠过滤跳过。**实测 `TMP`/`TEMP`/`TEST_TMPDIR` 均无效**
   （环境矩阵见「真机实测」），与 `DRAFT-sexpp-0.9.1-gtest-captured-stream-tmp-hardcode`
   「不读任何环境变量」的差异根因是它链接未打补丁的系统 googletest 1.14，
   详见 `knowledge/drafts/DRAFT-sexpp-0.8.7-gtest-capture-stdout-tmpdir-only.md`。
4. **产物形态**：库 `libsexpp.a`/`libsexpp.so`（上游 `OUTPUT_NAME sexpp`）+
   上游 CLI `bin/sexpp`（软件级 `commands.json` 已在 0.9.1 建立，本版补记 0.8.7）。
5. **cmake 版本**：上游 `cmake_minimum_required(VERSION 3.14)`，真机 CMake 4.4.3
   可接受，无需 `CMAKE_POLICY_VERSION_MINIMUM`。

## 上游测试账本（四维）
- **N_static = 68**：`tests/src/*.cpp` 中 `TEST`/`TEST_F` 宏总数（取数命令：
  `grep -rhE '^TEST(_F|_P)?[[:space:]]*\(' tests/src/*.cpp | wc -l`）
  - baseline-tests.cpp 3 / exception-tests.cpp 22 / primitives-tests.cpp 26 /
    g10-compat-tests.cpp 1 / g23-compat-tests.cpp 9 / g23-exception-tests.cpp 7 /
    compare-files.cpp 0（仅提供 `compare_binary_files` 辅助，无 TEST 宏）
- **N_ran**：见下「真机实测」
- **N_pass**：见下「真机实测」
- 上游 0.8.7 的 `add_executable(sexpp-tests ...)` 已包含全部 7 个测试源文件，
  **无需** 0.9.1 那条「补 traits-tests.cpp」的补丁（该文件 0.8.7 尚不存在）。

## 真机实测

命令（清缓存后重跑，源码由 `source()` 重新从 codeload 下载）：

```sh
conan remove "sexpp*" -c
conan create archives/s/sexpp/0.8.7 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
```

| 项 | 实测结果 |
|---|---|
| `conan create` 退出码 | `CREATE_RC=0` |
| 上游 ctest（在 `build()` 内执行） | `100% tests passed out of 68`，`Total Test time (real) = 2.51 sec`，逐条 `N/68 Test #N: … Passed` 共 68 行，无 Skip/Disabled |
| 上游套件 | `sexpp-tests`（`gtest_discover_tests` 枚举 6 个套件：BaselineTests 3 / ExceptionTests 22 / PrimitivesTests 26 / G10CompatTests 1 / G23CompatTests 9 / G23ExceptionTests 7） |
| 消费者测试（test_package） | 10 条断言全绿 → `ALL CONSUMER CHECKS PASSED`，退出码 0 |
| 产物 | `lib/libsexpp.a`、`bin/sexpp`（ELF 64-bit LSB arm64, `/lib/ld-musl-aarch64.so.1`）、`include/sexpp/{sexp,sexp-error,sexp-public,ext-key-format}.h`、`lib/pkgconfig/sexpp.pc`、`share/man/man1/sexpp.1` |
| gtest 来源 | `gtest/1.17.0`（`test_requires`，日志 `Already installed! (1 of 2)`，无网络拉取） |

### 捕获流环境矩阵（同机实测，支撑知识草稿）

用只依赖 `gtest/1.17.0` 的独立探针（2 个 `CaptureStdout/CaptureStderr` 用例，不含 sexpp 代码）：

| 注入变量 | 结果 | 实际路径 |
|---|---|---|
| 全不设 | FATAL + Signal 6 | `/data/local/tmp/…` |
| `TMPDIR=<可写>` | `[ PASSED ] 2 tests` | — |
| 仅 `TEST_TMPDIR=<可写>` | FATAL + Signal 6 | `/data/local/tmp/…` |
| 仅 `TMP`+`TEMP=<可写>` | FATAL + Signal 6 | `/data/local/tmp/…` |
| `TMPDIR=/nonexistent` + `TEST_TMPDIR=<可写>` | FATAL + Signal 6 | `/nonexistent-xyz/…` |

配套事实：`mount` 显示 `/dev/block/dm-0 on /tmp type erofs (ro)`，`touch /tmp/x` → `Read-only file system`；
OHOS clang 下 `__ANDROID__` 未定义、`__OHOS__` 已定义 ⇒ gtest 走非 Android 分支，
该分支的 `getenv("TMPDIR")` 行为完全来自制品仓补丁
`archives/g/gtest/1.17.0/patches/0001-tmpdir-ohos-sandbox.patch`。
详细因果链、版本对照表与查重见
`knowledge/drafts/DRAFT-sexpp-0.8.7-gtest-capture-stdout-tmpdir-only.{md,kv}`。
