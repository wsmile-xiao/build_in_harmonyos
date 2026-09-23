# cppgir

cppgir 是 KDE 维护的 [GObject-Introspection](https://wiki.gnome.org/Projects/GObjectIntrospection)
C++ 绑定生成器：处理 .gir XML 文件，生成命名空间/类/RAII 包装的 C++ 绑定代码。
生成的代码只需 C++14 编译器（fmt 路径为 C++17）+ 被包装的 C 库。

- 上游：https://invent.kde.org/libraries/cppgir
- 许可：MIT
- 构建系统：CMake（上游亦支持 meson）
- 依赖：fmt、boost（header）、expected-lite（子模块）、glib2（测试）

## 适配版本
| 版本 | 状态 | 说明 |
|------|------|------|
| 2.0+git20250629.2a7d9ce | built | Debian 快照版（commit 2a7d9ce），2026-09-11 适配 |
