# kf5wayland（KWayland）

KDE Frameworks 5 KWayland —— Wayland 协议客户端/服务端库（KWaylandClient / KWaylandServer）。

- 上游：https://invent.kde.org/frameworks/kwayland
- 类型：纯库包（.so），无命令行工具（无需 commands.json）

## 版本索引

| 版本 | 状态 | 谱系 | 说明 |
|------|------|------|------|
| 5.116.0 | built | Qt6（qtbase/6.11.1.2 + qtwayland/6.11.1） | OHOS PC 适配（高难度挑战）：4 补丁修复上游 Qt6 路径 CMake/源码缺陷，ctest 实跑 29/29，test_package 5 断言（含 .codesign 平台断言） |
