# mathicgb 1.4 — HarmonyOS PC 适配笔记

## 1. 概览

| 项 | 值 |
|----|----|
| 上游 | https://github.com/Macaulay2/mathicgb |
| 版本 | 1.4（git tag `v1.4`） |
| 源码 | `https://github.com/Macaulay2/mathicgb/archive/refs/tags/v1.4.tar.gz` |
| SHA256 | `c2d29521e26fa6024c1be85c5f8273324e2e3bed874327c0b07652986a7ede89`（714761 字节，2026-09-24 实测下载计算） |
| 构建 | CMake ≥ 3.12（上游另有 autotools 构建，本包只走 CMake） |
| 包类型 | static-library（另随包发布 `mgb` 命令行工具） |
| 依赖 | `memtailor/1.4`（requires，已发布）＋ `mathic/1.4`（requires，见 §2 W0 说明）＋ `gtest/1.17.0.1`（build_requires，仅测试） |
| 状态 | 首轮工作树（未提交）；真机 rule4 预检待 HMBS 后台执行，数字以预检日志为准 |

mathicgb 基于 mathic 的快速数据结构计算（signature）Gröbner 基，是
Macaulay2 生态的 C++ 计算内核之一（memtailor → mathic → mathicgb 依赖链的
最上层）。C++17。产物为静态库 `libmathicgb.a`（伞头文件 `mathicgb.h` ＋
`mathicgb/` 头目录树）与 `mgb` 可执行文件。

## 2. W0 — 依赖发布检查（首轮结论）

| 依赖 | ohpcd 制品仓状态 | 说明 |
|------|------------------|------|
| memtailor/1.4 | 本仓已有归档（`archives/m/memtailor/1.4`） | 与 mathicgb 1.4 同日发布的配套版本 |
| mathic/1.4 | **本仓暂缺**（`archives/m/` 下无 mathic 目录，全仓 grep 无命中） | 上游 https://github.com/Macaulay2/mathic 有 `v1.4` tag（与 mathicgb 1.4 同一批次） |
| gtest/1.17.0.1 | memtailor 1.4 已用其做 test_requires | 同口径复用 |
| TBB | 本包 `with_tbb=OFF`，不需要 | 确定性单线程构建 |

按 W0/R36 的拓扑序要求（memtailor → mathic → mathicgb），**mathic 需先
独立适配发布**，本包的 `requires("mathic/1.4")` 才能在 CI 的 PF4/R36 门禁
通过。首轮工作树如实声明该依赖，不做 vendor、不降级；若 HMBS 真机预检报
`dependency_missing(mathic)`，属预期内分支：请先派发 mathic/1.4 适配任务，
本包在 mathic 发布后直接重跑预检即可（配方本身无需改动）。
  （更新：首轮真机预检已确认 mathic 缺失导致图解析失败，见 §9；
  本包已按聚合经验 #1 改为配方内私有静态合包，不再要求 mathic 先独立发布。）

## 3. 三个上游缺陷（本包用两个 patch 修掉，同 memtailor 1.4）

### 3.1 `GTEST_FOUND` 恒假 → configure 期去 GitHub 拉 googletest（patch 0002）

上游 `src/CMakeLists.txt`（v1.4 tag 实测原文）：

```cmake
  if(NOT GTEST_FOUND)
    find_package(GTest)
  endif()
  include(GoogleTest)
  gtest_discover_tests(mathicgb-unit-tests TEST_PREFIX unit-tests:)

  if(GTEST_FOUND)
    target_link_libraries(mathicgb-unit-tests mathicgb GTest::GTest GTest::Main)
  else()
    include(FetchContent)
    FetchContent_Declare(googletest
      GIT_REPOSITORY https://github.com/google/googletest.git
      GIT_TAG        v1.16.0)
```

两个独立缺陷，必须一起修（同 memtailor §2.1）：

**(a)** `GTEST_FOUND` 全大写只由 CMake 自带 `FindGTest.cmake`（MODULE 模式）
设置；本包经 CMakeDeps 以 CONFIG 模式命中，只设置 `GTest_FOUND` → 条件恒
假 → configure 期 `FetchContent_MakeAvailable(googletest)` git clone，
CI worker 不可联网直接失败。

**(b)** `GTest::GTest` / `GTest::Main` 是 MODULE 模式旧别名；Conan 的
`gtest/1.17.0.1` 只声明 `GTest::gtest` / `GTest::gtest_main` 等。patch 改为：

```cmake
if(GTest_FOUND OR GTEST_FOUND OR TARGET GTest::gtest)
  target_link_libraries(mathicgb-unit-tests mathicgb GTest::gtest)
```

只链 `GTest::gtest`（`src/test/testMain.cpp` 自带 `main()`，不链 gtest_main）。

### 3.2 `ctest` 在 build 根目录「零执行却全绿」（patch 0001a）

上游 `include(CTest)` 只在 `src/CMakeLists.txt`（子目录）里，顶层
`CMakeLists.txt`（v1.4 全文 2241 字节，已通读）没有。`enable_testing()`
只对调用目录及其子目录生成 `CTestTestfile.cmake`，build 根目录跑 `ctest`
得 `No tests were found!!!` 且**退出码 0**。patch 把 `include(CTest)` 提到
顶层；`build()` 里仍同时解析 `ctest -N` 的 `Total Tests` 行与汇总行，不只
看退出码。

### 3.3 静态库与伞头文件都没被安装（patch 0001b）

上游顶层（v1.4 原文）：

```cmake
set_target_properties(mathicgb PROPERTIES PUBLIC_HEADER src/mathicgb.h)
install(TARGETS mathicgb LIBRARY DESTINATION lib)
```

只声明 LIBRARY → 静态库（ARCHIVE）不安装；`mathicgb.h` 无
`PUBLIC_HEADER DESTINATION` → 不安装。patch 补齐三类目的地；
`src/mathicgb/` 头目录树上游本来就装（`install(DIRECTORY ...)`），不动。

### 3.4 无需补丁的两处（已验证）

- **FindMathic/FindMemtailor**：上游自带 MODULE（`find_path`/`find_library`），
  随 CMakeToolchain 的 `CMAKE_PREFIX_PATH` 能命中 Conan 包，无需改写。
- **TBB**：`with_tbb=OFF` 直接绕开 `FindTBB`（v1.4 顶层是旧式
  `option(with_tbb auto)`，OFF 即单线程 `MATHICGB_NO_TBB` 分支）。

## 4. 上游测试：237 个 CTest 用例（ctest_entries 口径），无门控，全量实跑

v1.4 tarball `src/test/` 实测：约 101 个普通 TEST/TEST_F 宏（行首计数）＋
`src/test/MonoMonoid.cpp` 的 13 个 TYPED_TEST × 11 种 MonoidTypes：

| 文件 | 普通 TEST 宏 | 备注 |
|------|---------|------|
| F4MatrixBuilder.cpp | 5 | |
| F4MatrixReducer.cpp | 1 | |
| MathicIO.cpp | 8 | |
| MonoMonoid.cpp | 0 普通 + 13 TYPED_TEST | VarCount/MonoVector/MonoArena/ReadWriteMonoid/MonoPool/setExponentAndComponent/MultiplyDivide/LcmColon/Order/RelativelyPrime/SetExponents/HasAmpleCapacityTotalDegree/CopyEqualConversion × 11 种类型 ≈ 143 CTest |
| PrimeField.cpp | 10 | |
| QuadMatrixBuilder.cpp | 5 | |
| Range.cpp | 9 | |
| Scanner.cpp | 10 | |
| SparseMatrix.cpp | 3 | |
| gb-test.cpp | 12 | |
| ideals.cpp / ideals.hpp | 0（fixture helper） | |
| mathicgb.cpp | 11 | |
| poly-test.cpp | 27 | |
| testMain.cpp | 0（main 入口） | |
| **普通宏合计** | **101** | |

经 `gtest_discover_tests(... TEST_PREFIX unit-tests:)` 在 gtest/1.17.0.1 下展开为
237 个 CTest 用例（口径 `ctest_entries`；真机 2026-09-24 实测 `ctest -N`：
Total Tests: 237，执行 237、通过 237）。首轮误将口径记为 `gtest_macros`/101，
漏计 TYPED_TEST 展开，本轮已按真机注册数修正为 237。
`build()` 内 `ctest --output-on-failure` 全量实跑并输出
`HMBS_UPSTREAM_TEST_RESULT`（discovered 取自 `ctest -N`，其余取自汇总行），
同时落盘 `upstream/upstream_test_result.json` 并随包发布到 `res/`，
test_package 在消费测试中重发表（耐受 conan 构建缓存命中）。

## 5. 消费者测试（test_package）6 个用例

`test_mathicgb.cpp` 5 组（退出码 2..6 区分）＋ `mgb version` CLI 烟雾：

| 组 | 退出码 | 判据 |
|----|--------|------|
| 1 | 2 | `libmathicgbIsPresent()` 可链接 ＋ `MATHICGB_VERSION_STRING == "1.4"` ＋ `GroebnerConfiguration(101,3,1)` 存取/拷贝/四种 baseOrder 命名 |
| 2 | 3 | 真实计算 `computeGroebnerBasis({x^2-y, x^3-z})`（经 mathic＋memtailor）：输出多项式数 ≥ 2、总项数 ≥ 3、每式非空 |
| 3 | 4 | 单项式序契约：默认 (1,1,1)-revlex、空 grading 的 revlex 被拒绝（非全局序）、各选项 round-trip |
| 4 | 5 | `IdealStreamLog<CountingStream>` 包装真实计算（日志非空）＋ `logTime`/`logNumber` 烟雾（按文档返回值可为 false 不崩溃即可） |
| 5 | 6 | 重复运行逐位一致（确定性；单线程构建下必须成立） |
| 6 | — | `mgb version`（VersionAction 子命令，1.2 新增）打印版本，验证可执行产物可启动 |

## 6. 随包内容（预期）

- `include/mathicgb.h` ＋ `include/mathicgb/*.h{,pp}` 头目录树
- `lib/libmathicgb.a`
- `bin/mgb`（Groebner 基命令行工具：GB/SigGB/Matrix/Help/Version 五个动作）
- `licenses/gpl-2.0.txt`、`licenses/gpl-3.0.txt`

## 7. 本地预验证（首轮）

- 上游 tarball 下载＋SHA256 计算＋TEST 宏审计：在本机 Python 完成
 （见 §1 表格；不涉及编译，未在本机运行 conan）。
- 真机编译与测试：待 HMBS 后台预检（conan create 全量：101 上游用例 ＋
  6 消费者用例），结果回填至 PR 正文与本笔记 §8。

## 8. 真机预检记录

- 预检时间：2026-09-24（第二轮聚焦修复前）
- 上游测试：发现 237、执行 237、通过 237（`ctest --output-on-failure`；`HMBS_UPSTREAM_TEST_RESULT` 已在 build() 输出，但总数与 MANIFEST 声明的 101 不一致 → rule4 incomplete；根因为漏计 TYPED_TEST 展开，本轮已修正口径为 ctest_entries/237）
- 新增测试：`HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"./test_mathicgb && mgb version","discovered":6,"passedCount":0}`——`./test_mathicgb` 5 组通过后 `mgb version` 报 `/bin/sh: mgb: inaccessible or not found`（ConanException Error 127）；根因为 static-library 包的 bindirs PATH 注入不可靠，本轮改走包内绝对路径 `<package>/bin/mgb version`，并补齐上游结果落盘随包发布 + 消费测试重发表（经验 #1）。

## 9. 真机预检第一轮失败处理（mathic 远端缺失）

- 失败证据（HMBS preflight 2026-09-24）：`ERROR: Package 'mathic/1.4' not resolved:
  Unable to find 'mathic/1.4' in remotes. Required by 'mathicgb/1.4'`，卡在
  dependency graph 解析阶段，主源码未下载、主构建未运行。
- 根因：mathic 在 ohpcd 制品仓确实不存在且短期无独立适配，
  配方对其的直接引用无法解析；同时 mathicgb 上游用 MODULE
  FindMathic/FindMemtailor（find_path/find_library），需明确的头/库路径才能命中。
- 方案（聚合经验 #1：远端缺失依赖时配方内私有构建并合包）：
  conandata 新增 `vendor.mathic` 官方 v1.4 源码条目（校验值不变，
  gh-proxy 镜像在前、官方 URL 回退在后）；source 仅下载主源码，
  被依赖源码在 source 阶段 vendoring 到 `vendor/mathic-1.4`，
  build 内先用 Conan 工具链静态构建到 `build/vendor-install`
  私有 prefix（BUILD_TESTING=OFF，指向 Conan memtailor 包，
  同时修掉 mathic 上游同样的 `install(TARGETS mathic LIBRARY ...)` 静态安装漏装）；
  generate 保持不变，build 后续以 `MATHIC_INCLUDE_DIR/MATHIC_LIBRARIES/
  MEMTAILOR_INCLUDE_DIR/MEMTAILOR_LIBRARIES` 显式固定主构建的 MODULE 查找；
  package 合并头文件与 `libmathic.a` 并附带 lgpl 许可，
  package_info 捷绑 `["mathicgb", "mathic"]`；移除 test_package 对外部缺失包的
  直接引用，保留可运行的消费者验证（链接依然是
  `-lmathicgb -lmathic -lmemtailor`，但 mathic 头/库均取自本包）。
- mathic 官方 v1.4：108294 字节，sha256
  `6af7df540751de13456ba6c21bf8d06f84d4c43cd2c8c2695ba4b820e2d72883`；
  构建仅需 memtailor + Threads，无 TBB/GTest 运行依赖；设计上无已知边界。

## 10. 注意事项

- Windows 工作树说明：本机检出时上游 `archives/g/gama` 含 CR 字符文件名
  （Windows 非法）与 `archives/l/libXext`/`libxext` 大小写冲突，本地以
  sparse-checkout 排除 gama、assume-unchanged 屏蔽大小写冲突文件的伪差异；
  Linux 真机/CI 不受影响，HMBS 若见 `libXext` 相关差异请忽略（非本包改动）。
- `mgb` 的版本动作是子命令 `mgb version`，不是 `--version`。
- 本包 `package_type` 为 static-library 但同时发布 `bin/mgb`，故配套软件级
  `commands.json`（R38）声明该工具。
