# DRAFT: Qt6DBus 不可消费修复（qtbase 6.11.1 案例）

> **结构化数据**: [DRAFT-qtbase-6.11.1-dbus-reenable.kv](./DRAFT-qtbase-6.11.1-dbus-reenable.kv)
> **类别**: build-system, cmake, conan, qt6 | **路径**: B（知识库扩展）

---

## 问题

已发布 qtbase/6.11.1 制品中 **DBus 功能缺失**，下游模块执行
`find_package(Qt6DBus 6.9.0 REQUIRED NO_MODULE)` 失败：

- 制品无 `libQt6DBus.so`
- 制品无 `lib/cmake/Qt6DBus/Qt6DBusConfig.cmake`
- `package_info()` 无 dbus 组件

这是「已发布但不可消费」，不是「未发布」。

## 根因

配方 `archives/q/qtbase/6.11.1/conanfile.py` 的 `generate()` **硬编码**
`"FEATURE_dbus": "OFF"`（manifest.yaml 同步 `FEATURE_dbus=OFF`）。Qt6DBus
模块未参与构建，故无库文件、无 CMake 配置、无组件元数据。最小 CMake 消费
实证：

```
cmake -S . -B build -DCMAKE_PREFIX_PATH=<已发布qtbase包>/lib/cmake
  CMakeLists: find_package(Qt6 6.9.0 REQUIRED COMPONENTS DBus)
→ CMake Error: Qt6Config.cmake 存在但 Qt6_FOUND=FALSE
  "Failed to find required Qt component 'DBus'.
   Expected Config file at .../lib/cmake/Qt6DBus/Qt6DBusConfig.cmake does NOT exist"
  exit 1
```

## 修复方案

1. `requirements()` 增加 `self.requires("dbus/1.14.10")`（dbus 配方已在
   ohpcd 发布，R35 用 `conan download` 验证二进制可用）。
2. `generate()` 将 `"FEATURE_dbus": "OFF"` 改为 `"ON"`。
3. `generate()` 将 dbus 依赖 `package_folder` 追加进 `CMAKE_PREFIX_PATH`，
   使 Qt 的 `WrapDBus1`→`find_package(DBus1)` 能命中
   `include/dbus-1.0/dbus/dbus.h` 与 `lib/libdbus-1.a`（dbus 配方
   `includedirs = ["include", "include/dbus-1.0"]`）。
4. `package_info()` 新增 dbus 组件：

```python
dbus = self.cpp_info.components["dbus"]
dbus.libs = ["Qt6DBus"]
dbus.requires = ["core"]
dbus.set_property("cmake_target_name", "Qt6::DBus")
```

## 验证证据

| 门禁 | 命令 | 退出码 | 结论 |
|------|------|--------|------|
| 结构/导出 | `conan export .` | 0 | `qtbase/6.11.1#5dd454...` 导出成功 |
| L0i 依赖 | `conan download dbus/1.14.10 -r=ohpcd` | 0 | 二进制含 `dbus.h` + `libdbus-1.a` |
| 依赖图 | `conan graph info . -pr:h ohos-aarch64 -pr:b default` | 0 | requires: dbus/1.14.10 → expat/2.8.2 |
| 消费复现(修复前) | 最小 CMake `find_package(Qt6 ... COMPONENTS DBus)` | 1 | Qt6_FOUND=FALSE, Qt6DBusConfig 缺失（首错） |

> 完整 `conan create`（数小时级）留待后续构建轮在同一 worktree 执行；
> 本轮未伪造构建通过。

## 适用边界

- 适用于所有因 qtbase/qt6 配方 `FEATURE_*` 关闭导致 Qt 组件缺失、下游
  `find_package(Qt6*...)` 不可消费的场景。
- 修复模式通用：定位缺失 config → 查配方 `FEATURE_` 开关 + 依赖声明 →
  开启开关 + 暴露 Conan 依赖给 CMake 探测 + `package_info` 补组件。
- 依赖 dbus 需先发布（L0i），本案例 dbus/1.14.10 已发布。

## 查重结果

- `knowledge/drafts/`：无 qtbase/qt6/dbus 相关既有草稿（grep 无命中）。
- `knowledge/graph/`：无 Qt/dbus 条目；`index.tsv` 无 qtbase/qt6dbus。
- 关联既有条目：`qt5-qtbase 5.15.2.2`（同类 dbus/1.14.10 依赖接入，-dbus 方式）、
  `dbus/1.14.10`（静态库配方）。
- 差异点：本条目针对 **Qt6 CMake 组件体系**（FEATURE_dbus + CMAKE_PREFIX_PATH +
  Qt6::DBus 组件），与 Qt5 qmake/-dbus 方式不同，具备新增知识价值。

---

*生成时间*: 2026-08-29 | *来源*: archives/q/qtbase/6.11.1 (R03 DBus 路径 B 修复)
