# Test Report — md4c 0.5.2

**Date**: 2026-09-07
**Build System**: CMake
**Platform**: HarmonyOS PC (OHOS aarch64, clang 15)

## 上游测试全量枚举台账（测试源逐项分类）

测试源位于官方 tag `release-0.5.2` 源码 `test/` 目录（`/storage/Users/currentUser/tmp/builds/md4c-0.5.2.work/test/`）。

| 测试源文件 | 类型 | 是否独立上游用例 | 数量 | 分类理由 |
|---|---|---|---|---|
| `test/run-testsuite.py` | 用户测试驱动脚本 | 否（框架驱动） | — | 上游测试驱动器，解析 spec 文件并调用被测程序 |
| `test/spec.txt` | 用户测试数据（CommonMark spec） | 是 | 652 | 每个由 `````` example 围栏包裹的 example 为独立用例 |
| `test/spec-hard-soft-breaks.txt` | 用户测试数据（扩展 spec） | 是 | 2 | 同上，example 围栏计数 |
| `test/spec-latex-math.txt` | 用户测试数据（扩展 spec） | 是 | 6 | 同上 |
| `test/spec-permissive-autolinks.txt` | 用户测试数据（扩展 spec） | 是 | 15 | 同上 |
| `test/spec-strikethrough.txt` | 用户测试数据（扩展 spec） | 是 | 5 | 同上 |
| `test/spec-tables.txt` | 用户测试数据（扩展 spec） | 是 | 12 | 同上 |
| `test/spec-tasklists.txt` | 用户测试数据（扩展 spec） | 是 | 5 | 同上 |
| `test/spec-underline.txt` | 用户测试数据（扩展 spec） | 是 | 4 | 同上 |
| `test/spec-wiki-links.txt` | 用户测试数据（扩展 spec） | 是 | 23 | 同上 |
| `test/regressions.txt` | 用户测试数据（Issue 回归） | 是 | 56 | 同上，bug 修复回归例 |
| `test/coverage.txt` | 用户测试数据（覆盖率补测） | 是 | 19 | 同上 |
| `test/pathological-tests.py` | 用户测试（压力用例） | 是 | 27 | 每对 input+regex 独立压力用例 |
| `test/normalize.py` | 框架辅助模块 | 否 | — | 测试框架工具，非独立用例 |
| `test/prog.py` | 框架辅助模块 | 否 | — | 测试框架工具（子进程驱动），非独立用例 |
| `test/fuzzers/fuzz-mdhtml.c` | 模糊测试源码 | 否 | — | 需 libFuzzer 专用工具链与编译入口，上游未随源码提供可执行 fuzz target 构建目标；不构成 ctest/常规测试注册项 |
| `test/fuzzers/seed-corpus/*.md` | fuzz 种子数据 | 否 | — | 数据文件，非独立用例 |
| `test/LICENSE.md` | 许可证文件 | 否 | — | 非测试 |

**上游用例总量（源码声明）**: 799（spec/regression example）+ 27（pathological）= **826**

## 双口径统计

| 口径 | 数量 | 说明 |
|---|---|---|
| `source_declared_total` | 826 | 官方 tag 源码中按 example 围栏/pathological dict 枚举的全部独立用例 |
| `executed_passed_total` | 826 | 本地构建上游 md2html（同源码同 tag）后全量实测：799 spec/regression 全过 + 27 pathological 全过 |
| 失败数 | 0 | — |
| 未运行数 | 0 | 全部实际运行（md2html 以 aarch64 本地构建，`test/` 全量执行） |
| 全量通过率 | **826/826 (100%)** | 通过数/全量发现数 |
| 当前 OHOS 配置可执行集合（conan create 内 test_package） | 1 | `test_md4c`（含 6 项 md_parse 回调断言），1/1 通过 |

> 说明：上游 spec 测试依赖 `md2html` 可执行文件做 HTML 回归比对。该工具在 Conan 配方中按设计关闭（仅打包库，`BUILD_MD2HTML_EXECUTABLE=OFF`），因此上游 826 例在 conan create 管道内不注册为单独可执行用例；为如实完成全量运行，本轮在 `.work` 源树中用同一 tag 源码本地构建 md2html 后全量执行 826 例，全部通过。OHOS 目标上的包级验证由 test_package 的 `test_md4c` 真实 API 断言承担（1/1 通过）。

## 鸿蒙专项测试（test_package，消费者视角）

`test_package/test.c` 链接 Conan 包 `md4c::md4c` 目标，调用真实 `md_parse()` API 断言 6 项回调行为：

1. `md_parse()` 返回 0（解析成功）
2. `enter_block(MD_BLOCK_DOC)` 触发
3. `enter_block(MD_BLOCK_H)` 触发且 heading level = 1
4. text 回调交付标题文本 "Title"
5. `enter_span(MD_SPAN_STRONG)` 对 `**bold**` 触发
6. text 回调交付加粗内文本 "bold"

**结果**: OHOS aarch64 目标下 `conan create` 内 ctest 1/1 通过（`Test Passed`，0.02s），日志见 `test_package/build/clang-15-armv8-17-release/Testing/Temporary/LastTest.log`。

## 构建验证

- `conan create`（ohos-aarch64 profile，静态库 `BUILD_SHARED_LIBS=OFF`）：通过
- test_package 消费者链接 + 运行：通过
- W3 本地 CI 模拟（setup.sh + build_and_test.sh）：通过（`.ci-result.json` exit_code=0）
- 基线隔离复验：W3 首次命中其他库既有基线文件 `archives/u/util-linux-login/2.42.2/.ci-trigger`（main 中 2026-09-03 已提交、空文件、SHA-256 `e3b0c442...b855`）；索引级临时隔离后复跑 W3 通过（JC5=pass），原样恢复并核对恢复后 SHA-256 与隔离前一致（`pre == post = e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`），当前库 diff/staged 不含该路径。