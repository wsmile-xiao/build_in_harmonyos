# DRAFT: libqtxdg (qtxdg) 3.12.0 —— Qt5 Conan 配置缺口 + 非 PIC 静态库强制 STATIC

> 配套条目：`knowledge/drafts/DRAFT-qtxdg-qt5-conandeps-ohos-nonpic-static.kv`
> 状态：草稿（待主编审核）；关联软件：qtxdg（libqtxdg / Qt5Xdg）3.12.0

## 一句话

把 CMake + Qt5 的 C/C++ 库适配到 HarmonyOS PC 时，会遇到两类系统性问题：
**(A)** qt5-qtbase 包内原生 Qt5 umbrella 配置不可重定位、Conan CMakeDeps 又不产出
Qt5 的宏/私有头/大写 `GLIB_*` 变量；**(B)** 制品仓的 zlib/glib 只有非 PIC 静态库，
无法链进共享库。

## 典型报错

```
ld.lld: error: relocation R_AARCH64_ADR_PREL_PG_HI21 cannot be used against
               symbol 'z_errmsg'; recompile with -fPIC
               >>> defined in .../zlib/.../lib/libz.a
Could NOT find GLIB (missing: GLIB_GIO_UNIX_INCLUDE_DIR)
Target "Qt5XdgIconLoader" links to: Qt5::Svg but the target was not found
fatal error: 'gio/gio.h' file not found
```

## 处置要点（qtxdg 3.12.0 实测）

| # | 问题 | 处置 |
|---|------|------|
| 1 | 非 PIC 静态 zlib/glib 不能进 `.so` | 目标库改 **STATIC**（同 quazip 先例）；PIC 模块（插件）里把 `zlib::zlib` 置空 + `set(zlib_FOUND TRUE)` |
| 2 | 原生 Qt5 config 不可重定位 | 不用原生 config；改用 Conan CMakeDeps 目标 |
| 3 | CMakeDeps 缺 Qt5 宏/私有头 | 生成 `CMAKE_PROJECT_INCLUDE` shim：moc/rcc/qdbusxml2cpp 路径、`Qt5Core\|Qt5Gui_PRIVATE_INCLUDE_DIRS`、`include(Qt5CoreMacros.cmake/Qt5DBusMacros.cmake)`、`mkspecs/linux-clang` |
| 4 | `find_package(Qt5 COMPONENTS ...)` 拿不到 `Qt5::Svg` | 补 `find_package(qt5-qtsvgv CONFIG REQUIRED)` |
| 5 | `CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON` 让 `glib-config.cmake` 抢占 `FindGLIB.cmake`，大写 `GLIB_INCLUDE_DIRS` 为空 | `deps.set_property("glib","cmake_find_mode","none")` |
| 6 | FindGLIB 的 `gio-unix` 组件缺 pc | 生成 `gio-unix-2.0.pc` |
| 7 | 消费者链接静态 Qt5Xdg 缺 glib 传递归档 | 把 `libffi/libgmodule/libintl/libpcre2-8/libz` 注入 PUBLIC 接口 |
| 8 | 上游硬依赖未发布的 `lxqt-build-tools` | 配方自带官方源码，build() 内先装到子前缀（其 config 追加 `CMAKE_MODULE_PATH`）；配置它用 `Qt5CoreConfig.cmake` 桩 |
| 9 | 上游测试硬编码 `/tmp`（OHOS 只读） | 补丁改 `QDir::tempPath()`；ctest 注入可写 `TMPDIR` |

## 证据

- `conan create`（ohos-aarch64）成功；build() 内 `ctest` **3/3** 通过；test_package **15/15** 断言通过。
- W3 `finish`：JC 0，`L0_RESULT=pass`、`L1_RESULT=pass`（L1a–L1e），`.ci-result.json exit_code=0`。
