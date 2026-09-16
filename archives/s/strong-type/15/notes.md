# strong-type 15 — 适配笔记（OHOS aarch64）

## 来源核验
- 官方仓库：https://github.com/rollbear/strong_type
- 正式标签：`v15`（git tag 指向 commit `8a2b339474904887cbb9820c48cbe28d8d9af538`）
- 源码 tarball：`https://github.com/rollbear/strong_type/archive/refs/tags/v15.tar.gz`
- SHA-256：`d445398d4c4d6795060ac2b60be146b3cd7e6039985244b2d56f9bc333f20bae`（tarball 实测）
- 许可证：BSL-1.0（Boost Software License 1.0，LICENSE）
- 平台任务：7319（`strong-type/15`，依赖活动 activity_id=6）

## 结构
- 纯头文件库：`include/strong_type/` 下 31 个模块头（type/arithmetic/difference/ordered/... + strong_type.hpp 总入口），互相裸名 include，需整组打包
- 无库构建产物：根 CMakeLists 仅用于生成 CMake package config 与上游测试（`STRONG_TYPE_UNIT_TEST=on` 挂 test/ 子目录），配方按 header-library 打包
- C++14/17/20 兼容（消费侧以 C++17 验证）
- 依赖：库本体零依赖；**上游测试依赖 Catch2**（test/catch2.hpp 优先 `find_package(Catch2 3)`，无包时上游回退运行期下载 catch.hpp v2.13.9）

## W0 依赖核验（上游测试依赖，非库依赖）
- 制品仓 `catch2/3.8.1` **配方与 binary 均已发布**（`conan install --requires=catch2/3.8.1 --build=never` 实证成功），真机测试直接复用制品，无需先适配依赖
- `fmt/8.1.1` 配方已发布（binary 与设备 libc++ 运行时不兼容，见未执行项）；fmt 9/10/11 无制品

## 分支基线说明
- 分支 `feat/strong-type-15` 基于 fork `origin/main`（9b49d7903）：W3 的 JC6 用 `origin/main...HEAD` 判定 PR 原子性，fork main 为 upstream main 祖先，PR 与官方 main 三点 diff 仍只含本包（thread-pool/mlib 同场景已验证）

## 上游测试（四维账本）
- 测试目录 `test/`，Catch2 3 框架（制品仓 catch2/3.8.1），主套件为聚合可执行 `self_test`（32 个 test 源文件）+ 可选 fmt 对照子目录（test_fmt8/9/10/11，各按 `find_package(fmt <版本>)` 条件注册）
- **N_static（静态声明）= 99**：`TEST_CASE(` 调用点逐文件统计（test/*.cpp，含 test_fmt.cpp 3 例）
- **N_executed = 87 用例 / 304 断言，全部通过**：运行器自报 `All tests passed (304 assertions in 87 test cases)`，退出码 0
- **条件未编译 = 12**（99 = 87 + 12，上游自身平台守卫，非适配缺陷）：
  - C++20 三路比较序族 6 例（partially_ordered(-_with) ×2、strongly_ordered(-_with) ×2、weakly_ordered(-_with) ×2；守卫 `__cpp_impl_three_way_comparison && <compare> && _LIBCPP_VERSION >= 15000`）
  - 哨兵迭代器 1 例（守卫 `_LIBCPP_VERSION >= 16000`）
  - 类类型非类型模板参数 1 例（守卫 `__cpp_nontype_template_args >= 201911L`）
  - difference 取余 1 例（C++20 概念守卫）
  - std::format/fmt 相关 3 例（`STRONG_HAS_STD_FORMAT` 守卫 + test_fmt.cpp 未编入无 fmt 的 self_test）
- 运行方式：`cmake -S <src> -B build -DSTRONG_TYPE_UNIT_TEST=on -DCMAKE_PREFIX_PATH=<conan gen> -DCMAKE_BUILD_TYPE=Release && cmake --build build -j2 && ./build/test/self_test`（CMakeDeps 提供 Catch2 config；CMakeDeps 要求显式 CMAKE_BUILD_TYPE）。未修改任何上游文件
- 证据：设备 `~/tmp/uc2/strong-type-15/up/build/ctest.log`、`self_test` 运行输出、`test.done=RESULT_RC=0`

### 未执行项（不计入 check 主口径）
- fmt 对照子目录 4×3=12 用例：fmt8 可执行已构建但运行期符号缺失（制品仓 fmt/8.1.1 binary 与设备 libc++ 运行时不兼容，`fmt::v8::detail::locale_ref::get` 等符号 not found）；fmt9/10/11 制品仓未发布。属可选扩展（上游按 find_package 条件注册），不影响主套件全过结论

## 消费者 API 口径（试编译迭代确认）
- 主模板是 `strong::type<int, struct tag, 修饰符...>`——**值类型在前、tag 在后**（首轮探针写反导致 SFINAE 失配的 static_assert，已纠正）
- 修饰符**不要混合 arithmetic+difference 于同一类型**：clang 15 下 arithmetic 的 `operator+=` noexcept 表达式经 difference 的实例化链求值 `value_of` 隐藏友元会失配（上游测试自身也只用单修饰符族模式）；消费者测试按上游单修饰符模式组织（arithmetic/ordered/difference/incrementable 四类各一，9 项断言全过）

## 路径 B 判断（结论：不走 B，纯路径 A）
- 零补丁、零上游修改；修饰符混用实例化顺序问题属消费侧使用模式（上游模式即可避开），不构成可跨仓库复用的独立知识。按纯路径 A 交付。

## test_package（消费者验证）
- Conan L1：CMakeDeps + find_package（C++17），消费者程序 `test_strong_type.cpp`（1 个程序，9 项断言）：arithmetic 加/减/负、ordered 小于/大于等于、difference 差类型减法与 +=、incrementable 前置/后置自增；按上游单修饰符模式组织
- `test()` 经 bash 包装执行二进制（OHOS mksh 规避），退出码 0 判定通过

## 后续
- 状态：built（2026-09-12 finish 收尾）
- 无 commands.json（纯库，无命令行产物）
---

**编译结束**: 2026-09-12 04:44
**最终状态**: built
