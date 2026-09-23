# knotifications 6.26.0 适配笔记

## Scope

This package is part of the KF6 6.26 baseline (platform task #6385,
dependency activity). It updates the existing HarmonyOS PC recipe from the
6.14.0 archive (previous complete archive) to KDE Frameworks 6.26.0.

## 编译环境
- 构建系统: cmake (ECM/KDE)
- 编译日期: 2026-09-06
- 编译器: clang/clang++ (OHOS SDK, aarch64-linux-ohos)
- 状态: built (verified via conan create)

## 依赖版本

- qtbase/6.11.1 (Qt6Gui; registry published)
- kconfig/6.26.0 (KF6::ConfigCore; registry published)
- ecm/6.26.0 (build tool; registry published)
- kcoreaddons/ki18n NOT required by knotifications 6.26.0 (upstream
  CMakeLists only requires Qt6Gui + KF6Config; 6.14.0 needed ki18n for
  ecm_create_qm_loader, 6.26.0 still uses it but via KF6I18n only if built —
  verified: find_package(KF6I18n) is absent in 6.26.0 CMakeLists)

未启用（制品仓未发布/平台限制）：
- libcanberra/0.30 — PR #8498 CI 绿在途，但未合入未发布；音频通知后端
  (notifybyaudio.cpp) 未编译进本包
- kconfigwidgets/6.26.0 — 未发布（6.14/6.18 已有；本包不依赖它）
- Qt6DBus — USE_DBUS=OFF：DBus popup/portal 后端未编译

## 上游变化 (6.14.0 → 6.26.0)

- cmake_minimum_required 3.16 → 3.29
- Qt 最低版本 6.7.0 → 6.9.0（qtbase 6.11.1 满足）
- ECM QCH 文档构建 (ecm_add_qch/BUILD_QCH) 换成 ecm_generate_qdoc
  （qdoc 工具不在 qtbase 制品包；ecm_generate_qdoc 内部 find_package(QDoc)
  QUIET，缺失时跳过，不需要 patch）
- BUILD_PYTHON_BINDINGS 改为显式 option（默认 ON，但 Shiboken6/PySide6 缺失
  时上游直接 find_package REQUIRED 失败——cmake_dependent_option 的旧逻辑
  是 QUIET 可选。新逻辑下 CI 环境会 fail，需注意）
- 弃用版本行 QT 6.9/KF 6.12 → QT 6.11/KF 6.23
- src/ 代码重排（notifybyaudio 错误码处理、manager 查找逻辑等小改）
- autotests/CMakeLists.txt 的 KNotificationTest 在上游 6.26.0 仍是注释状态
  （与 6.14.0 相同），tests/ 的 2 个可执行测试由 HAVE_DBUS 守卫

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 时 find_package(Canberra REQUIRED) 失败 | libcanberra 未发布到 ohpcd（PR #8498 在途） | patch 0001: DBus+Canberra 块整体 if(FALSE) 禁用（沿 6.14.0 同语义），音频通知后端不编译 |
| 2 | ecm_install_po_files_as_qm(poqm) 失败 | Qt6LinguistTools 不在 qtbase 制品包 | patch 0001: 注释该行（沿 6.14.0/6.18.0/6.26 链补丁语义） |
| 3 | BUILD_PYTHON_BINDINGS 默认 ON 导致 find_package(Python3 ... REQUIRED) 失败 | 6.26.0 上游把 Python 绑定从 dependent_option 改为显式 option | cmake_dependent_option 语义等价改写进 patch 0001 的 if 块（沿 6.14 打法：BUILD_PYTHON_BINDINGS 由 toolchain 关） |

## 测试说明（N 申报）

上游构建系统注册的 CTest add_test 数（实测 ctest -N）：**0**
- autotests/: KNotificationTest 上游注释（需 DBus session bus +
  fake_notifications_server，CI 无 dbus 环境，平台限制豁免口径）
- tests/: unitylaunchertest / knotificationdbustest 由 HAVE_DBUS 守卫
  （USE_DBUS=OFF 时 0 项注册；CI 无 session bus，平台限制豁免）
- examples/: 无 add_test，且需 Qt6 Quick（qtbase 制品包无 Qml/Quick 组件，
  已在 patch 0001 中随 BUILD_TESTING 块禁用该子目录）
- ctest 以 --no-tests=ignore 运行（N=0 是实测事实，--no-tests=error 会对
  真实的 0 测试集误报失败）；命令仍会真实执行，任何真实测试失败都会红
- 消费者侧补全：test_package 6 项断言（eventId/title+text/iconName/
  flags/addAction+label API 面）全部通过

## 验证结果

OHOS `conan create` verification (2026-09-06):
- 见 .ci-result.json（finish step [5/10] 写入）
- test_package: PASS

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（七点打法） |
| conandata.yml | 源码 URL + sha256 |
| patches/0001-CMakeLists.txt.patch | DBus/Canberra 禁用 + po-qm 禁用 + Python 绑定守卫 |
| test_package/ | 消费者测试（R34 真实 API） |
| manifest.yaml | 版本级元数据 |
| notes.md | 本笔记 |

## 注意事项

- 若后续 libcanberra/0.30 与 Qt6DBus 可用，可撤 patch 0001 的 if(FALSE)
  并开启 USE_DBUS=ON 恢复音频通知与 DBus 后端
- knotifications 的 KNotification 事件通知依赖系统通知服务；OHOS 上的
  运行时行为取决于宿主应用集成方式（本包只提供库）
