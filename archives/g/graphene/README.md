# graphene

graphene 是一个轻量级的 2D/3D 数学类型库：点、向量、矩阵、四元数、欧拉角、平面、视锥体、球体、包围盒、射线、矩形、三角形、尺寸（size）等。纯 C 实现，MIT 许可，Meson 构建。

## 功能概述

- 核心数学类型与运算：point/point3d、vec2/vec3/vec4、matrix、quaternion、euler、plane、frustum、sphere、box、ray、rect、triangle、size、simd
- 可选的 GObject 类型（graphene-gobject，基于 gobject-2.0）
- SIMD 加速路径：aarch64 自动启用 NEON；SSE/GCC-vector 路径按编译器探测自动开关

## OHOS 适配要点

- **唯一直接依赖**：`glib2/2.88.0`（经 pkg-config 消费 `glib-2.0`，>= 2.30）
- `PkgConfigDeps` 仅生成 `glib-2.0.pc`；meson 检测 `gobject-2.0` → 配方补转发型 `gobject-2.0.pc`（Requires: glib-2.0）
- 测试依赖 mutest（tarball 内嵌 `subprojects/mutest`），`wrap_mode=nodownload` 离线构建
- 首轮静态构建（`default_library=static`），无 patch，真机 `meson test` 21/21 通过

## 参考资料

- 上游：https://github.com/ebassi/graphene
- 版本：1.10.8（archives/g/graphene/1.10.8）
- 适配记录：1.10.8/notes.md
