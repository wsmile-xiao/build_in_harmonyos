# barkeep 0.1.5 适配笔记

## 编译环境

- 构建系统: custom（**配方侧无库编译阶段**：header-only，`build()` 直调编译器编译并运行上游测试；上游 meson 树与 Makefile 在 release tarball 下不可用，见「遇到的问题」#1）
- 编译日期: 2026-09-26
- 编译器: clang/clang++ 15.0.4（`aarch64-unknown-linux-ohos`，libc++ **15004**）
- Conan profile: `ci/conan/profiles/ohos-aarch64`（os=OHOS / arch=armv8 / compiler=clang 15 / libc++ / **cppstd=17** / Release）
- 状态: built

## 编译步骤

1. `source()`：`get()` 下载 GitHub tag 归档
   `https://github.com/oir/barkeep/archive/refs/tags/v0.1.5.tar.gz`
   （sha256 `2577b09cfa7e5e117d13b765cfa4792f9e2b50719715786be275ae32dbf63b7c`，两次独立下载同值），`strip_root=True`；**无补丁可应用**。
2. `build()`：按上游 README「No tooling」口径直编三个测试翻译单元
   （`-O0 -std=c++20 -pthread -I<source> -I<catch2/2.13.10>/include [-I<fmt/11.1.3>/include]`），
   编译器取自 `tools.build:compiler_executables`（R33，不写死绝对路径）；随后逐个真跑，
   按 Catch2 v2 汇总行解析「test cases / assertions」计数，任一测试非零退出即 `ConanException` 构建失败；
   结果以 `HMBS_UPSTREAM_TEST_RESULT={...}` 一行写进 conan/CI 日志（见下表）。
3. `package()`：`barkeep/barkeep.h` → `include/barkeep/barkeep.h`，`LICENSE` → `licenses/`；
   `package_type="header-library"` + `package_id()` 清空 ⇒ 单一 package ID；`package_info()` 置空 bin/lib。
4. `test_package`：消费者从**已安装包头** include，在无 TTY（管道）形态下跑 23 项显式断言，失败即非零退出。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 `Makefile` 与 README 的 `-I./subprojects/Catch2_`、`-I./subprojects/fmt_` 编译必失败 | `subprojects/Catch2_`、`subprojects/fmt_` 是 **git 子模块**，release tarball 内为空目录（`find subprojects -type f` 仅 4 个 `.wrap`/`packagefiles` 文件） | 改用上游 README「No tooling」直编口径，头文件来自 `test_requires` 的 `catch2/2.13.10`（v2 单头，与上游 `branch = v2.x` 同族）与 `fmt/11.1.3`（`FMT_HEADER_ONLY`，不链接）；上游文件零改动 |
| 2 | `tests/test-stdfmt.cpp` 编译失败：`error: no member named 'vformat'/'make_format_args'/'format' in namespace 'std'` | OHOS SDK clang 15 + **libc++ 15004** 的 `<format>` 头存在但**未实现** `std::format`（设备最小探针 `std::format("{}", 42)` 同样失败） | 按「OHOS 缺特性」记 **NOT_RUN**（配方只在错误签名匹配时允许跳过，其它编译错误一律失败；若工具链将来支持则自动照常运行），不写成通过；同一测试面由 `test-fmtlib.cpp`（`BARKEEP_ENABLE_FMT_FORMAT`+`FMT_HEADER_ONLY`）等价覆盖 |
| 3 | CI profile 是 `compiler.cppstd=17`，上游要求 C++20 | 上游 `meson.build` `default_options: cpp_std=c++20`、`Makefile` `FLAGS=-std=c++20`；而 ohpcd 制品仓 `fmt/11.1.3` **只有 `cppstd=17` 二进制**，CI `conan create` 只允许重建本包（`--build=barkeep/*`） | 配方**不改** `settings.compiler.cppstd`（改了 CI 取不到 fmt 二进制），测试编译命令行显式 `-std=c++20`；`test_package` 用 `target_compile_features(... cxx_std_20)` 对消费者目标显式要求 C++20 |
| 4 | header-only 包 `conan-verify` 的 G4/L2/L4/L5 走「跳过」分支却并列打 `✅ PASS` | 路径解析缺陷（`device-facts` §二.17，必然命中而非偶发） | 报告中的 `⏭️ 跳过` 一律按显式 SKIPPED 处理，并人工补测写 `reports/conan-verify-supplement.md`（G4 产物清单↔`package_info()`、L2 真跑、L4 ELF 属性、L5 聚合 sha256） |
| 5 | release tarball 的 demo 程序（`tests/demo*.cpp`）含 10s 级 sleep 演示、无任何断言 | 上游 `tests/meson.build` 把 demo 也注册成 `test()` | 认定为**演示程序非测试用例**，不计入用例数（`test_package/MANIFEST.yml` 逐条登记），不冒充测试 |

## 源码修改

**无。** `patches` 为空，上游 tarball 106 个文件零改动；三个测试翻译单元是**配方侧**接入（直编译+运行），不涉及任何上游测试代码变更。

## 依赖版本

- 交付依赖：**0**（单头文件，仅标准库）
- 测试期（`test_requires`，不随包交付）：`catch2/2.13.10`、`fmt/11.1.3`

## 验证结果（R51 三步法）

**清点（源码宏数，`grep -E '^\s*(TEST_CASE|TEMPLATE_(LIST_)?TEST_CASE)\s*\('`，逐文件）**

| 文件 | 用例声明宏 | 框架注册（模板展开） | 状态 |
|---|---|---|---|
| `tests/test.cpp` | 19 | 59 | 实跑 PASS |
| `tests/test-fmtlib.cpp` | 5 | 20 | 实跑 PASS |
| `tests/test-stdfmt.cpp` | 5 | — | **NOT_RUN**（libc++ 无 `std::format`，见问题 #2） |
| **合计** | **29** | **79** | 候选数法取最大值 ⇒ **N = 79** |

- 上游**当前 HEAD**（`7d883ec3a12a16843d8abd8e9c30af730a6ac6bc`，= v0.1.6 提交）同口径源码宏 = **30**（比被审版本多 1 条 `TEMPLATE_LIST_TEST_CASE("Zero total progress")`，v0.1.5 中该行为注释态）；两者均 **≤ 声明 N=79**，无少报空间。
- **断言数随运行波动**（上游每个渲染帧都会重新断言，属上游测试设计），**权威读数取末轮**
  `reports/conan-create.log` 的 `HMBS_UPSTREAM_TEST_RESULT` 行；**用例数恒为 59 / 20（合计 79）**，
  消费者断言恒为 **23**（固定，不依赖时序）。

**运行（同一 SHA，沙箱 `HOME="$TASK_DIR/test-home"`）**

```text
test.out        → Passed all 59 test cases with … assertions.   rc=0
test-fmtlib.out → Passed all 20 test cases with … assertions.   rc=0
test-stdfmt     → 编译错误签名匹配 ⇒ NOT_RUN（不计入 executed）
test_package    → barkeep consumer checks: 23 run, 0 failed          rc=0
```
- `TOTAL = PASS + FAIL + SKIP + NOT_RUN`：上游用例 **79 = 79 + 0 + 0 + 0**（`test-stdfmt` 的 5 条**源码声明**因框架未注册而不在 N 分母内，作为 NOT_RUN 单列归因）。
