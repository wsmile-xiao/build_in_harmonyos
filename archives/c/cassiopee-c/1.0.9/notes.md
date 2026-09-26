# cassiopee-c 1.0.9 适配笔记

## 编译环境
- 构建系统: cmake（上游 CMakeLists.txt，cmake_minimum_required 2.8 → 补丁提升 3.5 兼容 CMake 4.x）
- 编译日期: 2026-09-25
- 编译器: clang/clang++ 15.0.4 (aarch64-unknown-linux-ohos, OHOS SDK 26.0.0.18)
- Conan: 2.29.1 (OHOS 适配版), profile: ci/conan/profiles/ohos-aarch64
- 状态: built

## 编译步骤

```bash
# 依赖安装（制品仓 ohpcd 已发布）
conan install --requires=boost/1.90.0.4.1 --requires=glog/0.7.1 --requires=cppunit/1.15.1 \
  -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --output-folder=build -g CMakeToolchain -g CMakeDeps

# configure（上游 cmake_minimum_required 2.8 与 CMake 4.x 不兼容 → 补丁提升为 3.5）
cmake .. -DCMAKE_TOOLCHAIN_FILE=conan_toolchain.cmake -DCMAKE_BUILD_TYPE=Release

# build
make -j2

# 产物
#   lib/libcassie.so （共享库，VERSION 1.0.0 SOVERSION 1）
#   bin/cassiopee    （CLI：索引/搜索，R38 → commands.json 需在软件级目录声明）
#   bin/cassiopeeknife（CLI：FASTA → cassiopee 输入转换）
#   include/Cassiopee.h + CassiopeeConfig.h + tree/tree.hh + tree/tree_util.hh
```

`conan create`（G2 干净构建）实测通过；test_package 消费者用例（consumer_test.cxx）编译链接运行均通过。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake Error: Compatibility with CMake < 3.5 has been removed | 上游 `cmake_minimum_required(VERSION 2.8)` 与 CMake 4.x 不兼容 | 补丁 0001：提升为 3.5 |
| 2 | `'glog/logging.h' file not found` + `unknown type name 'GLOG_EXPORT'` | 上游 src/CMakeLists.txt 用裸目标名 `glog` 链接且未 find_package；glog 0.7.x 需 `GLOG_USE_GLOG_EXPORT` | conanfile generate() 注入 `-DGLOG_USE_GLOG_EXPORT` 与依赖 include/lib 路径（依赖注入，非补丁） |
| 3 | `cannot define or redeclare 'string' ... fLS namespace` | glog 0.7.x flags.h 的 `DECLARE_string` 宏需先包含 <string>（C++17 下） | 补丁 0002/0003：cassie.cxx、cassiopee.cxx 在 `<glog/logging.h>` 前加 `#include <string>` |
| 4 | `undefined reference: boost::archive::...` 链接失败 | cassiopee-c 使用 boost serialization/iostreams 编译组件；boost/1.90.0 静态包缺 serialization 库 | 依赖改用 boost/1.90.0.4.1（含 libboost_serialization.so/libboost_iostreams.so），链接注入 `-lboost_serialization -lboost_iostreams` |
| 5 | 消费者编译 `boost/archive/text_oarchive.hpp` not found（conan-verify G2 test_package） | Cassiopee.h 公开头直接包含 boost 头；boost 作为传递依赖时 CMakeDeps 不导出 include 目录 | test_package 显式 requires boost/1.90.0.4.1（adql 同款先例） |
| 6 | ctest 运行时 `Error relocating ... symbol not found` | 测试二进制 DT_NEEDED 为相对路径 `../lib/libcassie.so`，从源码根运行无法解析 | 按运行时环境恢复：在源码根 `lib/` 建立指向 build/lib 的符号链接 + LD_LIBRARY_PATH 注入依赖库路径 |
| 7 | 上游 test.py 运行 FileNotFoundError: '../bin/cassiopee' | 上游脚本假设二进制在源码根 `bin/`，实际在 build/bin | 建立 `bin/` 符号链接满足上游路径假设（不修改上游脚本） |
| 8 | /tmp 只读（平台限制） | HMDFS 下 /tmp 不可写 | 使用 $TMPDIR=$HOME/tmp（环境已配置） |

## 源码修改（补丁）

- `patches/0001-CMakeLists.txt.patch`：cmake_minimum_required 2.8 → 3.5
- `patches/0002-src-cassie.cxx.patch`：`#include <string>`（glog 前）
- `patches/0003-src-cassiopee.cxx.patch`：`#include <string>`（glog 前）

## 依赖版本

| 依赖 | 版本 | 用途 |
|------|------|------|
| boost | 1.90.0.4.1 | serialization/iostreams（索引序列化、保存/加载） |
| glog | 0.7.1 | 日志 |
| cppunit | 1.15.1 | 上游测试链接 |
| gflags | 2.2.2 | glog 传递依赖 |

## 验证结果（上游测试完整枚举台账 + 双口径统计）

### 上游测试源枚举（R51 完整台账）

| 测试源 | 类型 | 是否独立上游用例 | 说明 |
|--------|------|------------------|------|
| test/test.h | 用户测试框架头 | 否（框架头/声明） | CPPUNIT_TEST_SUITE 套件声明 |
| test/test.cxx | 用户测试源（cppunit） | 是（13 个独立 TEST_CASE） | 见下方用例清单 |
| test/test.py | 用户测试脚本 | 是（1 个独立脚本用例） | CLI 全子串/全位置穷举搜索（r 还原模式）+ 输出比对 |
| test/pattern.txt | 测试数据 fixture | 否（fixture 数据） | 搜索模式数据 |
| test/protein.txt | 测试数据 fixture | 否（fixture 数据） | 蛋白序列样例 |
| test/sequence.txt | 测试数据 fixture | 否（fixture 数据） | 输入序列样例 |
| test/test.txt | 测试数据 fixture | 否（fixture 数据） | 输出/期望数据 |
| test2.fasta.cass | 测试数据 fixture | 否（fixture 数据） | test.py 输入序列（cass 格式） |
| test/CMakeLists.txt | 构建目标声明 | 否（构建注册） | add_executable(test_cassiopee) + add_test(TestCassie) |
| build/bin/test_cassiopee | 构建目标/可执行 | —（构建产物） | ctest 注册 TestCassie，内含 13 个 cppunit 用例 |

### 独立上游用例清单（13 个 cppunit TEST_CASE）

testIndex / testIndexWithReduction / testSearchInReduction / testAmbiguity /
testSearchWithError / testSearchAfterN / testSearchWithN / testReducedSearchAfterN /
testReducedSearchWithN / testProtein / testLoadSave / testMultiIndex / testSearchWithMorphism

### 双口径统计

- `source_declared_total`（源码声明测试总数）: **14** = 13 个 cppunit TEST_CASE + 1 个 test.py 独立脚本用例
- `configured_executable_total`（当前 OHOS 配置实际实例化/注册的独立可执行用例数）: **2** = test_cassiopee（ctest 注册 TestCassie，内含 13 用例）+ test.py（可直接运行）
- `executed_passed_total`（通过数）: **14**（cppunit OK (13) 全过 + test.py exit 0 全过）
- `executed_passed_total / source_declared_total` = **14/14 (100%)**
- `executed_passed_total / configured_executable_total` = **14/14 (100%)**

未运行/未实例化：0 项。互斥编译分支、条件宏、禁用条件：无。

### 实际运行命令与日志（cwd、退出码、SHA-256）

| 入口 | 命令 | cwd | 退出码 | 日志 | SHA-256 |
|------|------|-----|--------|------|---------|
| ctest | `ctest --output-on-failure` | build/ | 0（1/1 Passed, TestCassie） | $TMPDIR/cassiopee-c-1.0.9-testlogs/ctest-run.log | fc49445675845f1314c21c834698b59776804d6d1033ac706f0fb85b0916a01e |
| test_cassiopee（直接） | `./build/bin/test_cassiopee` | work 根 | 0（OK (13)） | $TMPDIR/cassiopee-c-1.0.9-testlogs/test_cassiopee-direct.log | 5430d5f1d879b8cfd20dd81d449829f602d0e41c84955efccb6983cbad39562e |
| test.py | `python3 test.py` | test/ | 0（全子串搜索全部命中，无 Not found） | $TMPDIR/cassiopee-c-1.0.9-testlogs/test-py-run.log | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |

> 运行时环境恢复说明：test_cassiopee 与 CLI 二进制 DT_NEEDED 含相对路径 `../lib/libcassie.so`，须在源码根 `lib/` 提供符号链接指向 build/lib/libcassie.so，并设置 LD_LIBRARY_PATH 注入 boost/glog/gflags/cppunit 库目录（测试实际探测路径已记录，属于当前库构建布局导致，非修改上游测试）。

### HarmonyOS 专项测试（独立于上游测试与消费者用例）

源码：`tests/harmonyos_test.cxx`（归档内独立测试源，3 个专项用例）：
1. **case1 序列化往返**：构造 CassieIndexer → index() → save()（写出 .cass.idx/.cass.meta）→ 重新构造后 index() 自动走 load 路径（index_loaded_from_file() == true）——验证 boost serialization 适配点在 OHOS 平台真实可用；
2. **case2 还原模式搜索**：reduction 建树 + search("ACGT") + removeDuplicates + sort，验证公开 API 命中 6 个位置（可观察结果）；
3. **case3 公开 API 可用性**：通过安装产物 libcassie.so 使用公开头文件与 API 完成索引+搜索。

编译命令（cwd=归档版本目录，链接安装产物 p/include + p/lib）：
```bash
aarch64-unknown-linux-ohos-clang++ -std=c++17 -DGLOG_USE_GLOG_EXPORT \
  -I<pkg>/include -I<boost>/include -I<glog>/include tests/harmonyos_test.cxx \
  -L<pkg>/lib -L<boost>/lib -L<glog>/lib -L<gflags>/lib -L<cppunit>/lib \
  -lcassie -lboost_serialization -lboost_iostreams -lglog -o harmonyos_test
```
运行（cwd=$LOGDIR）：`LD_LIBRARY_PATH=<pkg/lib>:<boost/lib>:<glog/lib>:<gflags/lib>:<cppunit/lib> ./harmonyos_test`
- 退出码：0；输出：`case1 OK: serialization round-trip (save -> auto load)` / `case2 OK: reduction search matched 6 positions` / `case3 OK: public API usable via installed libcassie.so` / `HarmonyOS specific test PASSED (3 cases)`
- 日志：`$TMPDIR/cassiopee-c-1.0.9-testlogs/harmonyos_test-run.log`，SHA-256 = d0092e8cc6e71fd40b22d1b6ef56a406fe81abab04c6a383dba8be5956af49f4
- 产物：`harmonyos_test`（ELF 64-bit arm64，动态链接 ld-musl-aarch64）

### 消费者验证用例（test_package）

- 源码：`test_package/consumer_test.cxx`（仅通过公开头文件 Cassiopee.h + 公开 API CassieIndexer/CassieSearch 使用 libcassie.so：索引构建、搜索、matches 列表、序列化保存与重载）；
- 验证方式：`conan create`（G2 门禁）中 test_package 实际编译、链接、运行该消费者二进制并通过（退出码 0）；
- 调用公开 API：CassieIndexer::index / save / index_loaded_from_file，CassieSearch::search / sort，`search.matches.size()`（可观察结果）。
- 与上游测试、鸿蒙专项测试分别计数，不重复充数。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake 版配方（依赖注入 + commands.json 对应 CLI） |
| conandata.yml | 官方 GitHub archive URL + sha256 cdd022ff…06c4 |
| test_package/ | 消费者用例 consumer_test.cxx（真实 API 调用） |
| patches/0001-0003 | cmake 版本兼容 + glog <string> 包含顺序 |
| commands.json | 软件级目录声明（cassiopee/cassiopeeknife CLI，R38） |

## 注意事项

- 上游 CMakeLists 直接以裸目标名链接依赖（glog/bash），依赖 include/lib 经 conanfile generate() 注入，属本配方私有注入（私有 prefix 语义），不污染共享系统目录。
- boost 必须用 1.90.0.4.1：含 serialization/iostreams 编译库且 CMakeDeps 正确导出 include；1.90.0.3 的 CMakeDeps include 为空会导致消费者编译失败。
- CLI 工具（cassiopee/cassiopeeknife）R38 需 commands.json，已在软件级目录声明并随 PR 交付；CI L0k 校验。
- 测试运行依赖源码根 lib/ 符号链接（上游相对 DT_NEEDED 布局），本地/CI 复跑需按此设置或由测试环境注入。
---

**编译结束**: 2026-09-25 07:44
**最终状态**: built
