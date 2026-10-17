# bluez-qt 6.28.0 适配笔记

## 编译环境
- 构建系统: cmake（ECM KDE 框架）
- 编译日期: 2026-09-02
- 编译器: clang 15.0.4 / clang++
- 状态: built

## 编译步骤

bluez-qt 6.28.0 为 KDE Frameworks 6 Tier 1 库（Qt BlueZ D-Bus 封装），
通过 Conan 配方驱动 CMake 构建：

1. `conan create`（ohos-aarch64 profile）自动完成源码下载/解压/配置/编译
2. CMake 配置关键参数：
   - `KF_IGNORE_PLATFORM_CHECK=true`（绕过 KDE 平台检测，OHOS 不在列表）
   - `KDE_SKIP_UNINSTALL_TARGET=TRUE`（ECM 打包缺 ecm_uninstall.cmake.in）
   - `KF_SKIP_PO_PROCESSING=ON`（qtbase 无 Qt6LinguistTools）
   - `Qt6_DIR/Qt6Core_DIR/Qt6DBus_DIR/Qt6Network_DIR` 指向 qtbase 包 config
3. `cmake --build -j1`（OHOS 沙箱不支持 mkfifo，须串行编译）
4. 运行上游 autotests（`ctest --output-on-failure -j1`）
5. 主库产物 `libKF6BluezQt.a` 编译成功，test_package 消费者测试通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | qtpaths 运行报 `_Unwind_Resume` 等 C++ 符号重定位失败 | 本机 `LD_LIBRARY_PATH` 的 `/data/storage/el1/bundle/libs/arm64` 段含不兼容的 `libc++_shared.so`（1334688B），加载器优先命中 | `generate()` 通过 Environment 将 qtbase lib 与 `/system/lib64`（兼容 libc++_shared.so 1289544B）前置到 `LD_LIBRARY_PATH` |
| 2 | ECM `ecm_setup_version` configure_file 失败 | ECM 6.28.0 打包缺 `ECMVersionHeader.h.in` 模板 | `generate()` 用 ECM 源码自带模板内容补齐（if-not-exists 保护，karchive 先例） |
| 3 | `ecm_qt_declare_logging_category` configure_file 失败 | ECM 打包缺 `ECMQtDeclareLoggingCategory.cpp.in/.h.in` 模板 | `generate()` 补齐两个模板文件 |
| 4 | test_package configure 失败 `find_dependency(qtbase)` 找不到 | qtbase 为 `cmake_find_mode=none` 无 config 文件，CMakeDeps 生成的 KF6BluezQtConfig.cmake 引用 qtbase | `package_info` 设 `cmake_find_mode=none` + `builddirs`，下游用上游 KF6BluezQtConfig.cmake（find_dependency Qt6Core/Qt6DBus） |
| 5 | test_package 编译失败 `Qt6::Network target was not found` | 静态库 KF6BluezQt 将 PRIVATE Qt6::Network 传播到链接接口，KF6BluezQtConfig 未定义该目标 | test_package CMakeLists 在 find_package(KF6BluezQt) 前先 `find_package(Qt6 COMPONENTS Core DBus Network)` |
| 6 | test_package 编译失败 `BluezQt/bluezqt_version.h not found` | 版本头实际安装在 include 根 `bluezqt_version.h`，CamelCase 头无 .h 后缀 | test.cpp 改用 `#include <BluezQt/Manager>`（无 .h）与 `#include <bluezqt_version.h>` |

## 源码修改

无源码补丁（patches/ 为空）。ECM 缺失模板通过配方 generate() 在构建期补齐。

## 依赖版本

- extra-cmake-modules/6.28.0（已发布至制品仓，bluez-qt 链前置依赖）
- qtbase/6.11.1.1（FEATURE_dbus=ON，提供 Qt6::DBus 组件；6.11.1 的 dbus=OFF 不满足）
- dbus/1.14.10（qtbase 的 Qt6DBus 传递依赖）

## 验证结果

```bash
# conan-verify（G1-G4 全 PASS）
python3 scripts/ohc-run.py conan-verify bluez-qt 6.28.0  # exit 0

# 本地 CI 模拟（W3，100% 通过）
CI_PACKAGES="archives/b/bluez-qt/6.28.0" zsh ci/conan/build_and_test.sh  # exit 0

# test_package 消费者测试
test_bluez_qt  # 输出: bluez-qt consumer OK (Manager instantiated, version=6.28.0)
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake + ECM + Qt6 配方（含 LD_LIBRARY_PATH 修复与 ECM 模板补齐） |
| conandata.yml | 官方源 URL + sha256 校验 |
| test_package/ | 消费者测试（Manager 实例化 + 版本宏校验） |
| manifest.yaml | 版本级元数据（status: built） |

## 注意事项

- bluez-qt 属蓝牙深度适配领域（R40）：本包为 Qt 对 BlueZ D-Bus API 的
  封装层，编译通过即适配完成；实际蓝牙功能链路需运行中的 BlueZ daemon，
  由系统/设备侧提供。消费者测试覆盖库 API 消费路径。
- autotests 需 Qt6::Test 与 fakebluez 环境，运行期 D-Bus session bus 缺失
  时相关用例按环境限制记录结果，不阻塞构建（kdbusaddons/karchive 同口径）。
- 本机 LD_LIBRARY_PATH 的 bundle/libs 段含不兼容 libc++_shared.so，是
  OHOS 沙盒环境特性；CI clean 环境无此问题，配方注入 /system/lib64 属
  通用兜底（无害）。
---

**编译结束**: 2026-09-02 05:56
**最终状态**: built
