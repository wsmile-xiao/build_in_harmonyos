# kdbusaddons5 5.116.0 适配笔记

## 编译环境
- 构建系统: cmake (Ninja)
- 编译日期: 2026-09-18
- 编译器: clang / clang++（HarmonyOS PC 工具链，aarch64）
- 状态: built（conan-verify 通过，未 upload）

## 编译步骤

探索性编译（模式 B，验证可用后再固化为 Conan 配方）：

```bash
cmake $SRC \
  -DCMAKE_TOOLCHAIN_FILE=<conan_toolchain.cmake> \
  -DCMAKE_BUILD_TYPE=Release \
  -DECM_MODULE_PATH="$ECM_PKG/share/ECM/modules;$ECM_PKG/share/ECM/find-modules;$ECM_PKG/share/ECM/kde-modules" \
  -DCMAKE_PREFIX_PATH="$QT_PKG/lib/cmake;$ECM_PKG/share/ECM/cmake" \
  -DKF_IGNORE_PLATFORM_CHECK=TRUE \
  -DKF_SKIP_PO_PROCESSING=ON \
  -DWITH_X11=OFF \
  -DKDE_INSTALL_USE_QT_SYS_PATHS=OFF \
  -DBUILD_TESTING=OFF
make -j1
```

产物：`libKF5DBusAddons.so` + `kquitapp5`（均构建成功，`kquitapp5 --help` 可执行）。

固化为 Conan 配方后，`conan create` 通过（G2），W3 本地 CI 模拟通过。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `find_package(Qt5DBus REQUIRED)` 失败 | `qt5-qtbase/5.15.2` 的二进制未配置 `-dbus`，无 Qt5DBus 模块 | 改用 `qt5-qtbase/5.15.2.2`（DBus 变体，requires dbus/1.14.10），提供 Qt5DBus |
| 2 | `ECMPoQmTools` 处理 poqm 报错 | 需 `Qt5LinguistTools`（lrelease），qt5 制品仓无此工具 | `-DKF_SKIP_PO_PROCESSING=ON` 跳过 po→qm |
| 3 | Qt5Core 引用 `../b/mkspecs/linux-clang` 不存在 | 发布包 mkspec 路径与源码不一致 | 复制包内 `mkspecs/linux-clang` 到 `<pkg>/../b/mkspecs/`（同 attica-kf5） |
| 4 | Qt5X11Extras 找不到 | OHOS 无 X11 | `-DWITH_X11=OFF` → `HAVE_X11=FALSE`，qtx11extras 代码路径编译掉（可选依赖） |

## 源码修改

无修改，无补丁。以上问题全部通过配方（conanfile.py）的 CMakeToolchain 变量解决，未改动上游源码。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| qt5-qtbase | 5.15.2.2 | 运行时，提供 Qt5Core/Qt5DBus/Qt5Gui |
| ecm | 6.20.0 | build-only（tool_requires），ECM 模块 |
| dbus | 1.14.10 | 经 qt5-qtbase 依赖链引入 |

## 验证结果

- 探索性编译：`make` 成功，`libKF5DBusAddons.so` + `kquitapp5` 生成
- conan-verify G0-G4 + L2/L4/L5：全部通过，test_package 实测 `KDBusService` API
- W3 本地 CI：`build_and_test.sh` 通过，`.ci-result.json` exit_code=0
- 上游 autotests 未运行：需 D-Bus session bus / dbus-daemon，CI 沙箱无此环境

## 交付物

| 文件 | 说明 |
|------|------|
| libKF5DBusAddons.so | KF5 DBusAddons 动态库 |
| kquitapp5 | 命令行工具（D-Bus 服务退出），software 级 commands.json 已声明（R38） |

## 注意事项

- `qt5-qtbase` 必须用 `5.15.2.2`（DBus 变体），plain `5.15.2` 无 Qt5DBus。
- `KF_SKIP_PO_PROCESSING=ON` 时 poqm 目录不生成 qm，但对库本体无影响。
- test_package 构造 `KDBusService` 需加 `NoExitOnFailure`，否则无 session bus 时构造即 `exit(1)`。

## 编译结束

最终状态：built（conan-verify 通过，W3 本地 CI 模拟通过，未 upload）。
编译结束标记（COMPLETED）。
