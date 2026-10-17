# coordgenlibs 3.0.2 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-25
- 编译器: clang/clang++ 15.0.4 (OHOS aarch64)
- 状态: built

## 官方来源
- 上游仓库: https://github.com/schrodinger/coordgenlibs
- 官方 tag: v3.0.2 (commit c4dd5b0e1f1971c06c7ab85725c185e47211814e)
- 源码包 URL: https://github.com/schrodinger/coordgenlibs/archive/refs/tags/v3.0.2.tar.gz
- 源码包 SHA-256: f67697434f7fec03bca150a6d84ea0e8409f6ec49d5aab43badc5833098ff4e3
- 下载说明: 本机 github.com 直连超时，改用 GitHub 官方 codeload 域名（codeload.github.com）下载同一官方 tag 的 tarball，解压内容与 tag 一致（77 个文件），SHA-256 核验通过。

## 编译步骤

1. init-build 初始化（registry→URL→下载→解压→骨架创建→环境检查）：
   `python3 scripts/ohc-run.py init-build coordgenlibs 3.0.2 --url=https://github.com/schrodinger/coordgenlibs/archive/refs/tags/v3.0.2.tar.gz`
   - 源码: /storage/Users/currentUser/tmp/builds/coordgenlibs-3.0.2.work
   - 归档: archives/c/coordgenlibs/3.0.2
2. 语言预检（R47）: `ohc-run.py lang-preflight coordgenlibs 3.0.2 --src $BUILD_SRC_DIR` → detected=cpp, exit 0
3. 库本体编译（测试关闭先验证）：
   `cmake -S . -B build-lib -DCOORDGEN_BUILD_TESTS=OFF -DCOORDGEN_BUILD_EXAMPLE=OFF -DCOORDGEN_BUILD_SHARED_LIBS=ON -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DCMAKE_CXX_COMPILER=/data/service/hnp/bin/clang++ -DCMAKE_C_COMPILER=/data/service/hnp/bin/clang -DCMAKE_BUILD_TYPE=Release`
   `cmake --build build-lib -j2` → libcoordgen.so 构建成功
4. 全量构建（含测试）：
   - 上游测试依赖 maeparser（schrodinger/maeparser v1.3.3，codeload 官方下载，SHA-256 78e7571a779ea4952e752ecef57c62fb26463947e29ef7f4b31b11988d88ca07）+ Boost（unit_test_framework/filesystem）
   - Boost 复用本机 conan 缓存已构建产物 boost/1.90.0（libc++/cppstd17/clang15/OHOS armv8，与 CI profile 一致）
   - `cmake -S . -B build-full -DCOORDGEN_BUILD_TESTS=ON -DCOORDGEN_BUILD_EXAMPLE=ON -DCOORDGEN_BUILD_SHARED_LIBS=ON -DCOORDGEN_RIGOROUS_BUILD=OFF -DCMAKE_POLICY_VERSION_MINIMUM=3.5 ...`
   - `cmake --build build-full -j2` → coordgen / example / test_coordgen / test_smilesparser 全部构建成功
   - 运行：`./test/test_coordgen --log_level=test_suite`、`./test/test_smilesparser --log_level=test_suite`、`./example_dir/example`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | github.com 直连下载超时 (Errno 110) | 本机对 github.com 域直连超时，官方 codeload 域可达 | 用官方 codeload.github.com 下载同一官方 tag tarball，SHA-256 核验通过 |
| 2 | 创建 worktree 全量检出失败 `No space left on device` | HMDFS 账户 inode 100% 耗尽（约 48.45M/48.46M，仅余约 5k，全量检出需 88.7k inode） | 用 `git worktree add --no-checkout` + sparse-checkout（cone 模式，仅检出 skill 工作流所需路径：scripts/references/templates/ci/.gitcode/knowledge/archives/c/coordgenlibs，约 4.7k 文件）创建唯一 worktree，git 元数据完整 |
| 3 | CMake 报 `Compatibility with CMake < 3.5 has been removed` | 本机 cmake 4.1.2 移除对 3.2 的兼容 | 配置参数 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` |
| 4 | 上游 `COORDGEN_RIGOROUS_BUILD=ON`（-Wall -Wextra -Werror）编译失败 | OHOS clang 对 boost 1.90 头文件报 -Wsign-compare（unsigned long vs int），测试源 coordgenBasicSMILES.h/test_coordgen.cpp 报 -Wunused-but-set-variable | 适配参数 `-DCOORDGEN_RIGOROUS_BUILD=OFF`（Werror 与 OHOS 工具链/boost 头文件不兼容，属平台适配项） |
| 5 | test_coordgen 运行时 `Error relocating ... symbol not found` | test 二进制 NEEDED 为相对路径 `../libcoordgen.so`，从 build-full 目录运行无法解析 | 从 build-full/test 目录运行（`cd build-full/test && ./test_coordgen`），并设置 LD_LIBRARY_PATH 指向 build-full 与依赖库 |

## 源码修改

无源码修改（未产生补丁；COORDGEN_RIGOROUS_BUILD 通过配方参数关闭）。

## 依赖版本

- maeparser 1.3.3（上游测试运行依赖，官方 codeload 下载源码本地构建）
- boost 1.90.0（本机 conan 缓存产物，libc++/cppstd17/clang15/OHOS armv8）
- zlib 1.3.1（conan 缓存，maeparser 依赖）

## 上游测试枚举与运行台账（双口径）

### 一、源码声明口径（source_declared_total）

按官方 tag 源码可复制枚举规则（grep `BOOST_AUTO_TEST_CASE`）发现的独立上游测试用例总数：

| 测试源文件 | 独立用例数 | 用例清单 |
|------------|-----------|----------|
| test/test_coordgen.cpp | 16 | SampleTest, TemplateTest, ClearWedgesTest, DisableMetalZOBs, terminalMetalZOBs, testMinimizedRingsShape, testPolyominoCoordinatesOfSubstituent, testPolyominoSameAs, testGetDoubleBondConstraints, testClockwiseOrderedSubstituents, testClockwiseOrderedNaN, testbicyclopentane, testFusedRings, testTemplates, testRingComplex, testCoordgenFragmenter |
| test/test_smilesparser.cpp | 4 | Basics, Rings, Branching, BondOrder |
| **合计（source_declared_total）** | **20** | |

非独立用例的框架/样例/数据文件（不计入独立用例，但列入台账）：
- example_dir/example.cpp — 样例可执行程序（非测试用例，ctest 注册为 example 测试项，实际运行验证库可用性）
- test/coordgenBasicSMILES.h — 测试辅助头文件（SMILES 数据容器，非用例）
- test/*.mae（test.mae, testChirality.mae, test_mol.mae, macrocycle.mae, metalZobs.mae, nonterminalMetalZobs.mae）— 测试数据 fixture，被 test_coordgen.cpp 通过 maeparser Reader 读取
- sketcherMaeReading.h — 测试辅助头文件
- cmake/CoordgenUtils.cmake, cmake/Findmaeparser.cmake — 构建辅助（maeparser 查找/下载），非测试

### 二、当前 OHOS 配置实例化口径（configured_executable_total）

| 构建目标 | ctest 注册名 | 实例化方式 |
|----------|-------------|-----------|
| example_dir/example | example | add_test(example ...)，CMake add_subdirectory(example_dir) |
| test/test_coordgen | test_coordgen | add_executable(test_coordgen ...) + add_test |
| test/test_smilesparser | test_smilesparser | add_executable(test_smilesparser ...) + add_test（注：上游 test/CMakeLists.txt 中 add_test 的 COMMAND 误写为 test_coordgen，两个 ctest 项实际都执行 test_coordgen 二进制；实际运行按源码对应目标分别执行） |

configured_executable_total = 3（example, test_coordgen, test_smilesparser），实际运行均成功。

### 三、执行结果

| 入口 | 命令 | cwd | exit_code | 结果 |
|------|------|-----|-----------|------|
| test_coordgen（16 用例） | ./test/test_coordgen --log_level=test_suite | build-full/test | 0 | *** No errors detected，16/16 通过 |
| test_smilesparser（4 用例） | ./test/test_smilesparser --log_level=test_suite | build-full/test | 0 | *** No errors detected，4/4 通过 |
| example（样例） | ./example | build-full/example_dir | 0 | 正常输出坐标 (-50, 0) (0, 0) |

### 四、统计口径

- source_declared_total = 20（test_coordgen 16 + test_smilesparser 4）
- configured_executable_total = 3（example, test_coordgen, test_smilesparser 独立可执行用例）
- executed_passed_total = 20（全部源码声明用例通过）
- 失败数 = 0
- 未运行/未实例化数 = 0
- 全量通过率 = 20/20 (100%)；当前配置可执行集合通过率 = 20/20 (100%)
- 无跳过、无硬阻塞、无依赖缺失导致的未运行入口。maeparser 1.3.3 与 boost 均已实际安装/构建并运行（最终回报前已复查 registry：maeparser/1.3.3 在 ohpcd 有已发布配方与 OHOS armv8 Release 二进制；本地测试实际复用缓存中已构建的 boost/1.90.0，registry 同时存在 boost/1.84.0 等已发布版本）。

## 验证结果

```bash
# 库本体
cmake --build build-lib -j2   # → libcoordgen.so
# 全量（含测试）
cmake --build build-full -j2  # → coordgen/example/test_coordgen/test_smilesparser
# 上游测试
LD_LIBRARY_PATH=<build-full>:<maeparser build>:<boost lib> ./test/test_coordgen --log_level=test_suite   # exit 0, 16/16
LD_LIBRARY_PATH=<...> ./test/test_smilesparser --log_level=test_suite   # exit 0, 4/4
./example                                                                    # exit 0
```
---

**编译结束**: 2026-09-25 16:50
**最终状态**: built
