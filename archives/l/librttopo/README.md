# librttopo

RT Topology Library — 暴露 API 以使用用户提供的 data store 创建和管理标准（ISO 13249 / SQL/MM）拓扑。代码源自 PostGIS 的 liblwgeom 库，并对其进行增强以提供线程安全性，减少依赖关系并独立于 PostGIS 发布周期。

- 上游: https://gitlab.com/rttopo/librttopo
- 许可证: GPL-2.0-or-later
- 构建系统: CMake（原 autotools，OHOS 缺 aclocal 改用 CMake）
- 依赖: geos/3.13.0

## 版本

- 1.1.0 — 2026-07-29 适配 HarmonyOS PC (arm64)
