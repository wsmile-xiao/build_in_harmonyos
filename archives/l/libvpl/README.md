# libvpl (Intel oneVPL dispatcher)

Intel® Video Processing Library（oneVPL）的**派发库**：实现完整的 MFX API（1.x 与 2.x），
在运行时 `dlopen` 具体的运行时实现（oneVPL GPU runtime、legacy MSDK `libmfxhw64`/`libmfxsw64`）
并把调用转发过去。库本身不含任何编解码实现。

## 功能概述

- **API 2.x loader**：`MFXLoad` / `MFXCreateConfig` / `MFXSetConfigFilterProperty` /
  `MFXEnumImplementations` / `MFXDispReleaseImplDescription` / `MFXCreateSession` / `MFXUnload`
- **API 1.x 兼容层**：`MFXInit` / `MFXInitEx` / `MFXQueryVersion` / `MFXClose` 以及
  `MFXVideoDECODE_*` / `MFXVideoENCODE_*` / `MFXVideoVPP_*` / `MFXVideoCORE_*` 全套入口
- **运行时发现顺序**：`ONEVPL_SEARCH_PATH` → `libvpl.so` 所在目录 → 编译期
  `MFX_MODULES_DIR`（= 包内 `lib/`）→ 系统默认库目录
- **ABI 稳定**：`-Wl,--version-script=libvpl.map` 导出 `LIBVPL_2.0` / `LIBVPL_2.1` 两个版本节点
- 交付物：`libvpl.so.2.16`（SONAME `libvpl.so.2`）、`vpl/*.h`、`VPLConfig.cmake`、`vpl.pc`

## OHOS 适配

**关键点：`CMAKE_SYSTEM_NAME=OHOS` 必须显式设置。**

`libvpl/CMakeLists.txt` 把 Linux 派发的核心实现（以及它需要的平台语义）放在 `if(UNIX)` 内，
而 version script 放在 `if(WIN32)` 的 `else()` 分支、`${CMAKE_DL_LIBS}` 的链接放在 `if(UNIX)`
之外（两者都**不受** `UNIX` 影响）：

```cmake
if(UNIX)
  set(SOURCES src/linux/mfxloader.cpp)          # MFXInit/MFXInitEx/MFXQueryVersion + 1.x 转发
  add_definitions(-DMFX_MODULES_DIR="...")
endif()
...
if(WIN32)
  ...
else()
  # use version script on Linux
  set_target_properties(VPL PROPERTIES LINK_FLAGS
    "-Wl,--version-script=${CMAKE_CURRENT_SOURCE_DIR}/src/linux/libvpl.map")
endif()
...
target_link_libraries(VPL PRIVATE ${CMAKE_DL_LIBS})   # 无条件；CMAKE_DL_LIBS 由 Platform/GNU.cmake 兜底
...
if(UNIX)
  find_package(Threads REQUIRED)                # Threads 查找与 -pthread 链接在此块内
endif()
```

CMake 没有 `Platform/HarmonyOS.cmake`，而 Conan 对 `os=OHOS` 的默认系统名与本设备
`uname -s`（`HarmonyOS`）都落到这个不存在的平台文件上：`CMAKE_SYSTEM_NAME` 为空或不可识别、
**`UNIX` 为假**，于是 `mfxloader.cpp` 不进入构建图、`MFX_MODULES_DIR` 未定义、Threads 与
`-pthread` 链接一并跳过，`DT_SONAME` 也丢失（`CMAKE_SHARED_LIBRARY_SONAME_<LANG>_FLAG`
由 `Platform/Linux.cmake` 定义）—— 产物只导出 7 个 2.x loader 符号，1.x 全量 API（`MFXInit`
等 52 个符号）**静默缺失**。CMake 只会打印三行 `System is unknown to cmake`，退出码 0，因此容易漏判；
version script 本身仍然生效，只是仅覆盖存活的那 7 个符号（实测破损产物仍带 `LIBVPL_2.0`/`LIBVPL_2.1`
版本节点，但无 `DT_SONAME`）。

配方在 `generate()` 中显式指定平台真名 `CMAKE_SYSTEM_NAME=OHOS`：SDK 随带
`Modules/Platform/OHOS.cmake`（内容为 `include(Platform/Linux)`），`UNIX=1`，完整派发库（59 个导出符号）、
`DT_SONAME` 与覆盖全 API 的 version script 均就位。**不需要任何源码补丁**，也不需要把平台伪装成
Linux（仓库内同口径先例：`archives/d/demumble`、`archives/d/dbus`）。

回归判定：`test_package/test_libvpl_ohos.c` 直接调用 `MFXInit`/`MFXInitEx`/`MFXQueryVersion`/`MFXClose`，
一旦 UNIX 分支再次丢失，L1 消费者会在**链接期**失败（符号不存在），比统计导出符号更早暴露。

其余平台事实：

- OHOS 无 Intel 运行时，运行期枚举必然返回 `MFX_ERR_NOT_FOUND`（`MFXInit`/`MFXInitEx` 返回
  `MFX_ERR_UNSUPPORTED`）。这是平台限制，不是适配缺陷。
- `examples/` 需要真实 Intel GPU，适配中关闭（`BUILD_EXAMPLES=OFF`、`INSTALL_EXAMPLES=OFF`）。
- 上游测试自带 vendored googletest 与 `stub`/`stub1x`/`stub-nofn` 三个 in-tree 运行时，
  可离线跑完 1014 项可执行用例（707 PASS / 307 SKIP）。

## 依赖关系

- **编译依赖**：无第三方库；只需 CMake + C++17 编译器（OHOS SDK clang）。
- **运行依赖**：`libc++_shared`、`libdl`、`libpthread`；实际编解码能力取决于运行时实现，
  OHOS 上不存在 Intel 运行时。

## 参考资料

- 上游仓库：<https://github.com/intel/libvpl>
- 版本：`v2.16.0`（`version.txt` = 2.16.0；API `MFX_VERSION_MAJOR/MINOR` = 2/16）
- 安装说明（上游）：`INSTALL.md`、`script/build`、`script/test`
