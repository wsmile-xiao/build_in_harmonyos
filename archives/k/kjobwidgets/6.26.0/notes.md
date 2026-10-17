# kjobwidgets 6.26.0 适配笔记

## 编译环境
- 构建系统: cmake（ECM 6.26.0，KF6 标准框架布局）
- 编译日期: 2026-09-27
- 编译器: clang/clang++（OHOS SDK clang 15，profile ohos-aarch64）
- conan: 2.29.1（OHOS 适配版），remote ohpcd
- 状态: built

## 背景（为何适配）
konversation 26.04.0 的 REQUIRED KF6 组件链要求 KF6JobWidgets/KF6Parts/KF6NotifyConfig
≥ 6.26.0，而 ohpcd 仅发布 kjobwidgets/6.18.0、无 kparts/knotifyconfig——
依赖链扩展：kjobwidgets/6.26.0 → kparts/6.26.0 → knotifyconfig/6.26.0。

## 真实依赖（kjobwidgets-6.26.0/CMakeLists.txt）
- ECM 6.26.0（tool_requires ecm/6.26.0）
- Qt6 Widgets（qtbase/6.11.1；Qt6GuiPrivate 仅 WITH_X11 时需要）
- KF6CoreAddons / KF6WidgetsAddons / KF6Notifications（均 6.26.0，已发布）
- 可选：Qt6 DBus（USE_DBUS）、X11（WITH_X11）、Python3+Shiboken6（BUILD_PYTHON_BINDINGS）

## 编译步骤

```bash
conan create archives/k/kjobwidgets/6.26.0 --build=missing -pr:h ohos-aarch64 -pr:b default
```

generate() 注入：ECM_MODULE_PATH 三段手工 set（CMakeDeps 不传播）；
qtbase cmake_find_mode=none → 手工生成 conan_cmakedeps_paths.cmake 把全部依赖的
lib/cmake、lib、include 前置；CMAKE_SHARED_LIBRARY_SONAME_*_FLAG 注入（E330）；
build/test 环境前置 /system/lib64（沙箱 libc++_shared.so 遮蔽，kconfig 先例）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | KDE 平台检查不含 OHOS | ECM 平台白名单 | KF_IGNORE_PLATFORM_CHECK=TRUE（kitemviews/knotifications 先例同款） |
| 2 | DBus job tracker 需要 Qt6DBus | qtbase/6.11.1 变体 FEATURE_dbus=OFF | 改用 qtbase/6.11.1.1（FEATURE_dbus=ON，dbus/1.14.10 已发布）+ override=True 统一依赖图；USE_DBUS=ON |
| 3 | WITH_X11 默认 ON（非 WIN/APPLE/ANDROID/HAIKU 平台） | OHOS 不在排除列表 | WITH_X11=OFF，Qt6GuiPrivate 依赖随之消失 |
| 4 | Python 绑定需要 shiboken6 | 工具链无 Shiboken6 | BUILD_PYTHON_BINDINGS=OFF |
| 5 | OHOS 原生构建无 DT_SONAME | Generic 平台模块无 soname 规则 | 注入 CMAKE_SHARED_LIBRARY_SONAME_*_FLAG（E330/kcodecs 先例） |
| 6 | ecm_install_po_files_as_qm(poqm) 触发 find_package(Qt6LinguistTools) 失败 | qtbase 包未发布 LinguistTools 组件 | 补丁 0001 注释该调用（qm 翻译不构建；kconfig/6.26.0 先例同款） |

## 源码修改

1 个补丁（patches/0001-disable-poqm-linguisttools.patch）：仅注释根
CMakeLists.txt 的 `ecm_install_po_files_as_qm(poqm)` 一行（Qt6LinguistTools
未发布 ohpcd；翻译 qm 产物非库功能），无其他改动。

## 依赖版本

qtbase/6.11.1.1（override=True，FEATURE_dbus=ON）、kcoreaddons/6.26.0、kwidgetsaddons/6.26.0、knotifications/6.26.0、
ecm/6.26.0（tool）。

## 验证结果

```bash
# 上游测试（R51 实测，2026-09-30）：USE_DBUS=ON 后 HAVE_QTDBUS 守卫解除，
# ctest 注册 2 项并全部通过：
#   1/2 kuiserver2jobtrackertest  Passed 0.06s
#   2/2 kuiserver2jobtrackertest2 Passed 0.22s
#   100% tests passed, 0 tests failed out of 2
# 运行环境：LD_LIBRARY_PATH 需含构建 bin/（SONAME .so.6 与加载器解析）+ /system/lib64
# 注：初版 USE_DBUS=OFF 时注册 0 测试；rule4 审查要求真实执行上游用例后改为 ON。
# test_package 消费者测试：5 项断言（KWidgetJobTracker 构造、registerTracker/
# unregisterTracker 往返、KDialogJobUiDelegate autoDelete 往返、KJob::setUiDelegate
# 关联、KJob::setAutoDelete）→ 实机输出 kjobwidgets 6.26.0: all 5 checks passed
```

产物：lib/libKF6JobWidgets.so（含版本符号链接）、include/KF6/KJobWidgets/ 头文件、
lib/cmake/KF6JobWidgets/（上游自带 KF6JobWidgetsConfig.cmake，cmake_find_mode=none）。

## 注意事项

1. 上游 KF6JobWidgetsConfig.cmake 自带依赖传播（find_dependency KF6CoreAddons 等），
   与 knotifications 同款用 cmake_find_mode=none 避免被 CMakeDeps 遮蔽。
2. kparts/6.26.0 硬性要求 KF6JobWidgets ≥ 6.26.0（KF_DEP_VERSION 对齐），ohpcd 的
   6.18.0 不满足——本包是 kparts/konversation 链的前置。
3. 未发布 ohpcd 制品仓（合入 main 后由 CI/维护者发布）。
