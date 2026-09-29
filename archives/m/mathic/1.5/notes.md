# mathic 1.5 适配笔记

## 编译环境
- 构建系统: cmake（上游另有 autotools，本包只走 CMake）
- 编译日期: 2026-09-28
- 编译器: clang/clang++（OHOS aarch64，libc++，C++17）
- 状态: published

## 编译步骤

1. 源码：`https://github.com/Macaulay2/mathic/archive/refs/tags/v1.5.tar.gz`
   （官方 tag v1.5，SHA-256 `6bd2fd41d95efb0bf599aa5c6bc406f0d6fff803fccfe854db4835041c6267ee`，
   已二次下载比对一致；上游另有 autotools 构建系统，本包只走 CMake，先例 mathic/1.4）。
2. 配方（沿 mathic/1.4 已验证形态移植）：`generate()` 用 CMakeToolchain 钉
   `BUILD_TESTING=ON`、`enable_pqsim/enable_divsim=OFF`；预置
   `MEMTAILOR_INCLUDE_DIR`/`MEMTAILOR_LIBRARIES` 命中上游 `cmake/FindMemtailor.cmake`；
   CMakeDeps 生成 memtailor/gtest 配置。
3. `cmake.configure()` + `cmake.build(build_tool_args=["-j1"])` 编译 mathic 静态库并构建
   `mathic-unit-tests`（gtest 套件）。
4. `build()` 内在 build 根目录 `ctest -N`（取注册数）+ `ctest --output-on-failure`
   （逐行解析 Test #N ... Passed/Failed）全量实跑上游套件，输出 HMBS_UPSTREAM_TEST_RESULT
   并落盘 hmbs_upstream.json。
5. `package()`：`cmake.install()` 装出 include/mathic.h + include/mathic/*.h +
   lib/libmathic.a；附加 licenses/；拷贝 hmbs_upstream.json 到 res/ 供 test_package 复发。
6. test_package：直接编译 test_mathic.cpp（`-I<mathic include> -I<memtailor include>
   -L... -lmathic -lmemtailor -pthread`），运行 6 组消费者断言 + 复发上游标记。
7. test_ohos：`run_ohos_test.sh` 实跑鸿蒙专项验证（S1a aarch64 ELF / S1b 无宿主路径泄漏 /
   S2 编译运行 ohos_special_test：宽度对齐契约 + bionic 多线程确定性 + 版本契约），全过。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `if(GTEST_FOUND)` 恒假 → configure 期 FetchContent git clone googletest 超时 | find_package(GTest) 走 CONFIG 模式只设 `GTest_FOUND`；全大写 `GTEST_FOUND` 仅 MODULE 模式设置 | patch 0002：改 `GTest_FOUND OR GTEST_FOUND OR TARGET GTest::gtest` 以 target 存在性兜底 |
| 2 | `GTest::GTest`/`GTest::Main` target not found | 旧式别名仅 FindGTest.cmake 提供；Conan gtest/1.17.0.1 只声明 `GTest::gtest`/`gtest_main`/`gmock`/`gmock_main` | patch 0002：只链 `GTest::gtest`（testMain.cpp 自带 main，不链 gtest_main） |
| 3 | build 根目录 ctest 输出 `No tests were found!!!` 且退出码 0 | 上游 include(CTest) 写在 src/ 子目录，enable_testing() 只对 build/src/ 生效 | patch 0001：include(CTest) 提到顶层；build() 解析日志不只看退出码 |
| 4 | lib/libmathic.a、include/mathic.h 缺失 | install(TARGETS mathic LIBRARY ...) 只声明 LIBRARY（静态库属 ARCHIVE）；伞头只挂 PUBLIC_HEADER 属性无 DESTINATION | patch 0001：补 ARCHIVE DESTINATION lib 并 install(FILES src/mathic.h DESTINATION include) |
| 5 | find_package(Memtailor REQUIRED) 在 Conan 沙箱找不到包 | 上游 FindMemtailor 用 find_path/find_library 搜系统前缀 | generate() 预置 MEMTAILOR_INCLUDE_DIR/MEMTAILOR_LIBRARIES 缓存变量指向 memtailor 包目录 |
| 6 | 消费者 HashTable.h 报 memtailor.h: No such file | mathic 公开头直接包含 memtailor 伞头 | test_package 同时 -I<memtailor include> 并链接 -lmemtailor |
| 7 | 受限 worker `/bin/sh: Out of memory`（串行 -j1 后仍复现） | 模板+gtest 头的单进程 clang Release 编译峰值内存超限 | patch 0003：仅把非交付物 mathic-unit-tests 封顶到 -O1（后出现的 -O1 覆盖 Release -O3），交付库保持 Release |

## 源码修改

- patches/0001-CMakeLists.txt-toplevel-ctest-and-install-static.patch：
  两处打包/测试缺陷（同 mathic/1.4 先例，对 1.5 源码干净应用）。
- patches/0002-src-CMakeLists.txt-conan-gtest-targets.patch：
  GTest 探测与 target 名修正（同 1.4 先例）。
- patches/0003-test-O1-cap-compile-memory.patch：测试目标 -O1 内存封顶（同 1.4 先例）。

## 依赖版本

- memtailor/1.4（requires，运行时；ohpcd 已发布）
- gtest/1.17.0.1（test_requires，仅测试；ohpcd 已发布）

## 验证结果

- conan-verify：G0-G4 与 L2/L4/L5 全 PASS（reports/conan-verify-report.md）。
- W3 本地 CI：setup.sh + build_and_test.sh 通过（JC 仅命中其他库基线空文件，按基线隔离
  复验后通过；4 个 main 基线文件 pre/post SHA-256 均为 e3b0c44...，原样恢复未进 diff）。
- 上游测试：14 个 TEST 宏（BitTriangle 3 / DivFinder 1 / HashTable 2 / PairQueue 8，
  testMain.cpp 0）＝ ctest 注册 14 ＝ 实跑通过 14 → **14/14 = 100%**
  （reports/test-report.md，双口径一致）。
- 消费者：test_mathic.cpp 6 组断言全过（HMBS_TEST_PACKAGE_RESULT passed 6/6）。
- 鸿蒙专项：reports/ohos-special-run.log，S1a/S1b/S2 全过。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py / conandata.yml | Conan 2 配方（静态库 mathic/1.5） |
| patches/0001-0003 | 三个适配补丁 |
| test_package/ | 消费者 6 组断言 + MANIFEST |
| test_ohos/ | 鸿蒙专项测试（自包含脚本+源码） |
| reports/ | conan-verify-report / test-report / ohos-special-run / knowledge-ledger |

## 注意事项

- 知识路径：C1-C3（subdir ctest / install 漏装 / GTest target 名）与 memtailor-1.4 草稿
  完全重复 → reuse_existing；C4（-O1 封顶非交付测试目标）为已验证新增差异 →
  new_draft（knowledge/drafts/DRAFT-mathic-1.5-test-o1-cap-compile-memory.kv/.md，同 PR 交付）。
- 不触发/不需要 commands.json：mathic 是纯库（无 bin 产物），非 CLI（R38 库类型）。
- W3 期间按基线隔离规程临时移除的 4 个 main 基线空文件（cloog/kics/thc 的
  .build-closed/.staging-verified）已原样恢复，SHA-256 与隔离前一致，当前库 diff 不含它们。

---

**编译结束**: 2026-09-28
**最终状态**: published