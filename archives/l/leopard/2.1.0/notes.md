# leopard 2.1.0 适配笔记

## 软件信息

- **名称**: leopard（上游项目 hosseinmoein/Leopard，C++ light-weight Thread Pool）
- **版本**: 2.1.0（上游 tag `2.1.0`，**无 v 前缀**；`git ls-remote --tags` 实证仅 1.0.0 / 2.0.0 / 2.1.0 三个 tag）
- **源码**: https://github.com/hosseinmoein/Leopard/archive/refs/tags/2.1.0.tar.gz
- **SHA256**: `26b57fdea4cd94ddbc34a478e978632637cde2fc263bdf2d6bdfd3e9ddd0b1d5`
  （与 conan-center-index `recipes/leopard/all/conandata.yml` 的 2.1.0 条目**逐字一致**，双源实证）
- **构建系统**: CMake（`cmake_minimum_required(3.8)`，设备 cmake 4.1.2 兼容，仅弃用告警）
- **语言标准**: C++20（头文件用 concepts `requires` 与 `std::optional`；设备 clang 15.0.4 满足）
- **许可证**: BSD-3-Clause
- **依赖**: **0 个第三方 Conan 依赖**（双源实证：① conan-center-index 配方无 `requires`；
  ② 上游 `CMakeLists.txt` 只有 `find_package(Threads REQUIRED)`，`src/CommonMakefile.mk`
  只链 pthread/dl/m；③ `conan list "leopard/*" -r=ohpcd` 返回 0、本地缓存 0）

## 编译环境

- 构建系统: cmake
- 编译日期: 2026-09-29
- 编译器: clang/clang++ 15.0.4（aarch64-unknown-linux-ohos）
- 状态: built

## 配方设计

- `package_type = "header-library"`；产物 = `include/Leopard/{ThreadPool,SharedQueue}.{h,tcc}` + `License`，
  `package_id` 清空（单一 package id）。
- `package_info()`：`cmake_file_name=ThreadPool`、`cmake_target_name=ThreadPool::ThreadPool`、
  `pkg_config_name=ThreadPool`，`system_libs=[pthread]`（OS ∈ {Linux, FreeBSD, OHOS}）。
- `configure()` 把 `compiler.cppstd` 从 CI profile 的 17 提到 20（头文件是 C++20），
  `validate()` 用 `check_min_cppstd(self, 20)` 固化该要求。
- `build()`：应用补丁 → `cmake.configure()` → `cmake.build()` → `cmake.test()`
  —— 上游 7 个 ctest 条目随 `conan create` 在设备上真实运行。

## 首条真实错误与修复

补丁前原生 `cmake -S . -B build -DHMTHRP_TESTING=ON` 直接失败：

```text
CMake Error: INSTALL(EXPORT) given unknown export "ThreadPoolExport"
-- Generating done
CMake Generate step failed.  Build files cannot be regenerated correctly.
```

根因与修复见下节「源码修改」。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 必然失败：`INSTALL(EXPORT) given unknown export "ThreadPoolExport"` | 全文件没有任何 target，却有 `install(EXPORT ThreadPoolExport ...)` | 补丁 0001 新增 `add_library(ThreadPool INTERFACE)` + `install(TARGETS ... EXPORT ThreadPoolExport)` |
| 2 | 测试编译报 `Leopard/ThreadPool.h file not found` | `test/` include `<Leopard/...>`，但没有任何 include 路径 | 补丁 0001 加 `include_directories(.../include)` 与 INTERFACE 目标的 `BUILD_INTERFACE`/`INSTALL_INTERFACE` |
| 3 | `install(DIRECTORY .../include/ThreadPool)` 指向不存在的目录 | 项目由 ThreadPool 改名 Leopard 时漏改 install 规则 | 补丁 0001 改为 `include/Leopard` |
| 4 | 上游 CMake 从不选择 C++20，`requires`/`std::optional` 编译失败 | C++20 只写在 `src/Makefile.Linux.GCC64` 的 `-std=c++20` 里 | 补丁 0001 加 `set(CMAKE_CXX_STANDARD 20)` |
| 5 | **Release 下 `par_sort_tester` 死循环（600s 超时被杀）** | `NDEBUG` 把 `assert(...)` 展开为空，而该有序性 `for` 循环的唯一自增写在 `assert()` 内；同时全部 22 处断言失效 ⇒ 假绿 | 配方 `generate()` 把 `CMAKE_CXX_FLAGS_RELEASE` 钉回 `-O3`（**不改任何上游测试文件**）；同族知识 = 既有条目 E259 |
| 6 | `System is unknown to cmake, create: Platform/HarmonyOS` | CMake 不认识 `CMAKE_SYSTEM_NAME=HarmonyOS` | 无害告警（知识库 E267 同族）；本版本 `GNUInstallDirs` 仍正常给出 `include`/`lib`，实测 install 路径正确 |

## 源码修改

- `patches/0001-cmake-repair-header-only-target-and-leopard-include-dir.patch`（对 `CMakeLists.txt`，+18/-1）：
  1. `set(CMAKE_CXX_STANDARD 20)` / `set(CMAKE_CXX_STANDARD_REQUIRED ON)`；
  2. 新增 `include_directories(.../include)` 与 `ThreadPool` INTERFACE 目标
     （含 `BUILD_INTERFACE`/`INSTALL_INTERFACE` include 目录、`Threads::Threads` 链接）
     并 `install(TARGETS ThreadPool EXPORT ThreadPoolExport)`；
  3. `install(DIRECTORY .../include/ThreadPool)` → `include/Leopard`。

  **未修改任何上游测试文件**；补丁为纯可移植性/构建修复，不含 `__OHOS__` 平台宏。

## 上游测试清点（R51 三步法）

| 口径 | 数值 | 取数命令 |
|---|---|---|
| `add_test` 注册条目（ctest 口径） | **7** | `grep -c '^add_test' test/CMakeLists.txt` |
| 测试源文件 / 测试程序数 | 7 | `ls test/*.cc \| wc -l` |
| **程序内命名子测试函数（申报口径 = 候选数法最大值）** | **16** | 逐文件清点 `main()` 内调用的测试函数 |
| `assert()` 断言点（assertion 口径，单列不混用） | 22 | `grep -c 'assert(' test/*.cc` 求和 |

- 16 = `thrpool_tester` 7 + `par_sort_tester` 4 + 其余 5 个程序各 1。
- `par_map_reduce` 无 `assert()`，判据为退出码 + 结果打印（如实记录，不改上游测试）。
- `test_package` 消费者 10 项断言**单列**，不进上游分母。

## 验证结果

上游测试（设备原生，未定义 `NDEBUG` 的 Release `-O3` 构建，逐程序带 900s 硬超时执行）：

```text
thrpool_tester        rc=0   55.4s  PASS
par_sort_tester       rc=0   18.3s  PASS
par_accumulate_tester rc=0    0.1s  PASS
par_map_reduce        rc=0    8.4s  PASS
par_partial_sum       rc=0    0.1s  PASS
par_adjcent_diff      rc=0    0.0s  PASS
par_dot_product       rc=0    0.0s  PASS
TOTAL=16 PASS=16 FAIL=0 SKIP=0 NOT_RUN=0（7 个程序全部 rc=0）
```

消费者探针（`test_package/test_leopard.cpp`）：`CHECKS=10 FAILURES=0`。

命令与逐字输出留档：`$TASK_DIR/upstream-test-assert-on/`（仓库外）。

## 依赖版本

无第三方依赖；工具链 = clang 15.0.4 / cmake 4.1.2 / GNU Make 4.4.1 / conan 2.29.1。

## 注意事项

- 上游 `src/Makefile.Linux.GCC64` 为历史构建路径，本设备不可用（硬编码 `CXX = /usr/bin/g++`、
  `-I/usr/include/c++/7`），故未采用。
- 平台任务卡把本软件描述为「C++ 时间序列数据库」，与上游实际内容（C++ 线程池）不符；
  以上游 README 与 conan-center-index 描述为准。
