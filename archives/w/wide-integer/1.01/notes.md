# notes.md — wide-integer 1.01 适配笔记

## 一、软件概况

- 上游：https://github.com/ckormanyos/wide-integer（tag v1.01）
- 类型：header-only C++20 任意精度整数库（唯一公开头文件 `math/wide_integer/uintwide_t.h`）
- 官方来源 SHA-256：`d295c92a6c70b89f8901f31bcc3f0e8128b5ff5e60e549f4063196b0b3bc9603`
  （GitHub archive `refs/tags/v1.01.tar.gz`，经 ghfast.top 与 gh-proxy.com 双镜像独立下载，交叉核验一致）
- conanfile.py：header-only 配方（无编译阶段），test_package 真实调用 uintwide_t API

## 二、HarmonyOS PC (aarch64) 适配点

### 补丁 0001：native_float_parts 的 long double 尾数存储扩展到 unsigned __int128

- 现象：`test/test_uintwide_t_edge_cases.cpp` 构造 `uintwide_t(inf_ld)` 时，
  实例化 `detail::native_float_parts<long double>`，命中 static_assert：
  `std::numeric_limits<long double>::digits (113) <= std::numeric_limits<unsigned long long>::digits (64)` 失败。
- 根因：x86-64 上 long double 是 80-bit 扩展精度（64 位尾数，恰好适配 ull）；
  aarch64（HarmonyOS PC）上 long double 是 IEEE quad（113 位尾数），超出 ull 容量。
  上游头文件注释也声明"需验证尾数能放入 unsigned long long"，属平台差异。
- 修复：`native_float_parts<FloatingPointType>` 用 `std::conditional` 按
  `digits > 64` 选择 `unsigned __int128` 作为尾数存储类型（mantissa_storage_type），
  static_assert 改为对存储类型校验；归一化位移 `1 << (digits-1)` 同步改用存储类型，
  避免 113 位移位溢出 64 位类型。
- 验证：OHOS clang 15 (aarch64-unknown-linux-ohos) 编译全部上游测试通过并运行通过。
- guard 说明：本补丁无平台宏，纯类型宽度适配，任何 80/113 位 long double 平台通用。

## 三、上游测试全量枚举与运行（双口径台账）

### 枚举口径（可复制规则）

按官方 tag 源码可复制枚举：主运行器 `test/test.cpp` 的 `run()` 内逐函数调用清单
（28 个独立测试函数：small_bits、boost_backend、examples、edge_cases、float_convert、
int_convert、spot_values、0000024/0000048/0000064/0000064_signed/0000096/0000128/
0000256/(0000256_limb_type_uint64_t)/0000512/0000512_signed/0001024/0002048/0008192/
(0008192_limb_type_uint64_t)/0012288/0032768/0065536_alloc/0008192_by_0012288/
0012288_by_0008192/0000032_by_0000032_4_by_4/0000064_by_0000064_4_by_4；
两个 limb_type_uint64_t 项在 `-DWIDE_INTEGER_HAS_LIMB_TYPE_UINT64` 下启用，本轮已启用），
加 2 个自带 main 的独立测试程序（xtra_from_issue_335、boost_backend_via_test_arithmetic），
共 **30 个 source_declared_total**。

框架头/源码、样例、基准、fixture、脚本、构建目标逐项说明：

| 条目 | 类别 | 是否独立用例 | 是否在本配置实例化/运行 | 备注 |
|---|---|---|---|---|
| test/test.cpp (run() 28 函数) | 用户测试源主运行器 | 是（28 个独立函数） | 是，28/28 通过 | ctest 注册名 `test test_uintwide_t` |
| test/test_uintwide_t_xtra_from_issue_335.cpp | 用户测试源（自带 main） | 是（1 个） | 是，1/1 通过 | issue 335 回归 |
| test/test_uintwide_t_boost_backend_via_test_arithmetic.cpp | 用户测试源（自带 main） | 是（1 个） | 是，1/1 通过 | Boost.Test report_errors=0 |
| test/test_uintwide_t_boost_backend.cpp 等 7 个 *_base.cpp | 供主运行器链接的实现文件 | 否（非独立用例） | 通过主程序运行 | 与 test.cpp 同批编译 |
| test/fuzzing/*.cpp (8 个 add/div/mul/powm/prime/sdiv/sqrt/sub) | libFuzzer harness | 否（无 main，fuzz 回调，非独立 TEST_CASE） | 未实例化 | 上游未接入 CMake 测试目标，需 libFuzzer 构建 |
| examples/*.cpp (23 个 example000-014) | 样例 | 否（样例，不计入用例） | 通过主程序间接运行 | test_uintwide_t_examples() 调用 |
| test/parallel_for.h / stopwatch.h / *.hpp 模板头 | 框架头/辅助头 | 否 | — | — |
| test/fuzzing 目录 | fuzz harness 集合 | 否 | — | 见上 |

### 执行证据（OHOS aarch64，clang 15，`-DWIDE_INTEGER_HAS_LIMB_TYPE_UINT64`）

| 编译产物 | 实际命令（cwd=src 根） | 退出码 | 运行日志（SHA-256） |
|---|---|---|---|
| test_uintwide_t | `clang++ -O2 -Wall -Wextra -Wpedantic -std=c++20 -DWIDE_INTEGER_HAS_LIMB_TYPE_UINT64 -DWIDE_INTEGER_HAS_MUL_8_BY_8_UNROLL -I. -I$BOOST_INC -pthread -lpthread test/test.cpp test/test_uintwide_t_boost_backend.cpp test/test_uintwide_t_edge_cases.cpp test/test_uintwide_t_examples.cpp test/test_uintwide_t_float_convert.cpp test/test_uintwide_t_int_convert.cpp test/test_uintwide_t_n_base.cpp test/test_uintwide_t_n_binary_ops_base.cpp test/test_uintwide_t_spot_values.cpp examples/*.cpp -o test_uintwide_t` | 编译 0；运行 0 | `5e16466693da1b0a91939bac09e8dd694ab029b7cf189f717c28f26616bf315f`（`result_of_main: 0`） |
| test_xtra_from_issue_335 | `clang++ -O2 -std=c++20 -DWIDE_INTEGER_DISABLE_PRIVATE_CLASS_DATA_MEMBERS -DWIDE_INTEGER_NAMESPACE=ckormanyos -I. -I$BOOST_INC test/test_uintwide_t_xtra_from_issue_335.cpp -o test_xtra_from_issue_335` | 编译 0；运行 0 | `9f6d29b0b76d8348d6677de434ff451a4b3e8dbdbdc469a0338dd77006db0271` |
| test_boost_backend_via_test_arithmetic | `clang++ -O2 -std=c++20 -DWIDE_INTEGER_HAS_LIMB_TYPE_UINT64 -I. -I$BOOST_INC test/test_uintwide_t_boost_backend_via_test_arithmetic.cpp -o test_boost_backend_via_test_arithmetic` | 编译 0；运行 0 | `063a32d3d02a8f9581405b89d88f6f330fb3828fed4233d8fc21bfd8732a8dea`（No errors detected） |

- 运行依赖 Boost（上游测试 include boost/multiprecision 等）。registry 已有 `boost/1.85.0`
  （recipe revision 8dfd18e...，2026-09-09 发布），已用 `conan install --deployer=full_deploy`
  部署头文件目录并用于编译。**注意：Boost 是本库上游测试的测试期依赖，不是库本身的运行时/构建依赖
  （wide-integer 本体为 header-only 零依赖），conanfile.py 不声明 requires。**
- CMake/CTest 注册路径：上游 `test/CMakeLists.txt` 仅注册 1 个 CTest 入口
  （`add_test(test test_uintwide_t)`），且仅在 `find_package(Boost)` 命中时启用。
  直接跑 CMake configure 时 CMake 4.1.2 无 HarmonyOS 平台模块（需 OHOS 工具链文件注入），
  属基础设施限制；已用上游头文件注释内记录的同源 clang++ 命令行实际编译并运行同等二进制。

### 双口径统计

- source_declared_total = **30**（主运行器 28 个函数 + 2 个自带 main 独立程序；fuzz harness 不计入）
- configured_executable_total = **30**（3 个可执行程序承载全部 30 项，全部实例化）
- executed_passed_total = **30**
- 失败 = 0；未运行/未实例化 = 0（8 个 fuzz harness 非独立 TEST_CASE，另列）
- 全量通过率 = **30/30 = 100%**；当前配置可执行集合通过率 = **30/30 = 100%**
- 源码声明 → 构建条件 → 构建目标 → 执行日志映射：见上表逐项证据（命令/退出码/日志 SHA-256）

## 四、补丁文件

- `patches/0001-math-wide_integer-uintwide_t.h.patch`（+17/-8，唯一变更文件）
- orig hash `0f0ad00d2777b703` → work hash `b16311dd444e86cc`
---

**编译结束**: 2026-09-19 12:09
**最终状态**: built
