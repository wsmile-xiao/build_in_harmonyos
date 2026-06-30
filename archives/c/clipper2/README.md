# Clipper2

Clipper2 是一个高性能的开源多边形裁剪和偏移库（Polygon Clipping and Offsetting Library），由 Angus Johnson 开发，用 C++17 编写。

## 功能概述

- **多边形裁剪**：支持 Intersection、Union、Difference、Xor 四种布尔运算
- **多边形偏移**：支持路径的膨胀/收缩（Minkowski Sum），可自定义偏移距离和圆弧步数
- **路径简化**：SimplifyPaths 移除冗余共线点和微小路径
- **矩形裁剪**：RectClip 快速矩形裁剪优化
- **三角化**：TriangulatePaths 将多边形分解为三角形
- **坐标系支持**：Path64（64位整数坐标，精度最高）和 PathD（双精度浮点坐标）

## OHOS 适配

- **构建系统**：cmake，在 OHOS 上 cmake 会输出 "System is unknown to cmake (HarmonyOS)" 警告但不影响编译（自动 fallback）
- **编译选项**：建议禁用内置测试（`-DCLIPPER2_TESTS=OFF`），因 googletest 依赖 git clone 在 OHOS 上不可用
- **编译结果**：纯静态库（libClipper2.a 和 libClipper2Z.a），无可执行文件
- **零修改编译**：不需要任何源码修改或补丁，cmake -Werror 编译零警告通过
- **USINGZ 库**：Clipper2Z 在 USINGZ 模式下为 Point64 添加 z 属性，适用于 3D 顶点裁剪

## 依赖关系

- **编译依赖**：cmake >= 3.15，C++17 编译器（clang/gcc）
- **运行依赖**：无（纯头文件+静态库，链接时仅需 -lm）
- **测试依赖**：googletest（可选，通过 git clone 获取）

## 参考资料

- 官网：https://www.angusj.com/clipper2/Docs/Overview.htm
- 源码仓库：https://github.com/AngusJohnson/Clipper2
- 许可证：Boost Software License 1.0
