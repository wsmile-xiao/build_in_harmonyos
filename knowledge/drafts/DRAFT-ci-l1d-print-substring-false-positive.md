# DRAFT-ci-l1d-print-substring-false-positive — CI L1d "fake test" 误报：可执行文件名含 print/echo/true 子串

> **Contributor**: pc7-1 | **Status**: DRAFT | **Updated**: 2026-09-20
> **Severity**: medium | **Category**: ci / test / false-positive
> **Audience**: 所有在 test_package 中使用 `cmake --build ... --target test` 或 ctest 方式运行消费者可执行文件的库

## 问题（真实首错）

W3 本地 CI 模拟（`ci/conan/build_and_test.sh`）L1d 检查报：

```
[fail] L1d: test() method appears to be a fake test (echo/print/true only)
```

L1 结论 `fake test detected`，W3 整体失败。但测试包本身是真实消费者测试：
`test_package/conanfile.py` 的 `test()` 方法只有一行 `cmake --build <builddir> --target test`，
通过 CTest 构建并运行真实的消费者可执行文件（asprintf.c 实例：`test_consume`，
内部 4 组 asprintf 断言全部真实通过，`1/1 Test #1: test_consume ... Passed`）。

## 根因

L1d 的启发式（`build_and_test.sh` L1337）：

```sh
grep -qE "self\.run.*(echo|print|true)" "$TEST_PKG_DIR/conanfile.py"
```

该模式是**子串匹配**：只要 test_package/conanfile.py 中任一 `self.run(...)` 行
在 `self.run` 之后（同一行内）出现 `echo`、`print` 或 `true` 子串即判 fail。
当消费者可执行文件名包含这些子串（如 asprintf 库最初命名 `test_asprintf_c`，
其中 `asprintf` 含 `print`）且该行同时是 `self.run("cmake --build ... --target test")`
一类长命令行时，子串命中，产生误报。测试本身完全真实（有真实断言、真实链接库产物、
真实退出码 0）。

## 解决方案

1. **执行端（推荐，已在 asprintf.c 验证）**：重命名消费者可执行文件，使其名字
   不含 `echo`/`print`/`true` 子串（asprintf.c：`test_asprintf_c` → `test_consume`），
   同步更新 `test_package/CMakeLists.txt` 的 `add_executable` 与
   `test_package/MANIFEST.yml` 的声明，重跑 `conan-verify`/W3 复验通过。
   命名建议：`test_consume`、`<lib>_consumer`、`demo_<lib>` 等不含禁用子串的词。
2. **CI 维护端（根治）**：将 L1d 模式改为词边界/独立词匹配，例如
   `self\.run\s*[("'].*\b(echo|print|true)\b` 并排除 `--target`/`add_executable`
   构建上下文；或在判 fail 前先校验 test() 是否引用了包内构建目标（有真实
   构建+运行证据时豁免）。此条不在执行端权限内，仅作为根治建议上报。

## 验证

- asprintf.c/0.0.3 实例：重命名后 W3 重跑，L1d 不再命中，
  `1/1 Test #1: test_consume ... Passed`，W3 `exit_code=0`。
- 反证：重命名前同一测试代码（仅名字不同）必中 L1d，证明差异来自名字子串而非测试内容。

## 适用边界

- ✅ 适用：test_package 消费者可执行文件名（或 self.run 命令行内任何标识符）
  含 `print`/`echo`/`true` 子串，且测试本身真实（真实断言+链接包产物+退出码 0）。
- ❌ 不适用：test() 真的只有 echo/print（无真实构建/运行）——那是真 fake test，
  应按 L1d 原意修复测试而不是改名字。
- ⚠️ 与 `E251`（禁止虚假测试结果）不重复：E251 针对"伪造测试通过结果"的审核红线，
  本条针对 CI 启发式对真实测试的子串误报；一个治理行为，一个治理检测器。

## 禁止

- ❌ 为绕过 L1d 而把真实消费者测试弱化成 `self.run("echo ok")` 一类空壳（触发 E251 红线）。
- ❌ 把"改名字"当成掩盖真实失败的手段；改名后必须重跑 W3 且测试仍真实运行。

## Source

- 库/事件：asprintf.c 0.0.3 OHOS 适配（task asprintf.c-0.0.3-r01-pc7-1-20260920T123513Z），
  首轮 W3 L1d `fake test detected` → 重命名 `test_asprintf_c`→`test_consume` 后 W3 通过。
- 证据：`ci/conan/build_and_test.sh` L1335-1343（启发式原文）、W3 日志
  `archives/a/asprintf.c/0.0.3/reports/w3-local-ci.log`（隔离复验后通过记录）。
