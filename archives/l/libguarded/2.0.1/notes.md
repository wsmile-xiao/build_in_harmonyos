# libguarded 2.0.1 — 适配笔记

## 软件信息

- **名称**: libguarded（上游项目 CopperSpice CsLibGuarded，`cs_libguarded`）
- **版本**: 2.0.1（上游 tag `libguarded-2.0.1`，无 GitHub Releases，源码取 tag 归档）
- **源码**: https://github.com/copperspice/cs_libguarded/archive/refs/tags/libguarded-2.0.1.tar.gz
- **SHA256**: 59167282e7a7957a614271d993c3070fadddf895d0f5aecf08f2e4e90d16ee2d
- **构建系统**: CMake（`cmake_minimum_required(3.18)`，设备 cmake 4.1.2 兼容）
- **语言标准**: C++20（INTERFACE target `cxx_std_20`，设备 clang 15 满足）
- **许可证**: BSD-2-Clause

## 配方设计

- `package_type = "header-library"`；上游导出 `CsLibGuarded::CsLibGuarded` INTERFACE target，`package_info()` 声明 `cmake_file_name=CsLibGuarded`、`cmake_target_name=CsLibGuarded::CsLibGuarded`。
- 无第三方 Conan 依赖，仅依赖 C++20 标准库与 pthread（上游测试经 `find_package(Threads)`，设备上 `CMAKE_HAVE_LIBC_PTHREAD=No`、`pthread_create in libpthread=Yes`，正常找到）。
- 头文件安装到 `include/CsLibGuarded/`；`cpp_info.includedirs = ["include", "include/CsLibGuarded"]` 同时覆盖 `<CsLibGuarded/cs_*.h>` 与 `<cs_*.h>` 两种上游合法 include 写法。
- `build()` 内开启 `BUILD_TESTS=ON` 并执行 `cmake.test()`，上游 Catch2 套件随 `conan create` 在设备上真实运行。
- 保持真实平台身份：不做 `CMAKE_SYSTEM_NAME=Linux` 覆盖，依赖 OHOS 版 conan 自动映射 `os=OHOS → CMAKE_SYSTEM_NAME=HarmonyOS`，由补丁使上游分支接受该拼写。配置期出现的 `System is unknown to cmake` 提示为已知无害告警（知识库 E267），不影响配置与构建。

## 首条真实错误与修复

补丁前原生验证（设备 cmake 自动识别 `HarmonyOS`）：

1. configure 成功，但输出只有 `CsLibGuarded will be installed in: /usr/local`，无 GNUInstallDirs 的相对目录变量。
2. `cmake --install` 第一条真实错误：

```text
CMake Error at .../cmake_install.cmake:54 (file):
  file cannot create directory: /cmake/CsLibGuarded.  Maybe need
  administrative privileges.
```

根因：`CMakeLists.txt` 平台链 `if (Darwin) / elseif (Linux|OpenBSD|FreeBSD|NetBSD|DragonFly) / elseif (Windows)` 不含 HarmonyOS/OHOS，`include(GNUInstallDirs)` 在 OHOS 上不执行，`CMAKE_INSTALL_LIBDIR` 等为空；空变量拼进 `DESTINATION "${CMAKE_INSTALL_LIBDIR}/cmake/CsLibGuarded"` 后退化为绝对路径 `/cmake/CsLibGuarded`，configure 不报错、install 阶段才失败。

修复（patches/0001-CMakeLists.txt.patch，+1/-1）：平台正则扩展为 `(Linux|OpenBSD|FreeBSD|NetBSD|DragonFly|OHOS|HarmonyOS)`，同时获得 GNUInstallDirs 与 ELF `$ORIGIN` RPATH。选择补丁而非 recipe 层 Linux 覆盖：保持平台身份真实，且同族 CopperSpice CMake 骨架库可复用该结论。

## 测试证据

上游测试（补丁前后各跑一遍，设备原生）：

- `ctest -N`：21 个用例（8 个 Catch2 测试文件经 ParseAndAddCatchTests 展开）。
- 补丁前：21/21 通过（基线）；补丁后：21/21 通过。统计单位为 ctest case。
- 命令：`ctest --test-dir <build> --output-on-failure`。

Conan/test_package：

- `conan create` 包内构建执行同样 21 个上游用例；`test_package` 为 1 个真实消费者程序，10 项显式检查（plain/shared/lr/rcu/cow 全部命中、`cow.cancel()`、`lock_guards` 双对象顺序加锁、4×500 与 2×250 多线程压力），设备端 10/10 通过。

## 知识库路径判断

本次为路径 B：E267 覆盖 `System is unknown to cmake` 告警与源码宏检测，E532 覆盖 `if(WIN32)/elseif(UNIX)/else FATAL` 三分支 configure 期致命错误；均未覆盖“平台分支承载 GNUInstallDirs、HarmonyOS 下 CMAKE_INSTALL_* 静默为空、install 阶段以绝对路径失败”这一签名与诊断组合。已按模板生成草稿 `knowledge/drafts/`，并提交知识库扩展 PR 与关联 Issue。
---

**编译结束**: 2026-09-04 23:34
**最终状态**: built
