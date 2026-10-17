# kmousetool 26.04.0 适配 notes

## R45 存档
- 工作目录: /storage/Users/currentUser/tmp/kmousetool-wk/
- 仓库: /storage/Users/currentUser/鸿蒙PC/build_in_harmonyos (branch feat/kmousetool-26.04.0)
- 源码 tarball: $HOME/tmp/kmousetool-wk /storage/Users/currentUser/tmp/kmousetool-wk/kmousetool-26.04.0.tar.xz
  sha256 = 3eec4e18549856a6f30836f96de7c33ba136c41ddccbcfe7ec44269e26216b81
- 官方 URL: https://download.kde.org/stable/release-service/26.04.0/src/kmousetool-26.04.0.tar.xz

## 依赖图（R35 全部 conan download -r ohpcd 验证过发布）
- qtbase/6.11.1.1 override=True（DBus-enabled 变体，全图统一）
- qtmultimedia/6.11.1
- KF6: kconfig/6.18.0 kconfigwidgets/6.18.0 kcoreaddons/6.18.0 kcrash/6.18.0
  ki18n/6.18.0 kiconthemes/6.18.0 kwidgetsaddons/6.18.0 kxmlgui/6.18.0
  kdbusaddons/6.29.0
- statusnotifieritem/6.26.0（KStatusNotifierItem 所在包；kstatusnotifieritem 包不存在）
- X11: libx11/1.8.13 + libxtst/1.2.5（XTest API）
  - 无 libxt（Xt 全为死 include，CMakeLists Xt 检查已补丁删除）
  - 无 libxext/libxi（源码无 Xext 符号；XTest.h 自包含，无需 XInput.h）
- tool_requires: ecm/6.26.0

## 关键侦察结论
- kmousetool.cpp include 块 1-30 行：XTest.h 之外 5 个 X11 include 全为死代码
  (Intrinsic.h/StringDefs.h/Xmd.h/xtestext1.h/fixx11h.h)，全源码无 Xt 符号引用
- 实际 Xlib/XTest 使用：XOpenDisplay/Display*（libx11），XTestFakeButtonEvent/
  XTestFakeKeyEvent/XTestQueryExtension（libxtst）
- kmousetool/CMakeLists.txt 29-31 行链接 ${X11_XTest_LIB} ${X11_Xext_LIB} ${X11_LIBRARIES}
  —— 保留原文（X11_LIBRARIES 来自 FindX11 找到的库集合，libx11 包提供；Xext 库本身
  无符号被引用，链接器 --as-needed 下不会产生对未发布包的 DT_NEEDED）
- kmousetool.cpp:581 KStatusNotifierItem 基类 → statusnotifieritem/6.26.0
- 顶层 CMakeLists 12 行 KF_MIN_VERSION 6.3.0；14 行 find_package(ECM NO_MODULE)；
  30 行 Qt6 含 Multimedia；37 行 KF6 九组件；51-72 行 KF6DocTools OPTIONAL；
  62 行无条件 ki18n_install(po)
- qtbase 6.11.1.1 包提供 offscreen QPA 插件（缓存 p/plugins/platforms/libqoffscreen.so），
  qtbase 配方 test_package 即用 QT_QPA_PLATFORM=offscreen

## 补丁说明
- patches/0001-ohos-x11-cmake-fixes.patch：顶层 CMakeLists 删除 Xt 硬检查
  （find_package(X11 REQUIRED) 与 XTest 检查保留）。已验证 patch -p1 干跑+实际应用成功。
- patches/0002-ohos-x11-dead-includes.patch：kmousetool.cpp 删除 5 个死 include
  （X11/Intrinsic.h、X11/StringDefs.h、X11/extensions/xtestext1.h 为 libXt/独有头
  全仓无包提供；fixx11h.h 为 kdelibs 遗留头不存在；X11/Xmd.h 保留——xorgproto 提供）。
  编译报 fatal error: X11/Intrinsic.h not found 后确认，patch-ng 解析通过。

## 关键构建修复（CMAKE_SYSTEM_NAME=Linux）
- 本机 cmake 4.1.2 无 HarmonyOS 平台模块：SYSTEM=HarmonyOS → UNIX=FALSE →
  FindX11 整体被 if(UNIX) 跳过（零 find_path 调试行、X11_FOUND=FALSE）。
  最小复现 + ableton-link/abcmidi 先例（E092）确认。
- 修法：toolchain cache_variables 设 CMAKE_SYSTEM_NAME=Linux +
  CMAKE_SYSTEM_PROCESSOR=aarch64（OHOS 即 Linux 内核）。configure 立即通过。
- 残留 KF6DocTools 软失败（无 gettext/msgfmt）由 KF_SKIP_PO_PROCESSING=ON 处理。

## 本机 ELF exec 限制结论（test_package 设计依据）
- 配方构建的 bin/kmousetool 在本机 exec 一律 EPERM（execve errno=1），已穷尽对照：
  同工具链 native/musl clang 产物、等尺寸(141KB/3MB)、PIE、相同程序头、RUNPATH
  数量与内容、改名/权限/目录迁移均不影响——q.bin（链接 Qt6Core/Gui/Widgets/DBus/
  Network+RUNPATH）可跑，kmousetool 不可跑，归因为系统执行管控（非包缺陷）。
- test_package 因此按 actiona 先例（Qt GUI application）做产物契约验证：
  ELF/aarch64 魔数断言 + readelf DT_NEEDED 链接集断言（按上游 target_link_libraries
  实际链接集核对，无 KF6::Crash——上游未链接）+ XTestFakeButtonEvent 重定位断言；
  另编译并真实运行 xtest_smoke（调用被测包 XTest API，XOpenDisplay 无 X server
  返回 nullptr 为预期路径，exit 0）。

## R51 上游测试申报
- 上游 tarball 无 tests/ 目录、无 add_test/ctest 注册、无 test_package —— 上游确无测试
- 清点证据：tar -tf 列表无 test 目录；grep add_test/enable_testing 全仓零命中
- 处置：按 R51 自行补齐应用型 test_package（产物契约断言 + XTest API 运行冒烟），
  路径 B（知识库扩展）
- 实测结果（2026-09-19 本机）：
  - conan create 全量通过（configure/compile/link/package 全绿）
  - test_package: xtest_smoke 编译+运行通过（"xtest_smoke ok (link+runtime
    against libXtst)"），kmousetool 产物断言+DT_NEEDED/符号契约断言全过
  - 上游测试 0/0（上游确无测试，见清点证据），自补测试 1/1 通过 = 100%

## 待办
- finish 终态校验
- 推送 fork（GitCode）+ PR 正文
---

**编译结束**: 2026-09-19 14:23
**最终状态**: built
