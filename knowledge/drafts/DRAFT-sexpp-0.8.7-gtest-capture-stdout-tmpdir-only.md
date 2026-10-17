# DRAFT-sexpp-0.8.7-gtest-capture-stdout-tmpdir-only：OHOS 上 gtest 捕获流只认 `TMPDIR` 一个变量，且是制品仓补丁给的、不是上游给的

> Contributor: iKalous_OscarP | Status: Draft | Updated: 2026-09-19
> Source: sexpp 0.8.7 HarmonyOS PC 适配（68 个上游 GoogleTest 用例全部真跑，含 2 个 `CaptureStdout` 用例）
> draft: true

## 一句话机制

在 OHOS 真机上，gtest `CaptureStdout()/CaptureStderr()` 的临时文件目录**只由 `TMPDIR` 一个环境变量决定**；
而这个能力**不是 googletest 上游版本自带的**，是制品仓 `gtest/1.17.0` 配方里
`patches/0001-tmpdir-ohos-sandbox.patch` 补出来的。因此：链接制品仓 gtest 的库，
**一行 `TMPDIR=<可写目录>` 就能跑满捕获流用例，不存在"平台阻塞"**；
而链接系统/内置（未打补丁）googletest 的构建，`TMPDIR/TMP/TEMP/TEST_TMPDIR` 四个变量**全都不认**。
判据只看报错里的路径前缀：`/data/local/tmp/…` = 命中补丁 = `TMPDIR` 有效；`/tmp/…` = 未打补丁 = 环境变量一律无效。

## 错误特征（真机原文，非转述）

```
[WARNING] .../googletest/src/gtest-port.cc:1148:: Failed to create tmp file /data/local/tmp/gtest_captured_stream.XXXXXX for test; does the test have access to the /tmp directory?
[ FATAL ] .../googletest/src/gtest-port.cc:1172:: Failed to open tmp file /data/local/tmp/gtest_captured_stream.XXXXXX for capturing stream.
Signal 6 (core dumped)
```

文件系统证据：

```
$ mount | grep /tmp
/dev/block/dm-0 on /tmp type erofs (ro,relatime,hmmac=inherit_parent)
$ touch /tmp/sx_probe
touch: '/tmp/sx_probe': Read-only file system
```

`/data/local/tmp` 对 `currentUser` 同样不可写——这正是上面 FATAL 的直接原因，
所以"回退到 `/data/local/tmp` 就能活"是不成立的，必须显式给 `TMPDIR`。

## 5 案例环境矩阵（独立探针，代码里没有任何 sexpp 影子）

探针只依赖制品仓 `gtest/1.17.0`（包 `21b17f8b2bc0e9511e276e3d57a23893067cefe5`），
2 个用例分别调用 `CaptureStdout()/GetCapturedStdout()` 与 `CaptureStderr()/GetCapturedStderr()`：

| # | 注入的环境变量 | 结果 | 报错/通过里的实际路径 |
|---|---|---|---|
| 1 | 全部不设（`-u TMPDIR -u TEST_TMPDIR`） | **FATAL + Signal 6** | `/data/local/tmp/…` |
| 2 | `TMPDIR=<可写>` | **`[ PASSED ] 2 tests`** | — |
| 3 | 只给 `TEST_TMPDIR=<可写>` | **FATAL + Signal 6** | `/data/local/tmp/…` |
| 4 | 只给 `TMP=<可写> TEMP=<可写>` | **FATAL + Signal 6** | `/data/local/tmp/…` |
| 5 | `TMPDIR=/nonexistent-xyz` + `TEST_TMPDIR=<可写>` | **FATAL + Signal 6** | `/nonexistent-xyz/…` |

读法：2 与 3/4 对照 ⇒ 只有 `TMPDIR` 被读；5 的报错路径是那个**不存在的** `TMPDIR` 值
⇒ `TMPDIR` 优先级压过 `TEST_TMPDIR`，`TEST_TMPDIR` 根本没参与决策。

同一结论在真实上游套件上复现（sexpp 0.8.7 的 `sexpp-tests`）：

| 命令 | 结果 |
|---|---|
| `env -u TMPDIR -u TMP -u TEMP ./sexpp-tests`（全量 68） | 跑到 `ExceptionTests.SexpWarning` 即 `Signal 6`，整个二进制崩 |
| `TMPDIR=<可写> ./sexpp-tests` | `[==========] 68 tests from 6 test suites ran.` → `[ PASSED ] 68 tests.` |
| `conan create` 内（配方注入 `TMPDIR` 后 `cmake.test()`） | `100% tests passed out of 68`，`CREATE_RC=0` |

## 根因分析

补丁改的是 `CapturedStream` 的 **`#else` 分支**（`archives/g/gtest/1.17.0/patches/0001-tmpdir-ohos-sandbox.patch`）：

```diff
 #else
-    name_template = "/tmp/";
+    // OHOS sandbox: /tmp is read-only; use TMPDIR env var when set
+    const char* ohos_tmp = getenv("TMPDIR");
+    name_template = ohos_tmp ? ohos_tmp : "/data/local/tmp/";
+    if (!name_template.empty() && name_template.back() != GTEST_PATH_SEP_[0])
+      name_template.push_back(GTEST_PATH_SEP_[0]);
 #endif
```

为什么 OHOS 会落到 `#else` 分支（而不是 Android 分支）——用同一套 SDK clang 实测预处理宏：

```
$ clang++ --target=aarch64-linux-ohos ... ; ./macros
__ANDROID__ defined  0        # 关键：OHOS 不定义 __ANDROID__
__OHOS__ defined     1
__linux__            (GTEST_OS_LINUX 走 generic 分支)
-> gtest port-arch picks GTEST_OS_LINUX (generic, non-Android)
```

`gtest-port-arch.h` 里 `GTEST_OS_LINUX_ANDROID` 只在 `__ANDROID__` 时定义，OHOS 不满足，
所以编译期选中的正是被补丁改写的那条 `#else`。**结论：让 `TMPDIR` 生效的是这个补丁本身，与 googletest 版本无关。**

上游各版本对照（逐 tag 取 `googletest/src/gtest-port.cc` 的 `name_template` 赋值行）：

| 版本 | Android 分支 | 非 Android 分支（OHOS 实际走的） | 结论 |
|---|---|---|---|
| v1.14.0 | `:1067 "/data/local/tmp/"` 硬编码 | `:1090 "/tmp/"` 硬编码 | 无 env |
| v1.15.2 | `:1106 TempDir()`（读 `TEST_TMPDIR`→`TMPDIR`） | `:1132 "/tmp/"` 硬编码 | OHOS 仍无 env |
| v1.16.0 | `:1106 TempDir()` | `:1132 "/tmp/"` 硬编码 | OHOS 仍无 env |
| v1.17.0 | `:1106 TempDir()` | `:1132 "/tmp/"` 硬编码 | OHOS 仍无 env |

即：**即便升到 1.17，未打补丁的 OHOS 构建依然不读任何环境变量**——`TempDir()` 只在 Android 分支被调用。
这解释了为什么"升级 gtest 版本"不是解法，而"链接制品仓的 gtest 包"才是。

## 解决方案

**推荐**：需要捕获流用例真跑时，用 `test_requires("gtest/1.17.0")` 拿制品仓的补丁版 gtest，
并在 `build()` 里跑测试前导出 `TMPDIR` 到构建目录下的可写子目录（3 行，无源码补丁、无平台宏）：

```python
if can_run(self):
    tmpdir = os.path.join(self.build_folder, "gtest-tmp")
    os.makedirs(tmpdir, exist_ok=True)
    test_env = Environment()
    test_env.define("TMPDIR", tmpdir)          # 只此一个变量
    with test_env.vars(self).apply():
        cmake.test()
```

配套（同一次适配里必须的另两点）：`DOWNLOAD_GTEST=OFF` 阻断上游 FetchContent 拉
`github.com/google/googletest.git`（真机不可达），并把 `GTest_DIR` 指到 conan 包内
`lib/cmake/GTest`，同时接受 config 模式导出的 `GTest::gtest/GTest::gtest_main` 目标名。

**禁止做法（均有实测依据）**：

1. `--gtest_filter=-*Warning*` 排除捕获流用例、再把它们写成"平台阻塞"。
   实测链接制品仓 gtest 时这 2 个用例**可以真过**，排除后 66/68 属台账失真（rule2/rule4/rule8–9 风险），
   并且会让下一个读 notes 的人以为无解。
2. 只设 `TMP`/`TEMP` 或只设 `TEST_TMPDIR`。矩阵 3/4/5 已实测为 no-op；
   按"POSIX 惯例三变量一起设"来兜底并不会带来额外效果，反而掩盖真正生效的那个变量。
3. 给被测库再写一份 gtest 源码补丁（改 `gtest-port.cc`）。与制品仓补丁重复，
   还会把测试框架的改动混进本库的 `patches/`，属 JC/AI 检视噪声。
4. 用"我这边设了 TMPDIR 还是崩"否定本条。**先确认链接的是哪个 gtest**：
   报错路径是 `/tmp/` 就是未打补丁的构建（系统/`FetchContent`/bundled），本条不适用。

## 通用性证据

- 独立探针（本节矩阵）：源码不含 sexpp，只调 googletest 的捕获流 API ⇒ 机制与"被测库是谁"无关。
- 第二个库（真实上游套件）：sexpp 0.8.7 的 68 用例 / 6 套件，同一配方在清缓存后重跑
  `conan create` 得 `100% tests passed out of 68`、`CREATE_RC=0`。
- 反向对照即本库同族版本：sexpp 0.9.1（main 已合入）在**未走该路径**时记的是
  `80/82 + 2 项平台阻塞`，其报错路径为 `/tmp/…`，与本节机制预测完全一致
  （未打补丁的构建 ⇒ env 无效）。同一套用例、同一台设备、两种链接方式，结果 2↔0 之差即由本机制解释。
- 适用面：所有"上游测试含 `CaptureStdout/CaptureStderr`"且用 conan+ctest 的 C/C++ 库
  （典型如各类 parser/CLI 库的 warning 断言用例）。

## 查重反证（main tip `85bce6366` 实测，540 条正式 E 条目 / 2378 个 drafts 文件）

| 相邻条目 | 它说了什么 | 与本条的可执行区别 |
|---|---|---|
| `E292`（正式，`layered-ctest-migration`） | 建议"补齐 `TEST_TMPDIR/TMPDIR`"，把 gtest TMPDIR 归入"测试框架运行环境" | E292 未指出捕获流**只认 `TMPDIR`**（矩阵 3 实测 `TEST_TMPDIR` 无效，即 E292 的推荐变量之一对本场景是 no-op），也未记录能力来自制品仓补丁、更无"看报错路径判分支"的判据。反证：`git grep -il 'tmpdir-ohos-sandbox' origin/main -- knowledge` → 仅 1 个文件命中，且那是下面这条： |
| `DRAFT-gtest-1-17-0-1-cmake-components.md` | 明确写"`0001-tmpdir-ohos-sandbox.patch` … 与 E292 的 GTest TMPDIR 范围重复，**不作为增量**" | 该判断把本机制当作已覆盖而放弃记录，实际 E292 与任何正式条目都没有本节的变量矩阵/判据/补丁定位。本条即补这个被误判为"已覆盖"的缺口 |
| `DRAFT-sexpp-0.9.1-gtest-captured-stream-tmp-hardcode`（.kv/.md） | "**GTest 的 `CapturedStream` 不读 TMPDIR/TMP/TEMP 任何环境变量**……环境层无解" | 直接冲突。该结论仅在未打补丁的构建（其日志路径为 `/tmp/…`）成立；链接制品仓 `gtest/1.17.0` 时矩阵 2 实测 2/2 通过。**勘误见下** |
| `DRAFT-googletest-1.12.1-ohos-test-platform-constraints` | "硬编码 `/tmp/` 的入口 `$TMPDIR` 不适用，需逐入口确认"（1.12.1 实测 35/63） | 版本口径会误导：本条 4 行版本表显示 OHOS 走的是非 Android 分支，**1.14→1.17 该分支恒为硬编码 `/tmp/`**，所以"升级 gtest"不能救，只有制品仓补丁能救；其"逐入口确认"结论仍成立，属边界补充 |
| `DRAFT-cssc-gtest-tmp-hardcode-death-test-abort` | googletest ≤1.6/1.7 bundled 硬编码，需给 bundled `gtest-port.cc` 打 `getenv("TMPDIR")` 补丁 | 场景是 **vendored 老 gtest**（补丁打在库源码上）；本条场景是 **链接制品仓包**（补丁已在包里，禁止重复打）。两者互为"是否已存在补丁"的边界 |
| `E272`（正式） | "OHOS libc `tmpfile()` 忽略 `TMPDIR`" | 相邻但不同层：`tmpfile()` 属 musl，确实忽略 `TMPDIR`；`CapturedStream` 属 gtest 且经补丁后读 `TMPDIR`。混用会得出"OHOS 上一切临时文件都不认 TMPDIR"的错误外推 |
| `E002/E265/E363`（正式） | 通用只读 `/tmp` + `TMPDIR` 方案 | 它们是"程序自己读 `TMPDIR`"的通用条目；本条给出 gtest 这一特例的**前置条件**（必须链接被打补丁的包），属 `caused_by` 下游 |

## 对既有条目的勘误

`DRAFT-sexpp-0.9.1-gtest-captured-stream-tmp-hardcode` 与 `archives/s/sexpp/0.9.1/notes.md` 问题表第 3 条、
`archives/s/sexpp/0.9.1/reports/test-report.md` 记为"平台阻塞、`TMPDIR` 无效、计入分母不计通过"的两项
（`ExceptionTests.SexpWarning`、`G23ExceptionTests.G23Warning`）：

- **不成立的前提**：结论来自未打补丁的 googletest 1.14 构建（其日志路径为 `/tmp/gtest_captured_stream.XXXXXX`）。
  制品仓 `gtest/1.17.0` 已带 `getenv("TMPDIR")` 补丁。
- **可复现的反证**：在本节矩阵 2 中，同一设备、同为捕获流的 2 个用例 `TMPDIR=<可写>` 下通过；
  sexpp 0.8.7 的 `conan create` 用 `test_requires("gtest/1.17.0")` + `TMPDIR` 注入得 `100% tests passed out of 68`。
- **影响**：照旧结论执行的会话会稳定少报 2 个用例并放弃修复机会。建议主编把该草稿改写为
  "分未打补丁/已打补丁两种构建"，并保留其 `/tmp/` 分支判据作为本条的 `similar_to`。

## 证据

| 项 | 值 |
|---|---|
| 库/版本 | sexpp 0.8.7（`archives/s/sexpp/0.8.7/`） |
| 分支 | `feat/sexpp-0.8.7` |
| 上游 tag tarball | `https://codeload.github.com/rnpgp/sexpp/tar.gz/refs/tags/v0.8.7`，sha256 `d877a2a3…66ba2b` |
| 上游用例清点 | `grep -rhE '^TEST(_F\|_P)?[[:space:]]*\(' tests/src/*.cpp \| wc -l` → 68（无 `#if 0` 用例） |
| 真机结果 | `conan create` 清缓存重跑 `CREATE_RC=0`；ctest `100% tests passed out of 68`；消费者断言 10/10 `ALL CONSUMER CHECKS PASSED` |
| 产物 | `lib/libsexpp.a` `bin/sexpp`（ELF 64-bit arm64）`include/sexpp/*.h` `share/man/man1/sexpp.1` |
| 依赖补丁 | `archives/g/gtest/1.17.0/patches/0001-tmpdir-ohos-sandbox.patch` |

## 元信息

- `id: DRAFT-sexpp-0.8.7-gtest-capture-stdout-tmpdir-only`
- `draft: true`
- `contributor_id: iKalous_OscarP`
- `doc_file: knowledge/drafts/DRAFT-sexpp-0.8.7-gtest-capture-stdout-tmpdir-only.md`
- 机器可读字段见同名 `.kv`；本条为路径 B 增量，`archives/` 侧改动只有 sexpp 0.8.7 目录与 `archives/s/sexpp/commands.json`。
