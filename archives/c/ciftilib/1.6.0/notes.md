# ciftilib 1.6.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-08
- 编译器: clang 15.0.4 (OHOS SDK, aarch64-linux-ohos)
- 状态: built

## 编译步骤

```bash
# 获取源码 (conandata.yml URL 已含 gh-proxy 镜像回退)
get(CiftiLib-1.6.0.tar.gz, sha256 5df9c72...)

# 生成阶段
PkgConfigDeps  -> libxml++-2.6.pc / glibmm-2.4.pc / libxml-2.0.pc
CMakeDeps      -> boost, zlib 的 CMake 目标
CMakeToolchain -> IGNORE_QT=ON, BUILD_SHARED_LIBS=OFF, CMAKE_CXX_STANDARD=11

# 配置与构建
cmake -DIGNORE_QT=ON -DBUILD_SHARED_LIBS=OFF -DCMAKE_CXX_STANDARD=11 -DCMAKE_POLICY_VERSION_MINIMUM=3.5 <source>
cmake --build .
# 原生 OHOS 上运行上游测试
ctest --output-on-failure  # 35 tests (5 files x 7 variants)
cmake --install .
# 对 libCifti.so.* 重新签名 (binary-sign-tool, HarmonyOS 动态链接器要求)
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | FindQt5Core 误匹配导致走 QT 路径 | OHOS 已安装 qt5-qtbase (5.15.2) 会被 FIND_PACKAGE(Qt5Core) 命中，QT 路径需要 QtXml 但 OHOS 的 qt5 去掉了 xml 特性，链接失败 | CMakeToolchain 强制 `IGNORE_QT=ON` (bool TRUE)，CMakeLists 的 `IF(NOT IGNORE_QT)` 直接跳过 QT 分支，走 libxml++ |
| 2 | Findlibxml++ 找不到 libxml++-2.6.pc | PkgConfigDeps 默认把 .pc 生成到 generators 目录，但 CMake 的 pkg_check_modules 只查系统 PKG_CONFIG_PATH | generate() 中设置 `tc.variables["PKG_CONFIG_USE_CMAKE_PREFIX_PATH"]=False` 并在 build() 显式将 `PKG_CONFIG_PATH` 设为 `generators_folder` + 各依赖的 `lib/pkgconfig`，确保 `pkg_check_modules(PC_LIBXMLPP libxml++-2.6)` 成功 |
| 3 | profile cppstd=17 覆盖项目的 11，导致 auto_ptr 报错 | CiftiLib 仍使用 C++11 (std::auto_ptr)；profile 设为 17 会让 CMakeToolchain 写 `CMAKE_CXX_STANDARD=17` 覆盖项目的 11 | 在 CMakeToolchain 中强制 `CMAKE_CXX_STANDARD=11` + `CMAKE_CXX_STANDARD_REQUIRED=True` |
| 4 | ctest 加载共享库失败 (libxml++-2.6.so, libglibmm 等) | 测试二进制依赖的 .so 在 conan cache 中，不在系统 LD_LIBRARY_PATH | build() 中将所有依赖的 `lib` 目录 + `build_folder` 拼成 LD_LIBRARY_PATH，再执行 `cmake.test()` |
| 5 | HarmonyOS 上 .so 未签名导致 dlopen 失败 | OHOS musl 动态链接器拒绝加载 stripped/未签名共享库 (E215) | package() 末尾调用 `_sign_shared_libs()`，用 `llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign -selfSign 1` 重新签名 |
| 6 | meson/1.11.0.1 在远端不可解析 + /tmp 只读 | ohpcd/conancenter 连续缺 meson/1.11.0.1（graph 在 Computing dependency graph 阶段即失败），且 HMFS /tmp 为只读导致 mktemp 失败（E002） | 移除 tool_requires meson/ninja，改为 vendored meson（meson-vendor-global shim，下载 meson 1.11.2 官方源码到可写 TMPDIR，生成 /storage/.../tmp/hmbs-shims/meson 可执行 shim，复用 astroterm/1.0.9 已验证方案）+ pip fallback（_ensure_meson_in_path 使用 HMBS_TMPDIR/TMPDIR），ninja 复用 HMBS_BUILD_TOOLS |

## 源码修改

无源码补丁。适配全部通过 Conan 工具链参数完成，未修改上游源码。`patches: {}`。

## 依赖版本

- boost/1.91.0.1.1 (OHOS CMake 重打包，基于上游 1.91.0，提供 Boost.Filesystem 等；pin 至此版本以避开 conancenter 1.91.0 的 b2 配方在 OHOS 上缺 sysroot 导致 errno.h 缺失；复用 ohpcd 已发布的 OHOS 预编译 01d92cf...)
- libxmlpp/2.42.3 (OLD 2.6 API 线，pc 名称 `libxml++-2.6`，依赖 glibmm/2.66.9 + libxml2/2.15.3)
- zlib/1.3.1.1 (NIfTI gzip 支持，FindZLIB)

> 2026-09-09 修正1：上一轮 HMFS shim 仅解决 libffi 的 install/chmod，回放显示主失败已转移至 boost 的 b2/sysroot（conancenter 1.91.0 无 OHOS 二进制，预检回退源码编译失败），故本轮改 pin 至 ohpcd 独有的 1.91.0.1.1 CMake 包以直接复用二进制。
> 2026-09-09 修正2：真机 graph 解析失败 `meson/1.11.0.1: Unable to find in remotes` + /tmp 只读（`can't create temporary file /tmp/...: Read-only file system`，E002）。移除 `tool_requires meson/ninja`（graph 阻塞），改为 vendored meson（meson-vendor-global shim，astroterm/1.0.9 已验证，gh-proxy 镜像 + /storage/.../tmp 可写路径）+ pip fallback（_ensure_meson_in_path，TMPDIR/TMP/TEMP 注入），ninja 由 HMBS 提供（HMBS_BUILD_TOOLS），不再 pin。

## 验证结果

```bash
# 上游测试 (build() 中 ctest)
ctest --output-on-failure  # 35 tests: info/rewrite/datatype x 5 files
# 期望: 100% 通过 (libxml++ 路径的 md5 与 QT 路径不同，但同一路径内自洽)

# 消费者测试 (test_package)
./test_ciftilib
# 输出:
# === CiftiLib 1.6.0 consumer test ===
# AString round-trip: hello-cifti
# PASS: AString
# CiftiFile default constructed, ...
# PASS: CiftiFile default
# CiftiXML dimensions: 0
# CiftiVersion default: 2.0
# PASS: CiftiXML/CiftiVersion
# PASS: exception path
# === All ciftilib consumer checks passed ===
```

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libCifti.a (或 libCifti.so.0) | 静态库为主 (BUILD_SHARED_LIBS=OFF 默认) |
| include/CiftiLib/CiftiFile.h, NiftiIO.h, Cifti/*, Common/*, Nifti/* | 头文件树 |
| lib/pkgconfig/CiftiLib.pc | pkg-config 文件 (Requires: libxml++-2.6) |

## 注意事项

- 默认静态库 (`shared=False`) 以避免 HarmonyOS 上 libCifti.so 的 SONAME/symlink 与 HMDFS 的兼容问题；如需共享库，可 `-o ciftilib/*:shared=True`。
- 依赖的 libxmlpp/2.42.3 为 2.6 API 线，与 OHOS 上 5.x 线的 libxml++/5.4.0 不兼容，切勿替换为 5.x。
