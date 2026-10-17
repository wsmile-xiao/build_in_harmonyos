# svgpp 1.3.1 test report

## Counting method

计数单位 = 一个 gtest 用例（可执行实例）。上游套件以 `ParserGTest` 的控制台汇总与
`--gtest_output=xml` 双向对账为权威；消费者侧以 `test_package` 内一个真实执行程序为一个用例，
其内部断言数（assertions）单列，不与用例数混计。静态源码计数（宏声明数）**只用于申报上游分母**，
不作为执行数。

## Results

| Environment | Test group | Passed | Failed | Skipped | Assertions | Result |
|---|---|---:|---:|---:|---:|---|
| HarmonyOS PC (OHOS 6.0 / armv8-aarch64), `conan create` 内 `build()` | 上游 `ParserGTest` | 200 | 0 | 0 | n/a (gtest 汇总) | PASS |
| 同上 | 消费者程序 `test_svgpp`（`test_package`） | 1 | 0 | 0 | 24 | PASS |
| 合计（适配后执行） | — | 201 | 0 | 0 | 24 | PASS |

上游分母（静态源码清点，逐文件行首锚定）：宏声明 **52** = `TEST` 29 + `TEST_F` 4 + `TEST_P` 19；
纳入 `ParserGTest` 目标的注册宏 **50**（`path_adapter_test.cpp`、`supported_value_parsers_test.cpp`
各 1 个 `TEST` 被上游自己从源列表注释掉）。静态 52 → 执行 200 的反向差集由三类叠加机制解释：
19 个 `TEST_P` 经 19 处 `INSTANTIATE_TEST_SUITE_P` 按参数集展开为 165 个实例；
`transform_strict_grammar_test.cpp` 仅 `#define` + 重包含 `transform_grammar_test.cpp`，把 4 个 `TEST`
以同名套件在严格分隔符模式下再执行一遍（故非参数化 31 + 4 = 35）；注册数 50 = 52 − 2。

## Raw evidence（本目录内，逐条可按行号复算）

| 项 | 原文 | 位置 |
|---|---|---|
| 构建动作 | svgpp/1.3.1: RUN: cmake --build "/storage/Users/currentUser/tmp/ch/home-zhuli5-svgpp/p/b/svgppea051ae36c61a/b/build-release" --target ParserGTest -- -j20 -j4 | `reports/w3-local-ci.log:215` |
| 编译对象 | `ParserGTest` 目标 216–241 区间内 `Building CXX object` **26** 行 = 23 个 svgpp 测试 TU + 3 个 vendored gtest/gmock（`gtest-all.cc.o` / `gmock-all.cc.o` / `gmock_main.cc.o`）；紧接 242 行 `[27/27] Linking CXX executable ParserGTest`（26 编译 + 1 链接 = 27 步）。全文另有 1 行 `Building CXX object` 属 `test_package` 消费者编译 （`CMakeFiles/test_svgpp.dir/test_svgpp.cpp.obj`），故全文计数 27，**引用时须写明区间** | 同文件 216–241、242 |
| gtest 汇总 | `[==========] 200 tests from 30 test cases ran. (7 ms total)` | 同文件 739 |
| gtest 结果 | `[  PASSED  ] 200 tests.` | 同文件 740 |
| 消费者执行 | `svgpp consumer test: checks=24 failures=0` | 同文件 825 |
| W3 本地 CI 模拟 | `exit_code=0 step=W3_local_ci timestamp=2026-09-23T21:25:24.104127 integrity_hash=46b07b53da2d31e4` | `../.ci-result.json` |
| 本日志完整性 | sha256 `e53fe11a4345378e6eede82f4f8a3f8e5156aabe151422550e64f185c086e7a3` | 与 `.ci-result.json` 的 `log_sha256` 逐字符一致 |

## Consumer scenarios（层 2，`test_package/test_svgpp.cpp`）

以库使用者身份编译、链接并调用 svgpp 公开 API，24 条断言覆盖路径元素的解析结果与几何量值比对，
退出码由断言结果决定（`checks=<n> failures=<m>` 自证输出）。交叉构建下未跳过程序执行。

## Not covered（如实声明，不计入通过）

- `CheckHeadersAutonomy`：每个公开头生成一个只做 `#include` 的 TU 的**编译期**自治检查，无运行期用例，
  未纳入 `build()`（成本全在编译期，约 150+ TU）；同一批头文件的实际使用由 `ParserGTest` 的 200 例提供主证据。
- `FullParseTest`：自带 `main()`、需命令行传入 SVG 文件，属解析基准工具而非测试套件，未执行。
- `include/svgpp/policy/xml/*`：上游自身的头自治检查亦刻意排除该目录（XML 后端由使用者自带），
  本配方不单独编译，与上游口径一致。
- `conan-verify` 的 **L2 / L4 / L5 本轮未执行**（报告中记 PASS 但正文为 `⏭️ 跳过（无 cache 路径）`），
  **G4 为降级 PASS**（`⚠️ 无法找到程序包 ID`）：根因是 `conan_verify.py` 的 package ID 正则匹配不了含点号
  版本号，属工具既存缺陷（知识库 **E478** 已收录）。故包内容清点改由下表手工实测代替，本文件不把
  G4/L2/L4/L5 当作独立产物证据引用。

## Package contents（手工实测，代 E478 所缺的 G4 环节）

- 包实体目录：``/storage/Users/currentUser/tmp/ch/home-zhuli5-svgpp/p/b/svgppea051ae36c61a/p``
- `include/` 下安装的文件数：**191**
- 除 `include/` 外的随包产物：`conaninfo.txt`、`conanmanifest.txt`、`licenses/LICENSE_1_0.txt` 等 3 个
- `package_type = "header-library"` ⇒ 无 ELF 可 `readelf` 属预期，不是缺口。

## Integrity

- 官方源 SHA-256：`be8a89df72d01cf062cc9815dd64c9576b4d20910d6d7aee7f0ea26484dc5e76`
  （`conandata.yml` 与 `manifest.yaml` 同源；仅官方 https 单 URL，无镜像前缀，R39）
- 构建环境：clang 15.0.4（`/data/service/hnp/bin`）、profile `ci/conan/profiles/ohos-aarch64`
  （host == build，native）、Conan 2.29.1、私有 `CONAN_HOME=~/tmp/ch/home-zhuli5-svgpp`
- 验证命令：
  `ohc-run.py conan-verify svgpp 1.3.1`（RC=0，G0–G4 记 PASS）→
  `ohc-run.py finish svgpp 1.3.1 built`
- 配方 `conanfile.py` 最后一次改动时间早于上表 W3 证据时间戳 ⇒ 证据与代码同源；
  其后的整改提交只动描述类交付物，`conanfile.py`、`test_package/` 与 `patches/` 一字未改。
- 未修改任何上游源码或测试文件；零补丁（`conandata.yml` 的 `patches:` 为空）。
