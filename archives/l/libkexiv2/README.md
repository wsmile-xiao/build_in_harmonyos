# libkexiv2

KDE 对 [Exiv2](https://exiv2.org/) 的封装库（KDE Gear 组件，上游 project version 5.1.0）。
提供 `KExiv2` 类：以 Qt/QImage 友好的接口读写图片的 EXIF / IPTC / XMP 元数据，
含 XMP sidecar、缩略图、GPS、评论等辅助能力。构建产物为 `libKExiv2Qt6.so`。

- 上游：https://invent.kde.org/graphics/libkexiv2
- 源码包：https://download.kde.org/stable/release-service/26.04.0/src/libkexiv2-26.04.0.tar.xz
- 许可证：BSD-3-Clause AND GPL-2.0-or-later

## HarmonyOS PC 适配说明

| 项 | 说明 |
|---|---|
| 源码补丁 | 无（`patches_applied: []`），保持上游 26.04.0 原样 |
| 依赖解析 | 不使用 CMakeDeps：qtbase 打包为 `cmake_find_mode=none`（自带完整 Qt6Config.cmake），exiv2 走包内上游 `exiv2Config.cmake`（定义 `Exiv2::exiv2lib`）。`conan_cmakedeps_paths.cmake` 手工声明全部 host 依赖（含传递的 expat/zlib）的 `lib/cmake`、`lib`、`include` 搜索路径 |
| `CMAKE_FIND_PACKAGE_PREFER_CONFIG` | 刻意不设置。置 ON 时 exiv2 配置里 `find_dependency(EXPAT)` 会加载 conan 的 `expat-config.cmake`（只导出 `expat::expat`），导致 `Exiv2::exiv2lib` 的 `$<LINK_ONLY:EXPAT::EXPAT>` 闭包在 generate 阶段报目标不存在 |
| 共享库加载 | HarmonyOS 加载器**不能通过软链接加载共享库**（知识 E018/E511）。配方把依赖的 soname 别名（`libQt6Core.so.6`、`libQt6Gui.so.6`、`libexpat.so.1`）复制实体化到私有 `runtime-libs/` 并前置 `LD_LIBRARY_PATH`，否则 configure 阶段的 `qtpaths` 与运行期都报 `Error loading shared library`。本库自身则以 `CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE` 产出**不版本化 SONAME** 的单个 `libKExiv2Qt6.so`（无软链接链，同时满足 CI L5a 的 DT_SONAME 门禁） |
| SONAME | CMake 无 `Platform/HarmonyOS` 模块且本环境 ECM/CMake 组合未回传 `KEXIV2_VERSION`/`KEXIV2_SOVERSION`，配方通过 toolchain 补齐这两个变量并注入 `-Wl,-soname,`，避免产物缺 `DT_SONAME` 被 CI L5a 拦截 |
| 上游测试 | 上游 `tests/` **无自动化测试**（无 `add_test()`/`enable_testing()`，ctest 注册 0），仅 7 个演示程序；`BUILD_TESTING=ON` 编译后在 `build()` 中 7/7 真实执行并记录退出码 |
| 消费者测试 | `test_package/` 自建 JPEG 夹具，驱动 KExiv2 做 EXIF / 日期时间 / XMP 写入-回读往返，24 项断言全部通过 |

## 依赖

- qtbase 6.11.1（Qt6 Core/Gui，项目要求 >= 6.5.0）
- exiv2 0.28.7（项目要求 >= 0.27，conan 包为静态库）
- ecm 6.26.0（构建工具，项目要求 >= 6.0）

## 功能验证

```bash
pkg-config --modversion exiv2          # exiv2 >= 0.27
conan create archives/l/libkexiv2/26.04.0 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# test_package: checks=24 failures=0
#   libkexiv2 version: 5.1.0 / libexiv2 version: 0.28.7
```

## 参考

- 上游仓库：https://invent.kde.org/graphics/libkexiv2
- 源码归档：https://download.kde.org/stable/release-service/26.04.0/
