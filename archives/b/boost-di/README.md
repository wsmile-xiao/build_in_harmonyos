# boost-di (Boost.DI)

C++14 Dependency Injection 库（Boost.Ext.DI），header-only，作者 Kris Jusiak。

- 官方仓库: https://github.com/boost-ext/di
- 许可证: BSL-1.0
- 当前版本: 1.3.2（标签 v1.3.2，release commit 20b6454c889f23c1e7c9eb5136cd7e3d6f6d718d）
- 适配状态: pending（bootstrap 骨架已建，adapt 未开始）

## 适配要点

- header-only：无编译产物，仅打包 `include/boost/di.hpp` 与 `include/boost/di/`
- 上游 CMake 仅用于构建测试/示例
- 官方仓库为 boost-ext/di（非 boostorg/di）

详见 `1.3.2/notes.md`。
