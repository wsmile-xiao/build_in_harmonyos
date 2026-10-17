# DRAFT: conan override 解 KF6 线版本冲突（cap 包卡旧版线）

## 场景

KDE Frameworks 6 线升级适配中，目标库 X/6.26 的 KF6 依赖多数已有 6.26 线包，
但个别中间层依赖（本例 kconfigwidgets）在 ohpcd 只有 6.18.0 cap 且其 recipe
锁死 6.18 传递闭包 → 同图双版本 → conan 拒绝。

## 报错签名（可机器匹配）

```
ERROR: Version conflict: Conflict between ki18n/6.26.0 and ki18n/6.18.0 in the graph.
Conflict originates from kiconthemes/6.26.0
```

第二失败模式（写法错误时）：
```
ConanException: Duplicated requirement: kconfig/6.26.0
```

第三失败模式（漏改导出模板时，test_package 阶段）：
```
Could not find a configuration file for package "KF6ConfigWidgets" that is
compatible with requested version "6.26.0".
```

## 根因

1. cap 包（kconfigwidgets/6.18.0）的 conanfile requires 6.18 线传递依赖，
   与 6.26 线包同图必然冲突；
2. conan 2 的 `override=True` 不能与同 ref 的普通 requires 并存（Duplicated）；
3. 上游 CMake 有两处版本地板：项目 CMakeLists.txt 的
   `find_package(KF6ConfigWidgets ${KF_DEP_VERSION})` 和导出的
   `KF6XmlGuiConfig.cmake.in` 的 `find_dependency(KF6ConfigWidgets "@KF_DEP_VERSION@")`
   ——只改第一处，消费者链在 find_dependency 时照样失败。

## 修复方案

- conanfile：cap 包普通声明一次；6.26 线所有包（含非直接依赖如 kcolorscheme/
  kcodecs）用 `override=True` 单声明；
- 源码补丁：两处版本地板同步降到 cap（6.18.0）；
- `--build=missing` 时 cap 包按新 package_id 从源码重建（KF6 框架包分钟级）。

## 兜底

全链降级到 cap 包版本线（ksvg 6.26.0 先例：补丁降 KF_DEP_VERSION 到 6.18.0，
archives/k/ksvg/6.26.0/patches/0001-lower-kf-dep-version.patch）。

## 实证

- kxmlgui 6.26.0（任务 #13725，PR 待建）：本机 conan create 绿，上游 6/6
  autotests passed，kconfigwidgets 重建后 7/7 passed，test_package 1/1 passed。
- verify_builds: CI 构建号待 CI 绿后回填。
