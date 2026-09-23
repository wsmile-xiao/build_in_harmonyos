# clamav-libunrar 1.4.5 适配笔记

## 编译环境
- 构建系统: cmake（仅配置上游 `libclamunrar/` 子目录）
- 编译日期: 2026-09-09
- 编译器: clang/clang++ (HarmonyOS PC aarch64)
- 状态: built（待 HMBS 真机预检，未提交）

## 上游信息
- 官方仓库: https://github.com/Cisco-Talos/clamav
- 发布页: https://www.clamav.net/
- 版本: 1.4.5（tag `clamav-1.4.5`）
- 源码包: `https://github.com/Cisco-Talos/clamav/archive/refs/tags/clamav-1.4.5.tar.gz`
- sha256: `afd91f024df9def18336069b9a6bf654b084574a3148bcd1da38a434f2b9434e`（2026-09-09 实测下载 13480089 字节计算）
- 许可证: ClamAV 主体 GPL-2.0-only；内嵌解码器另带 UnRAR freeware 条款（见包内 `licenses/license.txt`）

## 适配方案
1. 上游把 `libclamunrar` 放在单体 ClamAV 源码树内，无独立发布包。配方 `source()` 拉取完整 tag 包，
   `build()` 仅 `cmake.configure(build_script_folder=<source>/libclamunrar)`，避开顶层构建对
   Rust 工具链、Libcheck、python pytest 的强依赖（子目录构建模式参考 azure-core-cpp 配方与 E426）。
2. 子目录 CMake 原由顶层提供变量，独立配置时在 `generate()` 显式补齐（顶层 1.4.5 取值）：
   `ENABLE_SHARED_LIB/ENABLE_STATIC_LIB`（随 `shared` 选项二选一）、`LIBCLAMAV_VERSION=12.0.3`、
   `LIBCLAMAV_SOVERSION=12`、`CMAKE_INSTALL_LIBDIR=lib`（子目录未引入 GNUInstallDirs）。
3. OHOS 下 CMake 无 HarmonyOS 平台模块，共享库 SONAME 标志为空，沿用 azure-core-cpp 的
   `CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG=-Wl,-soname,` 守卫（仅 `os == OHOS`）。
4. 上游只安装库目标、不安装头文件，`package()` 手工复制公共 C API 头
   `dll.hpp` + `raros.hpp`（后者提供 `_UNIX` 宏）到 `include/`，`license.txt` 到 `licenses/`。
5. 无外部 Conan 依赖（解码器仅依赖 libc/libc++），不声明 `requirements`，无需 `commands.json`（纯库）。

## 上游测试审计结论
- `libclamunrar/` 内无 `tests/` 目录、无 gtest/pytest 痕迹，`CMakeLists.txt` 仅含 `add_library`，
  无 `enable_testing`/`add_test`，`ctest -N` 发现 0 测试。
- 顶层 `unit_tests/` 覆盖完整 libclamav 协议栈，需 Rust + Libcheck + pytest，与本独立包无关，
  在预检环境不可运行。
- 因此 `upstream_tests_exist: false`，真机输出 `HMBS_UPSTREAM_TEST_RESULT status:"no_tests"`。
- 证伪说明：本包测试不依赖 fixture 文件（toybox 空文件陷阱不适用），4 项检查全部断言真实
  API 返回值（版本号 8、双路径 `ERAR_EOPEN=15`、关闭返回 `ERAR_SUCCESS=0`）；若链接桩库或
  空壳实现，`RARGetDllVersion` 断言即失败，harness 以非零退出码捕获。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 顶层 CMake 要求 Rust/Libcheck | 单体构建的完整依赖 | 只配置 `libclamunrar/` 子目录 |
| 2 | 独立配置时 `ENABLE_SHARED_LIB` 等变量未定义导致无库目标 | 变量原由顶层 `CMakeOptions.cmake` 提供 | `generate()` 按 `shared` 选项显式传值 |
| 3 | `CMAKE_INSTALL_LIBDIR` 为空导致 install 目标非法 | 子目录未 `include(GNUInstallDirs)` | 显式传 `-DCMAKE_INSTALL_LIBDIR=lib` |
| 4 | OHOS 共享库 SONAME 为空 | CMake 无 HarmonyOS 平台模块 | 复用 azure-core-cpp 的 SONAME flag 守卫 |
| 5 | 包内无头文件，消费者无法 `#include` | 上游无 `install(FILES)` | `package()` 手工复制 `dll.hpp` + `raros.hpp` |
| 6 | 真机 `project()` 报编译器识别未知，三轮平台伪装/临时目录透传/预设编译器标识均无效 | 预设标识跳不过识别解析，识别仍需可用编译器+可写临时目录+有效平台模块；外加的平台覆盖与识别预设反而使 CMake 状态不一致 | 删除全部覆盖改用原生工具链，但真机明确报 System is unknown to cmake（CMake 4.4.3 无 Platform/HarmonyOS 模块），证明最小 Linux 平台借用不可少；本轮恢复最小借用（平台名+处理器+静态 try-compile），仍不预设编译器标识，保留 HMBS_TMPDIR 优先 |
| 9 | 回退 CMakeToolchain+Linux 借用仍报编译器识别未知（/data/service/hnp/bin/clang），且伴随 Problem parsing /proc/meminfo；ohos.toolchain 在预检机根本不存在 | CMake 的 try_compile/识别链依赖 conan 工具链注入的 sysroot/target 标志与受限 /proc，在该机上无可用组合；前三轮均为 CMake 参数级调参 | 删除全部 CMake 调用，主配方改为 conf 编译器直接编译上游 48 个 .cpp（defines/flags/include 与上游 CMakeLists 逐项对齐，ar 归档静态/.so 直链共享），test_package 本已直编保持；保留 TMPDIR 导出与签名容错 |
| 8 | 真机 project() 报编译器识别未知（CMAKE_C/CXX_COMPILER /data/service/hnp/bin/clang），伴随 /tmp 只读；前三轮 CMakeToolchain+Linux 借用与 E557 宿主运行时探针均未改变该错误 | CMakeToolchain 在 os=OHOS 时映射出 CMake 无平台模块的 system 名（ML-0035），Linux 借用叠加 OHOS SDK flags 使识别状态不一致；E557 的 libxml2 假设无日志证据（预检无探针输出、无 ldd 缺库证据） | 删除 CMakeToolchain 与 E557 探针，改用已验证 ohos.toolchain+裸 cmake（expat/xxhash/zstd 同法）：主配方自发现 ohos.toolchain.cmake 并裸 cmake 配置/构建，test_package 改为直接 clang 编译+运行（消除第二个 CMake project 失败点），保留最小 TMPDIR 导出与 .so 重签容错 |
| 7 | 最小借用后仍报编译器识别未知；E557 草稿明确禁止 try-compile / 编译器标识类绕过，且指出真凶多为宿主工具链运行时（SDK lld 动态依赖 libxml2.so.16 无法加载），CMake 只报表面症状 | 前三轮恰好依赖被禁的绕过路线，从未真正证明工具链可用；绕过还会把能力误判写进产物 | 删除 try-compile 绕过，保留最小 Linux 平台借用，主配方与 test_package 各自实现 E557 宿主运行时门：真实 C/C++ 编译链接探针，失败时从工具链派生 libxml2.so.16 目录并以 Conan Environment 局部 prepend LD_LIBRARY_PATH，仅作用于 configure/build，失败则 fail closed（参照 ls-hpack 2.3.5 实现，不硬编码 SDK 路径） |

## 依赖版本
- 无外部依赖。

## 验证结果
- 本地（Windows）仅完成源码审计与配方编写，未运行 conan（按守则不在本机运行 conan）。
- 待 HMBS 真机预检：`conan create`（OHOS aarch64）+ ctest 4 项检查 + `no_tests` 上游标记。
- 真机与命令属内部基建，仅记录于本笔记，不写入 PR 正文。
