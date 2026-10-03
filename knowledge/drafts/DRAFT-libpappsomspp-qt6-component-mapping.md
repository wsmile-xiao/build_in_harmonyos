# E6401：Qt6 组件多包拼装的 CMake 前缀解析——qtbase-sql-dbus 空壳包陷阱

## 错误特征

适配 Qt6 系三方库（0.11.x 起 Qt6::Core5Compat 线）时，conan 本机构建通过但 CI 失败，或消费端 test_package 配置失败，典型报错三形态：

```
CMake Error: Could NOT find Qt6Sql (missing: Qt6Sql_DIR)
Found package configuration file: .../qtbasc7fd.../lib/cmake/Qt6/Qt6Config.cmake
Expected Config file ".../qtbasc7fd.../lib/cmake/Qt6Sql/Qt6SqlConfig.cmake" does NOT exist
```

```
CMake Error at .../PappsoMSpp-Target-release.cmake (set_property):
  The link interface of target "libpappsomspp_DEPS_TARGET" contains:
    qtbase::qtbase  but the target was not found.
```

```
Error relocating .../libQt6Core.so.6: _ZNSt11logic_errorC2EPKc: symbol not found
（运行期：Qt .so 找不到 libc++——LD_LIBRARY_PATH 未注入依赖 lib + /system/lib64）
```

## 根因（平台机制因果）

OHOS 制品仓 Qt6 按组件拆包：`qtbase` / `qt5compat`（Core5Compat）/ `qtbase-sql-dbus`（Sql/DBus）/ `qtdeclarative`（Qml）/ `qtsvg`（Svg）。两个机制叠加成陷阱：

1. **qtbase-sql-dbus 是空壳树**：其 `lib/cmake/` 下有 `Qt6/Qt6Config.cmake`、`Qt6Sql/` 目录名，但 `Qt6SqlDependencies.cmake` 等 find_dependency 链文件是空壳（只含插件级 config）。**Qt6Sql/Qt6Svg 的完整 config 只在 qtbase 本尊包**。
2. **PREPEND 语义反转**：conan_cmakedeps_paths.cmake 按顺序执行 `list(PREPEND ...)`——**后写的行最终排最前**。qtbase 的 PREPEND 若先写，会被后续（quazip shim/generators 等）压后，空壳包的 Qt6Config 抢先命中。
3. CI 图可能混入本地没有的传递依赖（qtbase-sql-dbus 经 qtdeclarative 等），本地绿≠CI 绿。

## 解法（代码级）

**产出端（conanfile generate）**——qtbase 路径行最后追加（见 .kv solution 块完整代码）。

**消费端（test_package）**：
- `QT_ADDITIONAL_PACKAGES_PREFIX_PATH`（Qt 官方变量）必须在第一次 `find_package(Qt6 ...)` **之前**设置，指向 qtsvg/qtdeclarative/qt5compat/qtbase-sql-dbus 各包的 lib/cmake——Qt6Config 靠它解析住在 qtbase 之外的组件
- 上游只装 StaticTargets（无 install(EXPORT) config）时：直接 `include(.../XxxStaticTargets.cmake)` + 手工加载全部传递依赖 config + conan target 别名映射（`zstd::libzstd → Zstd::Zstd`）

**运行端（ctest/test 二进制）**：
```python
# conanfile build()/test_package test()：
runtime_env = Environment()
for dep in self.dependencies.values():
    if dep and dep.package_folder:
        runtime_env.prepend_path("LD_LIBRARY_PATH",
                                 os.path.join(dep.package_folder, "lib"))
runtime_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")  # OHOS Qt .so 的 libc++
```

## 降级方案

包无 config 只有 .a：StaticTargets 直连（见 .kv fallback）。

## 红线

- 不要试图给 qtbase-sql-dbus 补 config（那是平台包内部，改不了）
- 不要用 CMAKE_PREFIX_PATH 硬编码包 hash 路径（CI/本地 hash 不同）——必须经 `self.dependencies.get(...)` 动态解析
- ENV 注入时传**纯路径列表**（分号分隔），不要传整个 cmake 命令行文本

## 实证

- PR #12063 libpappsomspp 0.11.26：本机 conan create 60/60 TEST_CASE + 消费者 3/3（Qt6 线四件链主件）
- PR #11883 libodsstream 0.9.18：CI 环境 sql-dbus 空壳抢 include→qtbase 前置修复（87349f23）→CI passed
- 链先例：qtbase-sql-dbus 空壳在 test_package（本地复现）与 CI（传递依赖混入）两个场景双实锤
