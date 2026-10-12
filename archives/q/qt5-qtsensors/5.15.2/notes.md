# qt5-qtsensors 5.15.2 适配笔记

## 编译环境
- 构建系统: qmake
- 编译日期: 2026-10-06
- 编译器: clang/clang++ (OHOS llvm 15)
- 状态: built

## 编译步骤

1. 手工骨架：archives/q/qt5-qtsensors/5.15.2/（九件套 = 版本七件 + 软件级三件，参照 qt5-qtmultimedia 先例）
2. 源码双源实测：官方 download.qt.io + 清华 tuna 镜像各下载一次，sha256 一致（3f0011f9e9942cad119146b54d960438f4568a22a274cdad4fae06bb4e0e4839）；conandata 只写官方单条 URL（R39）
3. qmake 构建沿用 qt5-qtmultimedia 模式：私有可写 Qt prefix 镜像 qtbase（symlink + 重写 mkspecs 中 .pri 的 build-dir 引用）+ `qmake -spec linux-clang`
4. QtSensors QML imports（src/imports，QT += qml quick）：按 qt5-qtgraphicaleffects 模式将 qt5-qtdeclarative 的模块 .pri（modules/modules-inst，重写为其包目录）与 mkspecs/features（qmltypes.prf）合并进私有 Qt prefix，使 qtHaveModule(quick) 为真、imports 子项目参与构建
5. 插件裁剪：`SENSORS_PLUGINS=generic`（上游 src/plugins/sensors/sensors.pro 官方 qmake 开关）——只构建 generic 纯软件后端插件；linux（读 /dev/input，OHOS PC 无传感器设备节点）与 iio-sensor-proxy（系统 D-Bus，OHOS 无 dbus-daemon）被排除
6. `make install STRIP=true`（qmake strip --strip-unneeded 会破坏动态符号表导致 dlopen 失败）；INSTALL_ROOT 暂存后搬入 package_folder（lib/include/mkspecs/plugins/qml）
7. 打包后重写 .prl/.la/.pc 中残留的 build-dir/source-dir 路径为 package_folder
8. OHOS 对包内全部 .so 做 binary-sign-tool 签名（qrencode 模式：llvm-objcopy 先删 .codesign 段再 selfSign）
9. test_package：find_package(Qt5Sensors CONFIG REQUIRED) + 15 项消费者侧断言（CMAKE_SYSTEM_NAME=Linux 强制 + OHOS_CXX_RUNTIME_DIR 运行时链接，adamstark-audiofile + qt5-qtmultimedia 先例组合）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | iio-sensor-proxy 插件加载即 SIGSEGV | `QDBusConnection::systemBus().interface()->isServiceRegistered(...)` 在无系统 D-Bus 守护进程的 OHOS 上返回空 interface，链式调用空指针解引用 | 上游官方 qmake 开关 `SENSORS_PLUGINS=generic` 裁剪（零补丁）；单插件隔离实测定位（generic/linuxsys 加载安全 rc=0，iio 崩溃 rc=139） |
| 2 | QML imports 不构建 | src.pro 中 `qtHaveModule(quick)` 需要私 有 Qt prefix 能解析 qml/quick 模块 | 将 qt5-qtdeclarative 的模块 .pri 与 features 合并进私有 prefix（qt5-qtgraphicaleffects 模式） |
| 3 | qsensorgestures 上游测试段错误（rc=139） | QT_PLUGIN_PATH 下动态手势插件与测试内 QT_STATICPLUGIN mock 插件重复注册 | 干净环境（无 QT_PLUGIN_PATH）运行；该套件自带静态 mock 插件 |
| 4 | 上游测试 qmake/运行报 libc++ 符号缺失 | qmake（本体是 OHOS 二进制）需 LD_LIBRARY_PATH 指向 qtbase 包 lib | 构建与运行环境统一设置 LD_LIBRARY_PATH |
| 5 | legacy_sensors 套件 33/77 失败 | 强依赖完整 QtQuick 运行时（QML 插件搜索路径）且上游 auto.pro 已注释禁用（#SUBDIRS） | 按上游默认套件口径统计（不含 legacy_sensors）；失败定性为环境限制 |

## 源码修改

- 无补丁（patches_applied 为空），仅配方层适配（SENSORS_PLUGINS 为上游官方 qmake 变量）

## 依赖版本

- qt5-qtbase/5.15.2.2（已发布）
- qt5-qtdeclarative/5.15.2（已发布）

## 上游测试实测（本机即目标机 aarch64 OHOS）

tests/auto 默认套件（上游 auto.pro SUBDIRS 实际启用项）全部构建并运行：

| 套件 | 结果 |
|------|------|
| qsensor（自带 mock 后端 TestSensorPlugin） | 38 passed / 0 failed |
| qsensorgestures（自带静态 mock 插件） | 15 passed / 0 failed |
| qsensorgestureplugins（动态加载包内手势插件） | 13 passed / 0 failed |
| qsensorgestures_gestures（mock 数据回放） | 41 passed / 0 failed |
| sensors2qmlapi | 4 passed / 0 failed |
| qtsensors5 | 2 passed / 0 failed |
| **合计** | **113 passed / 0 failed（100%）** |

legacy_sensors（上游已禁用）44/77，环境限制不计数；bic/systemtests/manual 非默认套件。

## 验证结果

```bash
conan create . -pr:h=~/.conan2/profiles/ohos-aarch64 --build=missing（本地预验证全绿）
test_package: RUN ./test_qt5_qtsensors → 15/15 PASS（exit 0）
```
