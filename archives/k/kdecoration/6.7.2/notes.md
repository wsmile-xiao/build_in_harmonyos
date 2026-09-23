# kdecoration 6.7.2 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-06
- 编译器: clang/clang++ (OHOS SDK 26.0.0.18, clang 15.0.4)
- 状态: built

## 上游信息
- 上游: https://invent.kde.org/plasma/kdecoration (KDE Plasma 窗口装饰插件接口库)
- v6.7.2 tag: c7eabcd88eb25348efeca0a6f3b21f3b0cb675f3
- 源码包: https://download.kde.org/stable/plasma/6.7.2/kdecoration-6.7.2.tar.xz
- 产物: libkdecorations3.so.6.7.2 (KDecoration3::KDecoration)、libkdecorations3private.so.6.7.2、KDecoration3Config.cmake

## 编译步骤

conan create archives/k/kdecoration/6.7.2 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | ki18n_install(po) 失败 | OHOS 无 msgmerge（gettext tools 未发布到制品仓） | patch 0001：HarmonyOS 下跳过 po 安装（运行时 i18n 仍经 KF6::I18n 解析） |
| 2 | C++ 标准不足 | kdecoration 6.7.2 使用 C++20（上游 CMakeLists 设 CMAKE_CXX_STANDARD 20），conan toolchain variable_watch 将其覆盖回 17 | generate() 中以 CMAKE_CXX_FLAGS="-std=c++20" 强制（kcoreaddons 6.26.0 同款方案） |
| 3 | find_package(KF6I18n) 失败 | ki18n 使用 cmake_find_mode=none，CMakeDeps 不注入其 lib/cmake 到 CMAKE_PREFIX_PATH | generate() 中手动向 conan_cmakedeps_paths.cmake PREPEND ki18n 路径 |
| 4 | ECMQueryQt 调 qtpaths 报 127（libc++_shared.so 加载失败） | qtbase 的 qtpaths 是 OHOS ELF，运行时需 libc++_shared.so（位于 OHOS SDK llvm/lib/aarch64-linux-ohos） | build() 中动态探测 SDK lib 目录注入 LD_LIBRARY_PATH（ki18n 6.26.0 同款方案） |
| 5 | 库构建输出在 bin/ 且 NEEDED 记录 ../bin/libkdecorations3private.so，安装后 musl 加载器无法解析 | KDECMakeSettings (ECM>=5.38) 对所有平台设 CMAKE_LIBRARY_OUTPUT_DIRECTORY=${CMAKE_BINARY_DIR}/bin | patch 0002：仿 ANDROID 分支重设为 ${CMAKE_BINARY_DIR}/lib |
| 6 | 库无 SONAME，public 库 NEEDED 记录相对路径（musl 不支持） | CMake 无 Platform/HarmonyOS 模块，走 Generic 平台规则，CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG 未定义，链接器不传 -Wl,-soname | generate() 在 tc.generate() 后向 conan_toolchain.cmake 追加 set(CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG "-Wl,-soname,")（Linux 平台模块同值）；两库获得 DT_SONAME，NEEDED 变为裸 soname libkdecorations3private.so.2 |

## 依赖版本

- qtbase/6.11.1 (Qt6Core/Qt6Gui/Qt6Test)
- ki18n/6.26.0 (KF6::I18n)
- ecm/6.26.0 (build tool_require)

## 验证结果

conan create PASS：
- 上游 autotest 3/3 通过（kdecoration3-decorationButtonTest、kdecoration3-decorationTest、kdecoration3-decorationShadowTest，QT_QPA_PLATFORM=offscreen）
- test_package 1/1 Passed（KDecoration3::DecorationThemeMetaData 真实 API round-trip + BorderSize 枚举）

## 构建产物

- libkdecorations3.so.6.7.2 (SONAME libkdecorations3.so.6)
- libkdecorations3private.so.6.7.2 (SONAME libkdecorations3private.so.2)
- KDecoration3Config.cmake / KDecoration3ConfigVersion.cmake / KDecoration3Targets.cmake
- 头文件 include/KDecoration3/（CamelCase + lowercase + kdecoration3_export.h + Private/）

## 关键修复

- Qt6/KF6 双"cmake_find_mode=none"依赖（qtbase、ki18n）都需要在 conan_cmakedeps_paths.cmake 手动 PREPEND 路径，否则上游 CMake 的 find_package(Qt6)/find_package(KF6I18n) 均失败。
- HarmonyOS 未知平台导致 CMake 不给 shared library 传 soname flag —— 需在 toolchain 显式设置 CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG，同项目内多 so 互链时此问题致命（NEEDED 记相对路径，musl 加载器无法解析）。此经验适用于所有 KDE Plasma/KF6 带 private 库的包。
- 上游 autotest 需 QT_QPA_PLATFORM=offscreen + HOME/XDG_RUNTIME_DIR 沙箱环境（与 kcoreaddons 6.26.0 同款测试环境注入）。
---

**编译结束**: 2026-09-06 11:37
**最终状态**: published
