# clove-unit 2.4.6 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-27
- 编译器: clang 15.0.4（aarch64-unknown-linux-ohos）
- 状态: built（HarmonyOS 真机验证通过）
- 特殊说明: header-only 单头文件库，包内无编译产物；`build()` 只为跑上游测试

## 库简介

clove-unit 是单头文件（`clove-unit.h`，198 KB）的 C 单元测试框架，可与 C++
互操作，带**测试自动发现**（runner 用 `dl_iterate_phdr` + ELF `SHT_SYMTAB`
符号表扫描定位 `__clove_sym___<suite>___<test>` 形态的用例函数）。
- 上游仓库: https://github.com/fdefelici/clove-unit
- 许可证: MIT
- 类型: header-only（CMake `add_library(clove-unit INTERFACE)`）
- 上游 tag: `v2.4.6` → commit `ef6676f9f4ee870970b0626ae8eae4831dd7ada0`

## Conan 配方说明

### 配方结构
- `conanfile.py`：Conan 配方，CMake 工具链，`build()` 内跑上游 CTest
- `conandata.yml`：源码 URL + sha256 + 1 个补丁
- `patches/0001-sanity-drop-unsupported-leak-sanitizer.patch`：见下「平台适配」
- `test_package/`：消费者冒烟（3 用例/8 断言）+ 鸿蒙专项（16 项断言）

### 关键配置
- `package_type = "header-library"` + `self.info.clear()`：纯头文件库，所有
  settings 组合产出相同包内容（同 CCI 官方配方）
- `no_copy_source = True`：源码不复制进 build()，故补丁在 `source()` 内打
- `CLOVE_CMAKE__UC_BUILD=ON` + `CLOVE_CMAKE__UC_SANITY=ON`：对应上游 CI 的
  `build_{windows,macos,ubuntu}` 与 `sanity_check` 两条 job 线
- `package()` 用 `copy()` 而非 `cmake.install()`：上游 `CMakeLists.txt` 用
  `clove_join_paths` 把 `CMAKE_INSTALL_PREFIX` 改写成
  `${CMAKE_INSTALL_PREFIX}/clove-unit/${VERSION}`，`cmake.install()` 会把头文件
  落进 `<pkg>/clove-unit/2.4.6/include/`（conan 需要 `<pkg>/include/`）

## 平台适配

- **R32**：`self.settings.os in ("Linux", "OHOS")` 平台判断，不用 `== "Linux"`
- **补丁 0001**：上游 `tests/stricts/clove-sanity/CMakeLists.txt` 硬编码
  `-fsanitize=address,leak,undefined`，设备与 CI 的 clang-15 对
  `aarch64-unknown-linux-ohos` 目标直接拒绝该选项：

  ```
  clang-15: error: unsupported option '-fsanitize=leak' for target 'aarch64-unknown-linux-ohos'
  ```

  （实测 `-Wno-unsupported-option` 也无法抑制，属 driver 级硬错误；OHOS 目标未启用
  LeakSanitizer。）补丁只移除 `leak` 这一个 sanitizer 选项，**保留
  `-fsanitize=address,undefined`，测试源码与 12 条 CTest 注册命令零改动**。
  依据 `docs/TEST_QUALITY_SPEC.md` §3.3「在 conandata.yml 的 patches 中添加补丁
  修复测试」。补丁已实测 `patch -p1` 干跑 + 实打 + 与目标文件逐字节 `cmp` 一致。
- **ctest 空跑防护**：`build()` 先 `ctest -N` 断言 `Total Tests: 13`，不符即
  `exit 17`，再 `ctest --output-on-failure`——避免 `No tests were found!!!` +
  rc=0 的结构性假绿。
- **沙箱 HOME**：上游测试与消费者测试均在 `HOME="$TASK_DIR/test-home"` 下执行，
  不写用户真实 HOME。

## 上游测试面盘点（计数口径见 PR 正文两表）

| 上游测试面 | 用例/命令数 | 上游 CI 是否执行 | 本次是否执行 |
|---|---|---|---|
| `tests/functs` CLoveUnitTest | 175（clove `-l` 框架注册 / 22 suite） | 是（build_* 10 legs） | 是 175/175 |
| `tests/functs/resources/prj01` | 3（被 INTE 集成用例子进程拉起） | 是 | 是 |
| `tests/stricts/clove-sanity` | 12（CTest 命令 `Sanity_uc_*`） | 是（sanity_check） | 是 12/12（补丁后） |
| `tests/stricts/clove-c`、`clove-cpp` | 2（-Werror 严格编译检查，无 `add_test`） | 仅编译 | 是（编译通过） |
| `examples/clove101`、`clovepp` | 18（示例程序，无 `add_test`） | 仅编译 | 是（编译通过） |
| `tests/perfs` | 60000（`perf_generator.c` 生成的 `CLOVE_PASS()` 空用例） | 否（`CLOVE_CMAKE__UC_PERFS` 默认 OFF） | 否（同上游） |

**N（上游测试总数，四口径取值）**：
1. 源码宏数 `CLOVE_TEST(`：`tests/` 下 60182（含 perfs 60001）
2. 框架注册数（`CLoveUnitTest -l` + sanity/夹具）：175 + 3 + 1 = 179
3. assertion 数（`CLOVE_ASSERT` 族调用）：477（CI 执行面）
4. 消费者断言数（test_package）：24

声明 **N = 190 = 175 + 3 + 12**（上游 CI 实跑的测试条目：框架注册用例 + CTest
注册命令），差额逐项归因见上表：perfs 60000 为默认关闭的生成式性能基准、examples
与 stricts 上游 CI 只编译不执行。

## 依赖

0 个运行依赖、0 个编译依赖（W0 逐一核过：ConanCenterIndex 配方 `requirements()`
为空，本仓库也无需 `tool_requires`——cmake/clang/ctest 均为设备与 CI worker 自带）。

## 知识

G2 未失败、engine 未命中，按 §3.8 **零草稿为正常终态**（`knowledge_ref: []`）。

编译结束。
