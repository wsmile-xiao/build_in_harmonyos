# libheif-dav1d

libheif 的 **AV1 解码插件**（dav1d 后端）子包。

## 是什么

上游 libheif 把每个编解码后端做成「内置 / 独立插件」双形态：顶层
`CMakeLists.txt` 的 `plugin_option(<NAME> <说明> <默认启用> <默认插件>)`
同时派生 `WITH_<NAME>` 与 `WITH_<NAME>_PLUGIN` 两个开关。当
`ENABLE_PLUGIN_LOADING=ON` 且 `WITH_<NAME>_PLUGIN=ON` 时，
`libheif/plugins/CMakeLists.txt` 的 `plugin_compilation()` 走
`add_library(heif-<name> MODULE ...)` 分支，产出 `libheif-<name>.so`
并安装到 `<libdir>/libheif/`；否则后端源码被编进 `libheif.so` 本体。

本包固定这一形态：**只开 dav1d（AV1 解码），且以独立插件交付**，
其余后端全部显式 OFF。因此它给出的是「libheif + AV1 解码能力」的
最小自包含安装树，而不是另造一个 libheif 变体名称。

## 交付物

| 路径 | 说明 |
|---|---|
| `lib/libheif/libheif-dav1d.so` | 本包主交付物：AV1 解码插件（MODULE） |
| `lib/libheif.so*` | 插件宿主 libheif（插件 `target_link_libraries(... heif)`，脱离宿主不可用） |
| `include/libheif/*.h` | 公开 C API 头文件 |
| `lib/pkgconfig/libheif.pc` | pkg-config 元数据 |

插件目录在 configure 期被烧进 `heif_version.h` 的
`LIBHEIF_PLUGIN_DIRECTORY` 宏（= `<prefix>/lib/libheif`），
libheif 在 `heif_init()` 时按它扫描并 `dlopen` 所有 `*.so`。

## 依赖

- **dav1d/1.5.0** —— 唯一直接依赖，来自仓库既有独立包
  `archives/d/dav1d/1.5.0`（外部包，非内树捆绑）。
  上游用 `find_package(DAV1D)` → `libfind_pkg_check_modules(DAV1D_PKGCONF dav1d)`
  发现它，需要 `dav1d/dav1d.h` + `libdav1d` + `dav1d.pc`。

上游树内**没有** dav1d 源码副本，因此不存在「内树构建 dav1d」这条路。

## OHOS 适配要点

1. **插件是 `dlopen` 对象 → 必须代码签名**。鸿蒙 PC XPM 要求被
   `dlopen` 的 `.so` 带有效 `.codesign` 段，而 `cmake install` 的复制会
   破坏链接器自签，故配方在 `package()` 内装包后重签
   （`llvm-objcopy --remove-section .codesign` → `binary-sign-tool -selfSign 1`）。
2. **不要手工注入 `PKG_CONFIG_PATH`**。`CMakeToolchain` 默认带
   `PkgConfigBlock`，会把 generators 目录前置进 `ENV{PKG_CONFIG_PATH}`；
   只要 `generate()` 里调过 `PkgConfigDeps(self).generate()`，
   `FindDAV1D.cmake` 的 `pkg_check_modules` 就能命中 `dav1d.pc`。
3. **`WITH_REDUCED_VISIBILITY` 保持上游默认 ON**。它与交付面无关，
   改动它只会让一部分上游单元测试能编译，属于「为凑数字放开无关开关」。

## 版本

| 版本 | 状态 | 备注 |
|------|------|------|
| 1.23.0 | built | dav1d 1.5.0 后端；AV1 解码插件形态 |

## 同族子包

同一父 tarball（libheif 1.23.0）下按后端拆分：
`libheif-libde265` / `libheif-openh264` / `libheif-openjpeg` /
`libheif-svtenc` / `libheif-aom` / `libheif-jpeg` / 本包。
各包彼此独立，不互相依赖。

## 相关链接

- 官网：https://github.com/strukturag/libheif
- 源码：https://github.com/strukturag/libheif/releases
