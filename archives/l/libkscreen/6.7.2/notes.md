# libkscreen 6.7.2 适配笔记

## 编译环境
- 构建系统: cmake (KDE ECM 系)
- 编译日期: 2026-09-19
- 编译器: clang/clang++ (OHOS SDK, aarch64-linux-ohos)
- 状态: built

## 软件说明
libkscreen 是 KDE Plasma 的屏幕管理库（KScreen 命名空间）：
- libKF6Screen.so：核心库（Config/Output/Mode/Screen/EDID 模型 + backendmanager D-Bus 桥）
- libKF6ScreenDpms.so：DPMS 电源管理库（Wayland DPMS 协议）
- kscreen-doctor：命令行诊断工具
- kscreen_backend_launcher：D-Bus 后端服务进程
- 后端插件：KSC_Fake（fake JSON 后端）+ KSC_KWayland（KWin Wayland 后端）
- XRandR 后端（XCB 系）在 OHOS 上裁剪

## 依赖核验（制品仓 ohpcd 实测）
| 依赖 | 上游要求 | 制品仓版本 | 结论 |
|---|---|---|---|
| Qt6 Core/DBus/Gui/Test | ≥6.10 | qtbase/6.11.1.2 | ✅ |
| Qt6 WaylandClient | ≥6.10 | qtwayland/6.11.1（qtbase 6.11.1.2 内含 Qt6WaylandClient cmake）| ✅ |
| ECM | ≥6.26（KF6_MIN_VERSION）| ecm/6.26.0 | ✅（ECM 大版本内向后兼容，kconfigwidgets 6.14+ecm 6.20 先例）|
| PlasmaWaylandProtocols | ≥1.21 | **未发布** | ⚠️ 配方携带 1.21 源码注入 |
| Wayland Client | ≥1.24 | wayland/1.24.0 | ✅ |
| XCB（可选） | optional | 无 | ✅ 可选裁剪 |

⚠️ 任务卡提到"kconfig/kconfigwidgets/kcoreaddons/ki18n/kwidgetsaddons 为依赖"——实测 6.7.2 源码全树 grep 无任何 KF6 框架依赖（libkscreen 是 Plasma 组件不是 KF6 框架组件），实际依赖为 Qt6+ECM+wayland 系。

## 编译步骤

```bash
# conan create（W3 本地验证）
conan create . --build=missing -pr=ohos-aarch64
# 关键配置：
#   BUILD_TESTING=OFF（上游测试在 test_package 外单独跑，见"上游测试"节）
#   KF_IGNORE_PLATFORM_CHECK=TRUE（OHOS 不在 KDE 平台清单）
#   PLASMA_WAYLAND_PROTOCOLS_DIR=<src>/plasma-wayland-protocols/src/protocols
#   PlasmaWaylandProtocolsConfig.cmake 手写注入 generators 目录
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | find_package(PlasmaWaylandProtocols 1.21 CONFIG) 失败 | ohpcd 制品仓无此包 | conandata 第二源下载官方 plasma-wayland-protocols-1.21.0.tar.xz，extract 到源码树旁，手写 PlasmaWaylandProtocolsConfig.cmake + 注入 PLASMA_WAYLAND_PROTOCOLS_DIR |
| 2 | libdpms 链接 XCB::XCB 失败 | OHOS 无 XCB | 补丁 0001：裁 XcbDpmsHelper 源文件与 XCB 链接库，保留 WaylandDpmsHelper |
| 3 | dpms.cpp include QtGui/private/qtx11extras_p.h 失败 | qtbase 6.11.1.2 是非 X11 平台构建，不安装该私有头 | 补丁 0001：去 X11 分支，Wayland 分支变首分支 |
| 4 | 上游测试 add_test COMMAND dbus-launch 不存在 | OHOS 无 dbus-launch | 补丁 0001：直跑可执行文件，D-Bus 会话由测试环境提供 |
| 5 | qt6_generate_wayland_protocol_client_sources 需要 wayland-scanner | wayland/1.24.0 是目标平台包 | build_requires wayland/1.22.0（其 bin/wayland-scanner 为本机 arm64 原生二进制）+ WaylandScanner_EXECUTABLE 注入 |
| 6 | 上游测试加载 KSC_Fake.so 报 "Error loading ../../bin/libKF6Screen.so" | KSC_Fake.so 记录相对 DT_NEEDED（含 /），OHOS musl 按进程 CWD 解析不查 LD_LIBRARY_PATH（E607 同族） | 测试运行时在 CWD 向上两级的 bin/ 放 libKF6Screen.so 符号链接桥（kcalendarcore 先例） |
| 7 | 上游源码 C++23（<expected>/<print>/<format>/ranges::to/views::zip）| OHOS clang15/libc++15 无这些头且 ranges 不完整 | 补丁 0002：SetConfigResult polyfill + 迭代器算法改写 + CXX_STANDARD 23→20（<compare>/<=> 可用）|

## 源码修改

- patches/0001-ohos-no-xcb-and-optional-dbus-launch.patch：三处（autotests 去 dbus-launch、libdpms 裁 XCB、dpms.cpp 去 X11 分支）

## 依赖版本
- qtbase/6.11.1.2
- qtwayland/6.11.1
- wayland/1.24.0（链接库）+ wayland/1.22.0（build 工具包：wayland-scanner）
- ecm/6.26.0（build 工具包）
- plasma-wayland-protocols 1.21.0（源码内嵌，非 conan 包）

## 上游测试

上游构建系统注册的测试目标（autotests/CMakeLists.txt kscreen_add_test 宏，BUILD_TESTING=ON 口径）：
- kscreen-testscreenconfig / kscreen-testconfigserializer / kscreen-testconfigmonitor / kscreen-testinprocess / kscreen-testbackendloader / kscreen-testlog / kscreen-testmodelistchange / kscreen-testedid（8 个）
- testxrandr：ENABLE_XRANDR_TESTS 未启用，未注册（XCB 缺失）
- testkwaylandbackend / testkwaylandconfig：需 KF6::WaylandServer（上游 FIXME 标注 KF6 中不存在），CMake 配置阶段 return() 跳过
- tests/kwayland/waylandtestserver：同 KF6::WaylandServer 依赖，跳过

### 真跑结果（本机 aarch64 OHOS，QTest 直跑，2026-09-19）

在 conan 构建树上增量开启 BUILD_TESTING=ON 构建 8 个测试可执行文件后真跑
（QT_QPA_PLATFORM=offscreen、KSCREEN_BACKEND=Fake、KSCREEN_BACKEND_INPROCESS=1、
fake 插件目录注入 QT_PLUGIN_PATH；musl 相对 DT_NEEDED 坑用 ../bin 库桥解，
见"遇到的问题"第 6 条）：

| 测试目标 | 结果 | 用例 |
|---|---|---|
| testscreenconfig | PASS | 10/10 |
| testinprocess | PASS | 7/7 |
| testconfigmonitor | PASS | 3/3 |
| testbackendloader | PASS | 9/9 |
| testlog | PASS | 5/5 |
| testconfigserializer | PASS | 8/8 |
| testmodelistchange | PASS | 3/3 |
| testedid | FAIL | 3/7（4 用例挂）|

合计：48 用例通过 / 52 注册用例（92%）。testedid 的 4 个失败用例
（cor/dell/samsung/sharp）全部挂在同一断言 `QCOMPARE(e->deviceId(), deviceId)`：
EDID 二进制解析正常（isValid/pnpId/name/serial 断言全过），但 vendor
全名需要查 `/usr/share/hwdata/pnp.ids` 硬编码路径——OHOS 无 hwdata 包
且 /usr/share 只读不可注入，deviceId 缺 vendor 段（如 "xrandr-DELL U2410-..."
而非 "xrandr-Dell Inc.-DELL U2410-..."）。属环境限制（无 hwdata 数据文件），
非适配代码缺陷。

## 验证结果

```bash
# 本机 W3 conan create 全绿（local_verify.py 登记）
# test_package 消费者测试：test_libkscreen PASS
```

## 注意事项
- KF6Screen 的 cmake 包用 cmake_find_mode=none（项目自带 KF6ScreenConfig.cmake 带完整 find_dependency 链）
- libKF6Screen.so 的 DT_NEEDED 记录构建树相对路径——test_package 需按 kconfigwidgets 先例 symlink 镜像

---

**编译结束**: 2026-09-19
**最终状态**: built
