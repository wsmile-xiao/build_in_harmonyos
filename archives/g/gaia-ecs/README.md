# gaia-ecs

**gaia-ecs** 是一个用 C++17 编写的简单而强大的实体组件系统（ECS）框架，
由 Richard Biely 开发。面向游戏与数据导向（DOD）场景，支持实体生命周期、
组件存储、关系（Parent/ChildOf）、Prefab、查询（Query）、观察者（Observer）、
序列化、多线程任务调度等核心能力，并提供单头文件（single_include/gaia.h）。

- 上游仓库: <https://github.com/richardbiely/gaia-ecs>
- 许可证: MIT
- 构建方式: header-only（CMake INTERFACE 库，无编译产物）
- HarmonyOS PC 适配: 以 `package_type=header-library` Conan 配方发布
  `single_include/` 头文件，导出 CMake target `gaia::gaia`；详见 `1.0.0/notes.md`。

## 版本

| 版本 | 状态 | Conan 引用 |
|------|------|-----------|
| 1.0.0 | built | `gaia-ecs/1.0.0` |