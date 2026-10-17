# qtbase-sql-dbus 6.11.1 适配笔记

## 基本信息
- 软件名称: qtbase-sql-dbus（qtbase Sql/DBus 组件变体）
- 版本: 6.11.1
- 构建系统: cmake
- 编译日期: 2026-08-13
- 状态: built
- 上游仓库: qtbase-everywhere-src-6.11.1.tar.xz

## 编译步骤
1. 基于 qtbase/6.11.1 配方复制，name 改为 qtbase-sql-dbus
2. generate() 开启 FEATURE_sql=ON、FEATURE_dbus=ON
3. requirements 添加 dbus/1.14.10（制品仓已有）
4. conan-verify 验证

## 依赖
- dbus/1.14.10（Qt6::DBus 模块所需）

## 关键适配点
- 提供 Qt6Sql/Qt6DBus 组件，供 actiona 的 actions/data（Qt6::Sql）与 actions/system（Qt6::DBus）使用
- 与 qtbase/6.11.1 并存（制品仓已有无 Sql/DBus 的 qtbase），避免 R37 版本冲突

## 最终状态
built（conan-verify 验证中）
---

**编译结束**: 2026-08-13 19:19
**最终状态**: built
