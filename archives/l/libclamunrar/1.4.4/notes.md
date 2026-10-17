# libclamunrar 1.4.4 for HarmonyOS

## 概述

libclamunrar 在 HarmonyOS/OpenHarmony (aarch64) 上的编译指南和测试记录。

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | libclamunrar |
| 版本 | 1.4.4 |
| 下载地址 | https://github.com/Cisco-Talos/clamav/archive/refs/tags/clamav-1.4.4.tar.gz |
| 官方文档 | https://github.com/Cisco-Talos/clamav/tree/clamav-1.4.4/libclamunrar |
| 许可证 | UnRAR（freeware，禁止用于开发 RAR 兼容压缩器） |

## 鸿蒙环境

| 项目 | 值 |
|------|-----|
| 系统版本 | HarmonyOS HongMeng Kernel |
| 架构 | aarch64 |
| 编译器 | clang (LLVM) |
| 构建系统 | cmake（配方内生成的独立引擎工程） |

## 源码结构

- 上游 tag `clamav-1.4.4` 的 `libclamunrar/` 子目录：50 个 C++ 引擎源文件 + `dll.hpp` 公开 API。
- 顶层 ClamAV CMake 强制 `find_package(Rust REQUIRED)`，OHOS CI 无 Rust，按 W0b 选型结论绕开，独立构建引擎。
- 公开 API：`RAROpenArchive` / `RAROpenArchiveEx` / `RARReadHeader` / `RARProcessFile` / `RARCloseArchive` / `RARGetDllVersion`（`RAR_DLL_VERSION=8`）。
- SONAME 沿用 `LIBCLAMAV` 版本规则（1.4.4：CURRENT=12 REVISION=3 AGE=0 → `libclamunrar.so.12.0.3`）。

## 编译步骤

```bash
cd archives/l/libclamunrar/1.4.4
conan create . --user=ohpcd --channel=stable -pr:h=<ohos-profile> -pr:b=<ohos-profile> --build=missing
```

配方在 `build()` 内生成最小 `CMakeLists.txt`（`RARDLL` + `_FILE_OFFSET_BITS=64` + `_UNIX`，C++11），`cmake.configure(build_script_folder=build_folder)` 后 `cmake.build()`，`package()` 走 `cmake.install()` 并安装 `dll.hpp`。

## 上游测试审计

- `libclamunrar/` 无 `tests/` 目录、无 `add_test`/ctest 注册（见 `test_package/MANIFEST.yml` 的 `upstream_test_audit`）。
- RAR 集成检查位于 ClamAV `unit_tests/check_clamav.c` 的 `HAVE_UNRAR` 分支，需完整 `libclamav` + Rust 工具链，不属于本独立引擎包。
- 结论：`upstream_tests_exist: false`，`HMBS_UPSTREAM_TEST_RESULT(status=no_tests)` 由 `test_package` 每轮复发。

## 测试结果

详见真机预检日志。

| 测试项 | 结果 |
|--------|------|
| RARGetDllVersion == 8 | 待真机验证 |
| RAROpenArchive 缺失文件 EOPEN | 待真机验证 |
| RAROpenArchiveEx 缺失文件 EOPEN | 待真机验证 |

## 验证安装

```bash
ls <package>/lib/libclamunrar.so*
ls <package>/include/dll.hpp
./test_libclamunrar  # 期望输出 ALL 3 CONSUMER CHECKS PASSED
```

## 参考资料

- https://github.com/Cisco-Talos/clamav/tree/clamav-1.4.4/libclamunrar
- https://github.com/Cisco-Talos/clamav/blob/clamav-1.4.4/libclamunrar/CMakeLists.txt
- https://tracker.debian.org/pkg/libclamunrar
