# Imath

Imath 是一个 C++ 数学库，用于计算机图形学和其他领域的数值计算。它是 OpenEXR 项目的基础数学库，提供了 2D/3D 向量、矩阵、颜色、随机数等数学类型和算法。

## 软件信息

- **官方网站**: https://github.com/AcademySoftwareFoundation/Imath
- **版本**: 3.2.2
- **许可证**: BSD-3-Clause
- **构建系统**: CMake

## 编译版本

| 版本 | 状态 | 编译日期 | 备注 |
|------|------|----------|------|
| 3.2.2 | published | 2026-05-25 | 共享库编译成功 |

## 功能特性

Imath 提供以下核心功能：
- **half 类型**: 16-bit 浮点数类型，用于图像存储
- **向量类型**: Vec2, Vec3, Vec4（支持 int/float/half）
- **矩阵类型**: Matrix22, Matrix33, Matrix44
- **颜色类型**: Color3, Color4
- **几何类型**: Box, Line, Plane, Sphere, Frustum
- **数学函数**: 插值、变换、投影等算法

## 主要用途

- OpenEXR 高动态范围图像格式的基础依赖
- 计算机图形学应用
- 科学计算和数值处理

## 安装

通过 cmd-pkgs 公共安装脚本安装：
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- imath 3.2.2
```

安装后包含：
- 共享库: libImath-3_2.so
- 头文件: Imath/*.h
- pkg-config: Imath.pc
- cmake 配置: ImathConfig.cmake

## 使用示例

```cpp
#include <Imath/ImathVec.h>
#include <Imath/ImathMatrix.h>

using namespace Imath;

Vec3<float> v1(1.0f, 2.0f, 3.0f);
Vec3<float> v2(4.0f, 5.0f, 6.0f);
Vec3<float> v3 = v1 + v2;

Matrix44<float> m;
m.translate(Vec3<float>(1.0f, 0.0f, 0.0f));
```

## 依赖关系

Imath 无外部库依赖，仅需要标准 C++ 库。

## 相关项目

- OpenEXR: 高动态范围图像格式（依赖 Imath）
- OpenImageIO: 图像处理库（可选依赖 Imath）