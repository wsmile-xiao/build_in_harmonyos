# DRAFT: OHOS qtbase 双生态互斥与 KF6 版本闸适配策略

## 现象

依赖 KF6 全家（Config/CoreAddons/DBusAddons/I18n/Holidays）+ Qt6 DBus 的包，
在 OHOS 制品仓上选型时遭遇：

```
ERROR: Version conflict: Conflict between qtbase/6.11.1.1 and qtbase/6.11.1
in the graph. Conflict originates from kdbusaddons/6.29.0
```

## 根因：两个互斥生态

| 生态 | Qt 基座 | KF6 组件 | 备注 |
|------|---------|----------|------|
| A | qtbase/6.11.1（无 DBus） | kconfig/kcoreaddons/ki18n 6.26.0、kholidays 6.28.0、qtpositioning/qtdeclarative 6.11.1 | Qt6::DBus 由 qtbase-sql-dbus/6.11.1 独立包名提供（刻意并存设计）；kdbusaddons 只有 6.18.0 |
| B | qtbase/6.11.1.1 | kdbusaddons 6.29.0 | 其余 KF6 组件尚未在此基座发布 |

conan 禁止两个 qtbase 版本同图。上游 `find_package(KF6 6.26.0)` 版本闸
会拒生态 A 的 kdbusaddons 6.18.0（ConfigVersion: PACKAGE_VERSION <
PACKAGE_FIND_VERSION → NOT COMPATIBLE）。

## 修复策略（生态 A + 版本闸补丁）

1. conanfile 选生态 A：`qtbase/6.11.1` + `qtbase-sql-dbus/6.11.1`（并存）
   + `qtpositioning/6.11.1` + `kdbusaddons/6.18.0` + KF6 6.26 组件
2. 可移植性补丁放宽版本闸：`set(KF6_MIN_VERSION "6.26.0")` → `"6.18.0"`
3. 依据：daemon 唯一用到的 DBusAddons API 是 KDBusService（唯一 D-Bus
   服务注册），KF5 起 API 稳定，6.18.0 功能充分

实证：knighttime 6.7.2（daemon 用 KDBusService），本地 conan create
3/3 上游测试过 + CI（PR #11110，依赖发布后转绿路径已验证）。

## CMake 侧配套（拆分 Qt 模块包的组件解析）

Qt6Config.cmake 按自身前缀解析组件，拆分的 Qt 模块包（qtpositioning/
qtdeclarative/qt6linguisttools）需显式注册：

```python
tc.variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = qtpos_pkg_root
# 且写入 conan_cmakedeps_paths.cmake（CACHE FORCE）
```

## 何时不能走此路

目标包用了 kdbusaddons 6.19+ 新增 API → 只能等生态 B 的 KF6 全家发布。
