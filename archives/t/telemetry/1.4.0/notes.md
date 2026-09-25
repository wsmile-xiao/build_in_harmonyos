# telemetry 1.4.0 适配笔记

## 编译环境
- 构建系统: cmake (CMake >= 3.18, C++20)
- 编译日期: 2026-09-24
- 编译器: clang / clang++ 15.0.4 (OHOS SDK 26.0.0.18, libc++), lld 15.0.4
- profile: ohos-aarch64 (os=OHOS 6.0 / arch=armv8 / clang 15 / libc++ / cppstd17→20)
- 状态: built

## 上游身份
- 上游: https://github.com/CESNET/telemetry (Debian 源码包 telemetry 1.4.0-4 的 Homepage 同源)
- tag `v1.4.0` → commit `33287a91b344cc54af1a52ac091fd18b234b50bf` (release 2025-11-10)
- 源码: https://github.com/CESNET/telemetry/archive/refs/tags/v1.4.0.tar.gz
  sha256 = `aa7c0b457f507924a1b5ebd9df8b80db02fabb61b13f035ef803489b51d057d0`
- 产物: `libtelemetry.so.1.4.0` (核心库) + `libappFs.so.1.4.0` (FUSE3 文件系统视图) + 公共头

## 编译步骤

```bash
# 依赖 (W0 已用 conan download 验证可消费)
conan download libfuse/3.18.2 -r=ohpcd --only-recipe     # exit 0
conan download gtest/1.17.0.2 -r=ohpcd --only-recipe     # exit 0 (上游测试用)
# 配方内: PkgConfigDeps 生成 fuse3.pc; CMakeToolchain 注入 PKG_CONFIG_PATH
python3 scripts/ohc-run.py build telemetry 1.4.0
# 等价手工步骤: cmake(TELEMETRY_ENABLE_TESTS=ON) → make → ctest → install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `Failed to clone repository: 'https://github.com/google/googletest.git'`（configure 阶段，FetchContent） | 上游 `cmake/googletest.cmake` 用 FetchContent 拉 googletest v1.14.0；本环境 github.com:443 不可达，且制品仓无 googletest 1.14.0 | 补丁 0001：`find_package(GTest QUIET)` 优先，只有找不到外部 GTest 时才回退 FetchContent；配方 `test_requires("gtest/1.17.0.2")` + `GTest_DIR` |
| 2 | `src/telemetry/node.cpp:63: error: no member named 'find_if_not' in namespace 'std::ranges'` | OHOS SDK 的 libc++ 15 未实现 `std::ranges` 算法 | 补丁 0005：改用 `<algorithm>` 的 `std::find_if_not(name.begin(), name.end(), ...)` |
| 3 | `src/telemetry/aggFile.cpp:93,97: error: no member named 'any_of' in namespace 'std::ranges'` | 同上 | 补丁 0004：改用 `std::any_of(ops.begin(), ops.end(), ...)` |
| 4 | `ld.lld: error: unable to find library -lstdc++fs` | `src/appFs/CMakeLists.txt` 无条件链接 `stdc++fs`（GCC 的 std::filesystem 运行库）；libc++ 把 `std::filesystem` 放在主 C++ 运行库中，SDK 内不存在 `libstdc++fs` | 补丁 0002：仅当 `CMAKE_CXX_COMPILER_ID STREQUAL "GNU"` 时才链接 `stdc++fs` |
| 5 | `ld.lld: error: libfuse3.a(fuse.c.o): symbol fuse_new@FUSE_3.0 has undefined version FUSE_3.0` | 依赖包 `libfuse/3.18.2` 是**静态库**且带 `--version-script`（FUSE_3.0…FUSE_3.17 版本节点）。版本节点只在链接 libfuse 自身时生成，把该静态归档链接进共享库时 lld 要求节点存在 | 补丁 0002：`get_target_property(... PkgConfig::fuse INTERFACE_LINK_LIBRARIES)` 检测到 `.a` 时加 `-Wl,--exclude-libs,libfuse3.a`，把归档符号从动态符号表隐藏（`--undefined-version` 对 lld 15 无效；GNU ld 同样失败） |
| 6 | `cmake --install --prefix ...` 安装到 `/usr/local/lib`（无权限，失败） | `cmake/installation.cmake` 在 configure 阶段用 `GNUInstallDirs` 的 `CMAKE_INSTALL_FULL_LIBDIR`（绝对路径），`--prefix` 不生效 | 配方 generate()：`LIB_INSTALL_DIR=lib` + `INCLUDE_INSTALL_DIR=include`（上游为 RPM 打包预留的覆盖变量），安装路径改为相对 package_folder |
| 7 | 产物无 `DT_SONAME`，且 `libappFs.so` 的 `DT_NEEDED` 是相对路径 `../telemetry/libtelemetry.so`（L5a/L5b 门禁会拦截） | OHOS 的 CMake 平台模块只定义 `CMAKE_SHARED_LIBRARY_SONAME_C_FLAG`，未定义 CXX 变体，CMake 直接丢弃 `-soname`；配 `SOVERSION` 也无效 | 补丁 0002/0003：给两个库设置 `VERSION/SOVERSION`；配方 generate() 注入 `CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG/C_FLAG=-Wl,-soname,` → `SONAME=libtelemetry.so.1` / `libappFs.so.1` |

## 源码修改（5 个补丁，见 conandata.yml）

| 补丁 | 文件 | 内容 |
|------|------|------|
| 0001 | cmake/googletest.cmake | 外部 GTest 优先（Conan gtest），FetchContent 仅作回退 |
| 0002 | src/appFs/CMakeLists.txt | `stdc++fs` 仅 GCC；静态 libfuse3.a 符号隐藏；`SOVERSION` |
| 0003 | src/telemetry/CMakeLists.txt | `VERSION/SOVERSION`（DT_SONAME） |
| 0004 | src/telemetry/aggFile.cpp | `std::ranges::any_of` → `std::any_of` |
| 0005 | src/telemetry/node.cpp | `std::ranges::find_if_not` → `std::find_if_not` |

> 补丁不含任何平台宏（无 `__OHOS__`），全部为编译器/依赖形态的可移植性修复，GCC + 共享 libfuse 的常规环境仍按上游路径工作。

## 依赖版本

- `libfuse/3.18.2`（直接依赖，满足上游 `fuse3>=3.2.1`；pkg-config 名字 `fuse3`，静态库）
- `gtest/1.17.0.2`（仅测试，`test_requires`；替代上游 FetchContent 的 googletest v1.14.0）
- 系统/工具链自带: pthread、libc++（不再使用 `stdc++fs`）

## 验证结果

```bash
# 上游测试（build() 内执行，57 个用例）
ctest --test-dir <build> --output-on-failure
100% tests passed, 0 tests failed out of 57          # 见 reports/test-report.md
# 消费端测试（test_package，2 个用例）
ctest → test_telemetry_consumer / test_appfs_ohos    # 100% passed
# SONAME
readelf -d libtelemetry.so.1.4.0 | grep SONAME      # libtelemetry.so.1
readelf -d libappFs.so.1.4.0     | grep SONAME      # libappFs.so.1
readelf -d libappFs.so.1.4.0     | grep NEEDED      # libtelemetry.so.1 / libc++_shared.so / libc.so
```

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libtelemetry.so.1.4.0 | 核心遥测库（SONAME libtelemetry.so.1） |
| lib/libappFs.so.1.4.0 | FUSE3 文件系统视图库（SONAME libappFs.so.1，静态吸收 libfuse3.a） |
| include/ | appFs.hpp + telemetry*.hpp（公共头，含 `include/telemetry/`） |
| 无 bin/ | 上游不产出可执行文件，故不声明 commands.json（R38 不适用） |

## 注意事项

- 运行期挂载 FUSE 需要 `/dev/fuse`，属鸿蒙沙箱平台能力问题，不影响编译/打包/链接（test_package 中仅作信息性探测）。
- `libappFs.so` 已静态吸收 libfuse3.a（上游 libfuse 只发布静态包），因此下游运行时不需要 `libfuse3.so`；`cpp_info.requires` 仍保留 `libfuse::libfuse` 以提供 `fuse3/fuse.h` 头文件。
- 消费端需要 `FUSE_USE_VERSION=30` 与 `_FILE_OFFSET_BITS=64`（上游 appFs 的 PUBLIC 编译定义），配方通过 `cpp_info.defines` 传递。
---

**编译结束**: 2026-09-24 15:34
**最终状态**: built
