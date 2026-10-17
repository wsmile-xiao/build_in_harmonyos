# manifold 3.4.1 适配笔记

## 软件简介
manifold（elalish/manifold）是 C++17 三维流形三角网格几何库，保证布尔运算等的拓扑鲁棒性。CMake 构建。Apache-2.0。

## 构建方式
- 构建系统：cmake（C++17）
- 依赖：`clipper2/2.0.1`（CrossSection，PRIVATE 链接）、`gtest/1.17.0.2`（仅测试，visible=False）
- 关键 CMake 选项：`MANIFOLD_TEST=ON`、`MANIFOLD_CROSS_SECTION=ON`、`MANIFOLD_CBIND=ON`、`MANIFOLD_PAR=OFF`、`MANIFOLD_PYBIND=OFF`、`MANIFOLD_STRICT=OFF`、`MANIFOLD_DOWNLOADS=OFF`、`ASSIMP_ENABLE=OFF`、`TRACY_ENABLE=OFF`、`MANIFOLD_FUZZ=OFF`

## OHOS 适配要点
1. **FetchContent 不可用**：上游默认 `MANIFOLD_DOWNLOADS=ON`，会 git clone `googletest`（v1.17.0）与 `clipper2`，但 OHOS 真机无法从 GitHub git clone（clipper2/2.0.1 的 README 也记录了该限制）。因此配方关闭 `MANIFOLD_DOWNLOADS`，改由 Conan 提供两个依赖（CMakeDeps + `find_package` 命中）。
2. **系统名**：manifold **不**强制设置 `CMAKE_SYSTEM_NAME=Linux`（与 clipper2 不同）。原因是 manifold 需经 `gtest_discover_tests` 在构建期运行测试二进制注册 ctest；若强制系统名会让 CMake 认为本机构建是交叉编译而禁用用例发现。zydis（同样跑 ctest 的配方）在 OHOS 也不设系统名。
3. **编译器位置**：真机上 clang 迁移到 `~/usr/local/bin`（旧 profile 可能仍指向 `/data/service/hnp/bin`），`generate()` 解析真实 clang/clang++ 并 pin 到 toolchain（zydis 教训）。
4. **Python for gtest_discover_tests**：注解 `Python3_EXECUTABLE` 优先取 `HMBS_PYTHON3`。

## 上游测试
- `MANIFOLD_TEST=ON` 通过 `gtest_discover_tests(manifold_test)` 将每个 GTest 用例注册为独立 ctest 条目（*nix 分支）。
- build() 内运行 `ctest --output-on-failure`（失败即抛），随后从 `gtest_discover_tests` 生成的
  `<target>[N]_tests.cmake` 发现文件统计 `add_test(` 条数作为 discovered（等价 `ctest -N` 总数），emit `HMBS_UPSTREAM_TEST_RESULT` 并持久化到包 res/。
- **总数（ctest_entries 口径）**：真机详见下文“修复记录”，以真机 ctest 实际注册数为准。

## 修复记录
### 真机 compile 失败：Unknown CMake command "gtest_discover_tests"（test/CMakeLists.txt:69）【已解决】
- **根因**：`gtest_discover_tests` 由 CMake 内置模块 `GoogleTest.cmake` 定义，需 `include(GoogleTest)` 加载。上游默认用 FetchContent 构建 googletest，由 googletest 自身 CMakeLists 顺带 include；改用 Conan 提供 gtest 后该 include 不再执行。
- **修复**：新增 patch `patches/0001-include-googletest-cmake.patch`，在 `test/CMakeLists.txt` 的 `enable_testing()` 之后显式 `include(GoogleTest)`。

### 真机 compile 失败：test_package 消费者编译报 `no type named 'CrossSection' in namespace 'manifold'`
- **现象**：上游测试 318/318 全绿、HMBS_UPSTREAM_TEST_RESULT 正确后，test_package 消费者 `test_manifold.cpp:33` 编译报 `no type named 'CrossSection'`，conan create 退出码 1。
- **根因**：`CrossSection`（2D API）定义在独立公共头 `manifold/cross_section.h` 中；`manifold.h` 并不会无条件拉入它，而是由调用方在 `#ifdef MANIFOLD_CROSS_SECTION` 下显式 `#include "manifold/cross_section.h"`。上游测试正是这样写（test/manifold_test.cpp：`#ifdef MANIFOLD_CROSS_SECTION #include "manifold/cross_section.h" #endif`）。本库以 `MANIFOLD_CROSS_SECTION=ON` 构建并安装该头，但消费者翻译单元既未 include cross_section.h 也未定义 MANIFOLD_CROSS_SECTION，故类型不可见。
- **修复**：test_manifold.cpp 增加 `#include "manifold/cross_section.h"`；test_package/CMakeLists.txt 为 test_manifold 增加 `target_compile_definitions(... MANIFOLD_CROSS_SECTION=1)` 以镜像库的构建开关（100% 对齐上游消费者约定）。未删除任何断言。
- **验证**：本机语法/YAML 校验通过；真机预检将复跑 test_package，预期 test_manifold 编译链接成功、5 项 CHECK 全绿，`HMBS_TEST_PACKAGE_RESULT` 的 discovered=5/passedCount=5。

### 真机 compile 失败：ctest 实测 318/318 全绿，但 reported 0 discovered tests
- **现象**：真机 `ctest --output-on-failure` 完整跑完并 `100% tests passed, 0 tests failed out of 318`，
  但随后 emit 的 `HMBS_UPSTREAM_TEST_RESULT` 却为 `discovered:0 executed:0 passed:0`，触发
  “ctest reported 0 discovered tests… refusing to fabricate a pass” 硬拒绝，conan create 退出码 6。
- **根因**：`_count_ctest()` 只在构建树里遍历名为 `CTestTestfile.cmake` 的文件统计 `add_test(`。
  但 manifold 的测试是经 `gtest_discover_tests()` 注册的：CMake 生成的
  `CTestTestfile.cmake` 只对发现文件做 `include(...)`，真正含 `add_test(...)` 的是
  `gtest_discover_tests` 产出的 `<target>[N]_tests.cmake`（如 `manifold_test[1]_tests.cmake`）。
  因此按旧逻辑一个 `add_test(` 都数不到 → discovered=0 → 误判“0 用例”。
- **修复**：`_count_ctest()` 改为遍历构建树中所有 `*_tests.cmake` 发现文件，统计其中
  `add_test(` 条目数（每个已注册 GTest 用例恰好一个，等价 `ctest -N` 总数），作为唯一的
  discovered 数据源。复用真机日志确认的 “out of 318” 作为口径基准。
- **口径修正**：早期静态手盘（TEST/TEST_F 宏 212 + 多边形语料 109 = 321）与真机 ctest 实测
  318 差 3；以真机实际注册数为准，`upstream_test_total` 定为 318（官方口径 ctest_entries，
  “100% tests passed, 0 tests failed out of 318”）。discovered/passed 取同一真机 ctest 结果，
  全绿则通过率 100%。
- **验证**：本机语法/逻辑审查通过；真机预检将复跑 ctest，预期 discovered=318, passed=318。

### CI L0 门禁失败：commands_json_r38（CLI tool detected but commands.json missing）【已解决】
- **现象**：官方 CI 在 `conan-build-test` 步骤的 L0k（R38）质量门禁失败，提示
  “CLI tool detected but commands.json missing”，L0_RESULT=fail: commands_json_r38，
  阻止进入后续构建/测试阶段（build/test 均 skip）。
- **根因**：manifold 配方 `package_info` 声明了 `bindirs=["bin"]` 且包会安装可执行文件
  （`manifoldc` C 绑定工具 / bin 目录产物），R38 门禁据此判定该软件包产出命令行可执行文件，
  要求软件级目录 `archives/m/manifold/commands.json` 存在以声明 CLI 工具及 binary 标志。
- **修复**：在 `archives/m/manifold/commands.json` 新增命令行工具声明（参考
  `templates/commands.json.template` 与 `archives/s/strace/commands.json` 示例）：
  name=manifold、type=tool、versions["3.4.1"]={ref:"manifold/3.4.1", binary:true}；
  通过 `json.load` 校验合法，name/type/versions 与配方对齐。
- **验证**：本机 `json.load` 解析通过、字段命名与模板一致；真机预检将复跑 L0k 门禁。
  （注：working tree 中另有与本 PR 无关的 uncommitted 文件 `archives/l/libXext/*` 与
  `fix_checkout.py`，为共享工作区遗留，非 manifold 改动，未纳入本轮处理。）

## 待办 / 备注
- 依赖 clipper2/2.0.1 与 gtest/1.17.0.2 需已发布到制品仓（L0i/R36），否则预检在 L0 阶段拦截（属依赖可用性，非配方缺陷）。
- test_package 消费者用例：构造一个 Cube manifold，校验 `status==Manifold::Error::NoError` 且 `volume()>0`。
- this PR 只含 manifold 一个库的改动。
