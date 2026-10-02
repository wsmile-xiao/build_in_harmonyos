# sems-dsm 2.1.0 适配笔记

## 编译环境
- 构建系统: cmake（上游 2.1.0 已全量迁移 CMake）
- 编译日期: 2026-09-30
- 编译器: clang / clang++（OHOS SDK 26.0.0.18，aarch64-linux-ohos，musl，libc++，C++17）
- 状态: built
- 依赖: libevent/2.1.12（制品仓，静态链接）

## 编译步骤
1. `conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing`
2. `source()`：取官方 tarball `sems-2.1.0.tar.gz`（sha256 `f16c2891…8756`），`strip_root=True`；剔除上游 tarball 内的 CodeQL 自引用软链 `_codeql_detected_source_root`
3. `generate()`：`CMakeToolchain` 关闭全部可选组件（`SEMS_USE_OPUS/ILBC/MONITORING/PYTHON… = OFF`），仅构建 core 静态库（`libsems_core.a` / `libsems_sip.a`）+ dsm app 模块（`dsm.so`）+ 测试程序
4. `build()`：构建 dsm 目标，并 `cmake.build(target="sems_tests")` 构建上游单体测试程序
5. `package()`：`lib/` 收插件与 core 静态库、`bin/` 收 `sems_tests`、随包分发 resample 源码与 DSM 图表
6. `test_package`：真实 `dlopen` 插件 + 工厂契约校验 + 图表语法校验

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | OHOS musl 下链接报 `pthread_cancel` 不可用 | musl libc 未实现 `pthread_cancel`，而上游 `AmThread::cancel()` 依赖它 | `patches/0001`：`#if defined(__OHOS__) \|\| defined(__MUSL__)` 分支改走协作停止（`DBG` + `_stopped.set(true)`），`#else` 保留上游语义。**R8 例外说明**：平台宏此处仅用于选择上游已有的协作路径，分支内含实质逻辑（日志 + 状态置位），非空壳 stub |
| 2 | CMake 找不到 libevent | 上游 CMake 期望系统 `find_package` 的结果，conan 依赖目录未进入搜索路径 | `patches/0002`：注入 `LIBEVENT2_INCLUDE_DIR` / `LIBEVENT2_LIB_DIR` / `LIBEVENT2_LIBRARIES`（静态库完整路径，注意 CMake 列表分号语义） |
| 3 | 插件重定位失败：`dsm.so` 引用 420 个 core 符号（`llvm-nm` 实测） | SEMS 插件由 `-rdynamic` 宿主进程加载，符号由宿主提供而非插件自身 | 测试宿主以 `-Wl,--whole-archive` 按绝对路径收录随包 `libsems_core.a`/`libsems_sip.a` + 静态 libevent，`LINKER_LANGUAGE CXX` 带 libc++ 运行时，`-rdynamic` 导出符号 |
| 4 | `ResampleFactory` 符号缺失 | 上游 `target_sources` 把 `core/resample.cpp` 只挂到 `sems`/`sems_tests` 可执行目标（不在 `sems_core` 内） | 随包分发该源码，由测试宿主一并编译补齐 |
| 5 | 上游 tarball 含符号链接循环 | CodeQL 打包残留 `_codeql_detected_source_root`（自引用软链） | `source()` / `package()` 阶段剔除该软链 |

## 源码修改
- `patches/0001-ohos-musl-pthread-cancel.patch` → `core/AmThread.cpp`（协作停止分支）
- `patches/0002-inject-libevent-dirs.patch` → `core/CMakeLists.txt`（libevent 探测变量注入）
- 两枚补丁均为可移植性适配，**未修改上游任何测试用例**。

## 依赖版本
- `libevent/2.1.12`（Conan 制品仓；静态链接，规避 musl + 无 rpath 场景的运行期加载失败）
- 工具链：OHOS SDK 26.0.0.18 clang 15，`aarch64-linux-ohos`，libc++，C++17

## 上游测试用例申报表（R51 三步法）

- **① 清点**：上游 `core/tests/` 共 **11 个 suite 源文件**（`test_amconfig/auth/extensions/headers/jsonarg/parser/replaces/rfc3261_musts/rfc3261_parser/sdp/uriparser.cpp`）+ `sems_tests.cpp`（`fct.h` 入口）+ `fct.h`。上游 CMake 将该目录编译为**单体可执行程序** `sems_tests`（`core/CMakeLists.txt`：`add_executable(sems_tests …)` / `add_test(NAME Tests COMMAND sems_tests)`；主 `CMakeLists.txt` `enable_testing()`）。
- **② 真实执行**：配方 `build()` 构建 `sems_tests` 并随包分发（`bin/sems_tests`），`test_package` 的 `test()` 第一步真实运行；2026-09-30 于 HarmonyOS PC（aarch64，OHOS SDK 26.0.0.18 clang 15，musl）实跑。
- **③ 如实回填**：逐 suite `FCT_TEST_BGN` 静态计数 = 88+25+15+14+13+13+11+10+8+5+2 = **204**；实跑输出 **`PASSED (204/204 tests in 0.016430s)`**、退出码 0、日志内 `FAILED`/`ERROR` 命中 0 —— 静态计数与运行结果一致。
- **补全测试（鸿蒙特有，N=3 ≥ 1，`test_package/test.c`，完整消费者用例非纯断言）**：
  1. `dlopen` 加载随包 `sems/plug-in/dsm.so` 成功；
  2. `plugin_class_create` 工厂契约（SEMS app 模块 CLASS 导出，`DSM.cpp` / `AmApi.h`）可用；
  3. 随包 DSM 状态机图表（`share/sems/dsm/charts/inbound_call.dsm`）读取 + 语法标记校验。

## 验证结果

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# → sems-dsm/2.1.0: Created package revision bdcdf2e01f6eb94ffaa5fe0a306f8223
# test_package 输出：
#   PASSED (204/204 tests in 0.016430s)          ← 上游 sems_tests
#   PASS: dlopen …/sems/plug-in/dsm.so
#   PASS: plugin_class_create (app-module contract)
#   PASS: DSM chart readable (873 bytes, syntax ok)
#   RESULT: sems-dsm 2.1.0 plugin consumer test OK (load+export+chart)
```

## 交付物

| 文件 | 说明 |
|------|------|
| `lib/sems/plug-in/dsm.so` | DSM 状态机解释器插件（SEMS app 模块） |
| `bin/sems_tests` | 上游单体测试程序（随包分发，供 `test_package` 真实执行） |
| `include/` + `lib/*.a` | core 静态库与头文件（插件宿主链接所需） |
| `share/sems/dsm/charts/*.dsm` | DSM 图表（消费者用例校验对象） |

## 注意事项

- **插件型包的非自包含性**：本包不是可独立 `dlopen` 的普通库 —— 插件依赖宿主导出的 core 符号（420 个，`llvm-nm` 实测），消费者须按 `test_package/CMakeLists.txt` 的 `--whole-archive` + `-rdynamic` 方式链接宿主。
- `commands.json` 中 `bin/sems_tests` 的用途是 R51 实测证据（库包不提供 CLI 服务）。
- 待办（本轮检视提出，不阻塞构建）：`patches/0001` 的平台宏可改为 CMake 能力探测 `check_symbol_exists(pthread_cancel "pthread.h" HAVE_PTHREAD_CANCEL)`（同源姊妹 PR #13892 即此法），以彻底避免补丁内引入平台宏（R8）。

---
**编译结束**: 2026-09-30 23:06
**最终状态**: built
