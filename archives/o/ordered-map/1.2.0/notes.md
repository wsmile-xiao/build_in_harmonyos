# ordered-map 1.2.0 适配笔记

## 软件概况

- tsl::ordered_map / tsl::ordered_set：保持插入顺序的 C++11 哈希 map/set，header-only，MIT。
- 上游：<https://github.com/Tessil/ordered-map>，tag `v1.2.0`（带 v 前缀）。
- sha256：`3053e2d62db8a158c5941b75dacf397e1c695cd99dda4db78a32af76f4523423`（设备实测 sha256sum）。
- 无第三方运行时依赖（tests 除外，见下）。

## W0 依赖预检

- `ci/scripts/preflight_check.sh ordered-map/1.2.0`：无依赖声明，预检通过。
- header-only，`package_id` 清空，任何配置共享同一包。

## 上游测试与 Boost.Test 困境（本库核心适配点）

- 上游 `tests/CMakeLists.txt`：`find_package(Boost 1.54.0 REQUIRED COMPONENTS unit_test_framework)`，
  编译选项 `-Werror -Wall -Wextra -Wold-style-cast -DTSL_DEBUG -UNDEBUG`，`cxx_std_11`。
- ohpcd 制品仓 boost 二进制实测**均不含 unit_test_framework**：
  - boost/1.84.0：lib 下仅 filesystem/iostreams/program_options/regex（静态）；
  - boost/1.90.x：共享库构建同样没有 unit_test_framework。
  → 无法按上游方式链接执行 Boost.Test（也不允许 `--build=missing` 现编 boost）。
- 用例面（静态计数，grep 全宏面共 12 种）：
  - ordered_map_tests.cpp：57 BOOST_AUTO_TEST_CASE + 4 BOOST_AUTO_TEST_CASE_TEMPLATE
  - ordered_set_tests.cpp：4 + 1（模板各迭代 5 / 6 类型 `boost::mpl::list`）
  - custom_allocator_tests.cpp：1
  - 合计 **67 个用例定义**；CHECK_EQUAL 196、CHECK 166、REQUIRE 10、REQUIRE_NE 6、
    REQUIRE_EQUAL 4、CHECK_NE 2、CHECK_THROW 1（经 utils.h TSL_OH_CHECK_THROW）、BOOST_ASSERT 16。
- 仓库先例：archives/a/atomic_queue/1.9.2 同样因 Boost.Test 不可得而改用无 Boost 测试移植。

## 解决方案：零依赖 Boost.Test shim（上游测试源文件零修改）

- 上游测试只 include 两个 Boost 头：`<boost/test/unit_test.hpp>` 与 `<boost/mpl/list.hpp>`。
- 配方目录归档 `shim/`（随 export_sources 导出）：
  - `shim/boost/test/unit_test.hpp`：最小 Boost.Test 语义替身——
    CHECK/CHECK_EQUAL/CHECK_NE 非致命计数；REQUIRE/REQUIRE_EQUAL/REQUIRE_NE 抛
    `case_failure` 中止当前用例（其余用例继续）；CHECK_THROW try/catch；
    BOOST_ASSERT → assert（-UNDEBUG 下生效，与上游一致）；SUITE/SUITE_END/TEST_MODULE 空宏；
    AUTO_TEST_CASE 注册进全局 registry；CASE_TEMPLATE 用 thunk 类模板 + 递归
    `expand_seq<std::tuple<...>>` 按类型列表展开注册（纯 C++11，不用 index_sequence）。
  - `shim/boost/mpl/list.hpp`：`boost::mpl::list` = `std::tuple` 别名（纯编译期类型序列）。
  - `shim/shim_main.cpp`：替换上游 main.cpp（其仅 `#define BOOST_TEST_MODULE` +
    include，依赖编译型 Boost.Test 提供 main()），调 `run_all()` 返回失败数。
- 三个测试源文件与 utils.h **原封不动**编译（-I shim 在 include 路径最前）。
- 复刻上游语义选项：`-std=c++11 -DTSL_DEBUG -UNDEBUG`；`-Werror` 一族告警门禁不随 shim 复刻。

## 设备冒烟结果（2026-09-02 03:59，鸿蒙 PC 真机原生执行）

- 编译：clang++（hnp，aarch64-unknown-linux-ohos）一次通过，零告警零错误。
- 执行：**88/88 运行时用例全部通过，0 失败，183624 个断言**（67 定义 → 5 个模板用例按
  4×5 + 1×6 类型展开为 26 个运行时用例，62+26=88），RC=0。

## 配方要点

- `package_type = "header-library"`；package() 只装 `include/tsl/*.h` + LICENSE → licenses/。
- `build()`（run_upstream_tests=True 且 can_run 时）编译并真实执行上游套件，
  解析 shim summary（`test cases: N | N passed | N failed`），failed≠0 或 executed=0 抛
  ConanException；输出两行证据（套件 88/88 + 1/1 suites OK）。
- R32：validate 用 `in`；R33：编译器取自 `tools.build:compiler_executables`。
- conandata.yml：url 单元素列表（绕 CI 缺 curl）；patches 空（零补丁）。

## test_package（消费侧）

- 10 个 CHECK：插入序保持（front/nth）、find/at/erase、erase 与 rehash 后顺序、
  ordered_set insert/erase/count、1000 元素 map nth。失败返回非零。
- CMake 消费：`find_package(ordered-map REQUIRED)` + `ordered-map::ordered-map`
  （cmake_file_name/cmake_target_name 由 package_info 设定）。

## 已知限制

- shim 不复刻 Boost.Test 的数据驱动测试、fixture 依赖注入与告警门禁（-Werror）；
  本库上游测试未用到这些特性，宏面 12 种全覆盖。
- 移植口径：67/67 用例定义全部执行（测试修改=框架替换，测试体零修改）。

## 验证

```
conan create archives/o/ordered-map/1.2.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

**编译结束**: 2026-09-02 04:14 / **最终状态**: built
