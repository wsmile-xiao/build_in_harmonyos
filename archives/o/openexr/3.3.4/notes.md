# openexr 3.3.4 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-10
- 编译器: clang/clang++（OHOS SDK 15，aarch64-linux-ohos triplet）
- 状态: built

## 源码信息
- 上游: https://github.com/AcademySoftwareFoundation/openexr（tag v3.3.4）
- 源码: GitHub 官方 release tarball `openexr-3.3.4.tar.gz`
- sha256: `73a6d83edcc68333afb95e133f6e12012073815a854bc41abc1a01c1db5f124c`（本地下载实测与 conandata.yml 一致）

## 依赖版本
- imath/3.2.2（本仓库制品仓已发布，包名小写 imath；transitive_headers=True——OpenEXRCore 的 openexr_config.h 直接 `#include <ImathConfig.h>`）
- libdeflate/1.22（本仓库制品仓已发布；上游 OpenEXR 3.3.4 默认外部 libdeflate，找不到才 FetchContent 内嵌 v1.18）
- 说明：上游 find_package(Imath) 找不到时同样会 FetchContent 拉 v3.1.12 源码——CI 无网络，两者都必须走 conan 依赖并确保 CMake CONFIG 命中

## 编译步骤
conan create（ci/conan/profiles/ohos-aarch64，CMakeToolchain 自动映射 CMAKE_SYSTEM_NAME=HarmonyOS）：
- BUILD_TESTING=OFF（与 conan-center-index 3.x 官方配方口径一致，测试套不在 conan 包产物中，上游测试独立执行见下）
- OPENEXR_BUILD_TOOLS=ON / OPENEXR_BUILD_LIBS=ON
- BUILD_SHARED_LIBS=ON（默认动态，非系统同名库，Conan 管理依赖链）
- OPENEXR_FORCE_INTERNAL_DEFLATE=OFF（走外部 libdeflate/1.22）

产物组件：libIex / libIlmThread / libOpenEXRCore / libOpenEXR / libOpenEXRUtil（so 命名带 -3_3 后缀）+ exrinfo 等 9 个命令行工具 + OpenEXR cmake config 导出（OpenEXR::OpenEXR 等 8 个 target）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | OpenEXRCore 编译报 `openexr_config.h:12:10: fatal error: 'ImathConfig.h' file not found` | 上游 ImathConfig 组件安装接口同时暴露 `include/` 与 `include/Imath`（见上游 ImathTargets.cmake 的 `Imath::ImathConfig INTERFACE_INCLUDE_DIRECTORIES`），而本仓库 imath/3.2.2 配方 cpp_info 只声明 `include/`，CMakeDeps 生成的 ImathConfig.cmake 缺 `include/Imath` 目录 | 在 openexr 配方 generate() 里给 imath 依赖的**组件级** includedirs 追加绝对路径 `.../include/Imath`（对齐上游安装口径；注意：①必须用绝对路径，相对路径会被丢弃 ②包级修改不传导到组件，必须直接改 components ③必须在 CMakeDeps 构造前完成）。test_package 消费侧同款补丁 |
| 2 | 上游 OpenEXRSetup.cmake 的 libdeflate 探测只认 `libdeflate::libdeflate_shared` / `libdeflate::libdeflate_static` 目标名 | Conan CMakeDeps 默认组件目标名为 `libdeflate::libdeflate`，上游分支逻辑对不上号时会回退 FetchContent（CI 无网络必挂） | `deps.set_property("libdeflate", "cmake_target_name", "libdeflate::libdeflate_shared")` 对齐目标名，实测走外部 libdeflate/1.22 |
| 3 | 库间 NEEDED 记录为构建树相对路径（`../IlmThread/libIlmThread-3_3.so`），安装到平铺 lib/ 后加载器找不到 | CMake 对 HarmonyOS 平台无专属 platform module，不生成 SONAME 链接参数（Linux 上会传 `-Wl,-soname,libxxx.so.<SOVERSION>`） | generate() 显式注入 `CMAKE_SHARED_LIBRARY_SONAME_C_FLAG/CXX_FLAG="-Wl,-soname,"`，库间 NEEDED 变为标准 `libIlmThread-3_3.so.32` |
| 4 | 上游测试套 mkdir `/var/tmp/OpenEXRTest_*` 失败（errno=2） | OHOS 设备 /var 只读、/var/tmp 不存在；上游 tmpDir.h 硬编码 POSIX 分支 `/var/tmp/` | 0001-ohos-test-tmpdir.patch：POSIX 通用方案（无平台宏）——运行时 `imf_tmp_dir()` 优先解析 IMF_TMP_DIR/TMPDIR 环境变量，回退上游默认 /var/tmp/（Linux 行为完全兼容）；OHOS 等只读平台导出 `TMPDIR=$HOME/tmp` 即可运行测试套。测试断言与逻辑零改动，库本体不受影响 |
| 5 | 测试二进制运行报 `libc++_shared.so` not found | musl 加载器默认搜索路径不含 /system/lib64 | test() 里 `Environment().define("LD_LIBRARY_PATH", "/system/lib64")`（同 archives/d/date/3.0.5 先例） |
| 6 | OpenEXRCore 消费者编译缺 Imath 头（test_core.c 编译失败） | 上游 OpenEXRCore 的 Imath::Imath 是 PUBLIC 依赖（openexr_config.h 公开包含 ImathConfig.h），初版 package_info 组件 requires 漏了 imath | OpenEXRCore 组件 requires 补 `"imath::imath"` |

## 上游测试执行情况（N = 上游 CMake 注册数）

上游 BUILD_TESTING=ON 时注册的 add_test 测试目标（ctest -N 实测）：
- OpenEXRCore 套：60 项
- OpenEXR C++ 主套：58 项（ctest -N 实测；源码 define 列表 63 个中部分被条件门控未注册）
- OpenEXRUtil 套：3 项
- OpenEXR.bin 工具套：12 项（Python3 驱动 + openexr-images v1.0 在线图）
- Iex 套：1 项
- examples：1 项
- **合计注册数 N = 135**（Fuzz 4 项被上游 OPENEXR_RUN_FUZZ_TESTS=OFF 默认门控，不在默认注册口径）

本地实测执行：**135/135 通过（100%），总耗时 286s**，无豁免项。明细见 reports/test-report.md。

## 源码修改
patches/0001-ohos-test-tmpdir.patch（上游测试临时目录 POSIX 通用适配，见问题 4；无平台条件宏，Linux 行为不变，库本体与 BUILD_TESTING=OFF 构建不受影响）。

## 验证结果
- conan create（ohos-aarch64 profile）：通过（patch 应用 + 主包构建 + test_package 全绿）
- test_package（消费者视角）：test_openexr + test_core 双 OK
- 上游测试套：135/135（100%），详见 reports/test-report.md

## 注意事项
- imath 依赖必须 `transitive_headers=True`：OpenEXRCore 的公开头直接包含 ImathConfig.h
- 后续 openvdb 适配消费本包时，用 `OpenEXR::OpenEXR` / `OpenEXR::OpenEXRUtil` cmake target（find_package(OpenEXR CONFIG)）；imath includedirs 缺 include/Imath 的问题在消费侧 generate() 需同款补丁（见问题 1——imath/3.2.2 配方缺陷，待 imath 侧后续版本修复）
- 本包非系统同名库，默认动态链接，RPATH 由 Conan 管理
- 测试图 openexr-images v1.0 共 16 张需在线下载（bin 套件），本机已全量 md5 校验；CI 构建 BUILD_TESTING=OFF 不涉及
