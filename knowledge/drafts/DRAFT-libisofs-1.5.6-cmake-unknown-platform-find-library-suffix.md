# DRAFT — libisofs 1.5.6: CMake 不识别 HarmonyOS 导致 CMakeDeps find_library 找不到静态库

> 与 `DRAFT-libisofs-1.5.6-cmake-unknown-platform-find-library-suffix.kv` 配对（同 stem）。
> 路径 B（new_draft）：无等价命中且可跨库复用的候选经验。

## 问题

在 HarmonyOS PC（aarch64）上使用 Conan 2 的 CMakeDeps 消费静态库配方时，
`conan create` 的 test_package 阶段在 CMake configure 时失败：

```
CMake Error at build/clang-15-armv8-17-release/generators/cmakedeps_macros.cmake:81 (message):
  Library 'libisofs' not found in package.  If 'libisofs' is a system
  library, declare it with 'cpp_info.system_libs' property
```

库文件本身已正确安装于包内 `lib/libisofs.a`（`ar archive`，2546840 字节，内容有效），
`cpp_info.libs = ["libisofs"]` 声明无误，include 目录也正常，唯独
CMakeDeps 的 `conan_package_library_targets()` 里 `find_library` 找不到它。

## 根因

CMake 没有 `Platform/HarmonyOS.cmake` 平台模块。当 `CMAKE_SYSTEM_NAME` 被识别为
HarmonyOS 时（配置日志出现 "System is unknown to cmake, create: Platform/HarmonyOS"），
CMake 不加载任何平台的默认 `CMAKE_FIND_LIBRARY_SUFFIXES`/`CMAKE_FIND_LIBRARY_PREFIXES`
（Linux 平台会提供 `.so;.a` 等后缀，Windows 提供 `.lib/.dll`）。

CMakeDeps 的 `cmakedeps_macros.cmake` 在 `conan_package_library_targets()` 中通过
`find_library(CONAN_FOUND_LIBRARY NAMES ${_LIBRARY_NAME} PATHS ${package_libdir}
NO_DEFAULT_PATH NO_CMAKE_FIND_ROOT_PATH)` 定位库文件。由于后缀集合为空，
`find_library` 无法匹配 `libisofs.a`，返回 NOTFOUND，宏随即 `message(FATAL_ERROR ...)`。

与既有条目区分：
- **E092**：CMake unknown platform 导致平台宏/工具链检测失败（check_c_source_compiles 等）——方案是 -DCMAKE_SYSTEM_NAME=Linux 或 toolchain 覆盖；不涉及 find_library 后缀。
- **DRAFT-tinyspline-0.6.0-cmake-libdir64-cmakedeps**：同为 "Library not found in package"，但根因是 GNUInstallDirs 选 lib64 与 Conan 默认 lib/ 不一致——方案是 cache_variables 强制 libdir；不涉及 unknown platform 后缀。
- 正式图谱（graph/E*.kv）无任何 `CMAKE_FIND_LIBRARY_SUFFIXES` 条目。

## 触发条件

- HarmonyOS PC / OHOS 平台（CMake 不识别，无 Platform/HarmonyOS.cmake）
- Conan 2 + CMakeDeps 生成器消费**静态库**（.a；共享库 .so 同样受影响，因后缀集为空）
- test_package 或消费者 CMake 项目使用 `find_package(<pkg> REQUIRED)` 的 CMakeDeps target

## 方案

在 test_package（或消费者）CMakeLists.txt 中，`find_package(<pkg> REQUIRED)` **之前**
显式声明 HarmonyOS 下 find_library 的前缀/后缀：

```cmake
if(CMAKE_SYSTEM_NAME MATCHES "HarmonyOS|OHOS")
    set(CMAKE_FIND_LIBRARY_SUFFIXES ".so" ".a" )
    set(CMAKE_FIND_LIBRARY_PREFIXES "lib" "" )
endif()
```

libisofs 1.5.6 实测：添加后 test_package 的 configure → build → test 全部通过，
`conan-verify` G2/G3/G4 通过。

## 验证

```bash
conan create archives/l/libisofs/1.5.6 -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
# 修复前：test_package configure 报 Library 'libisofs' not found in package
# 修复后：configure/build/test 全过，conan-verify 全绿
```

## 适用边界

- 适用于 CMakeDeps 消费场景；若消费者手动 `find_library` + 显式 PATHS，同样需要后缀集。
- 纯头文件库（header-only）无 find_library，不受影响。
- 反例：将 `CMAKE_SYSTEM_NAME` 设为 `Linux` 伪装平台——会加载 Linux 平台逻辑
  （systemd/dbus/X11 探测），对纯 POSIX 库可能无害，但平台集成类项目会引入错误
  依赖，且 W4 审计视为平台身份伪装，禁止。

## 反例与限制

- `set(CMAKE_SYSTEM_NAME "Linux")`：平台伪装，禁止（见 forbid_1）。
- 依赖传递元数据：若在 test_package 手动 find_library 并直接链接绝对路径，
  会丢失 CMakeDeps target 携带的 INTERFACE_LINK_LIBRARIES 传递依赖
  （本库无 Conan 依赖，未暴露此问题；有依赖的库需用 target 方式或显式补全）。

## 查重差异

- 与 E092：E092 管 unknown platform 的配置/检测失败（toolchain、check_c_source_compiles），
  本条目管 CMakeDeps find_library 后缀缺失导致的消费者配置失败；触发工具与修复面不同。
- 与 DRAFT-tinyspline：tinyspline 是 libdir 布局不匹配（lib64 vs lib），
  本条目是 unknown platform 导致后缀集为空；修复位置不同（配方 generate vs 消费者 CMakeLists）。
- 正式图谱无 CMAKE_FIND_LIBRARY_SUFFIXES / find_library 后缀相关条目。

## 源证据

- 库：libisofs 1.5.6（task libisofs-1.5.6-r01-bootstrap-and-adapt-pc1-49-20260906T150459Z）
- 失败日志：`archives/l/libisofs/1.5.6/reports/conan-create.log`（"Library 'libisofs' not found in package"）
- 修复文件：`archives/l/libisofs/1.5.6/test_package/CMakeLists.txt`
- 最小复现实验：`find_library` 在无后缀集时返回 NOTFOUND，声明 `.so;.a` 后找到 `libisofs.a`
