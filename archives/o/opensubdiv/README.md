# OpenSubdiv

OpenSubdiv 是 Pixar Animation Studios 开发的开源细分曲面库，实现了高性能的细分曲面评估算法，支持 CPU 和 GPU 并行架构。

## 核心功能

- **Far**: 高级 API，用于细分曲面的数据表示和评估
- **Bfr**: 面评估框架，用于限制曲面表示
- **Vtr**: 低级拓扑表示
- **Sdc**: 细分方案（Catmark、Loop、Bilinear）
- **Osd**: CPU/GPU 评估器（OpenMP、TBB、CUDA、OpenCL、Metal）

## 编译版本

当前已编译版本：3.7.0

## 编译说明

OpenSubdiv 使用 CMake 构建系统。核心库无外部依赖，可选组件包括：
- OpenGL（可视化）
- CUDA/OpenCL/Metal（GPU 加速）
- GLFW（示例程序）
- Ptex（纹理支持）
- TBB/OpenMP（CPU 并行）

在 OpenHarmony 上编译时，需要禁用可选组件（OpenGL、CUDA、OpenCL、GLFW、Ptex 等），只编译核心 CPU 库。

## 应用场景

- 3D 建模和动画软件
- 游戏引擎
- CAD/CAM 系统
- 科学计算可视化

## 官方资源

- 官网：https://opensubdiv.org
- GitHub：https://github.com/PixarAnimationStudios/OpenSubdiv
- 文档：https://opensubdiv.org/docs/intro.html