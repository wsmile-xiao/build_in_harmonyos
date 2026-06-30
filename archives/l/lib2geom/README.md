# lib2geom

**描述**: 2D几何计算库，提供高级几何算法和数据结构

**官网**: https://gitlab.com/inkscape/lib2geom

**版本**: 1.4

**分类**: Library/Geometry

---

## 简介

lib2geom 是一个用于2D几何计算的C++库，由 Inkscape 项目开发并维护。它提供了丰富的几何算法和数据结构，包括：

- **基本几何对象**: Point、Line、Rect、Ellipse、Bezier曲线等
- **路径操作**: Path构建、变换、相交计算
- **SVG支持**: SVG路径解析和生成
- **高级算法**: 几何变换、曲线拟合、形状分析

## 编译状态

| 版本 | 状态 | 编译日期 | 平台 |
|------|------|----------|------|
| 1.4 | ✅ published | 2026-05-30 | OpenHarmony |

## 依赖

- **必需依赖**:
  - GSL 2.8 (GNU Scientific Library)
  - Boost 1.87.0
  - double-conversion 3.3.1
  - ragel 6.10

- **可选依赖**:
  - GTK3 (GUI功能)
  - Cairo (图形渲染)

## 应用场景

- SVG路径处理
- 2D图形编辑器开发
- 几何计算和变换
- CAD/CAM工具
- Inkscape 图形编辑器（主要依赖）

## 使用方法

### 安装

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- lib2geom 1.4
```

### 编译链接

```bash
clang++ -std=c++17 \
  -I$HOME/usr/local/include/2geom-1.4.0 \
  -I$HOME/usr/local/include \
  -L$HOME/usr/local/lib \
  your_program.cpp \
  -l2geom -lboost_system -lgsl -lgslcblas -ldouble-conversion -lm \
  -o your_program
```

### 示例代码

```cpp
#include <2geom/point.h>
#include <2geom/rect.h>

using namespace Geom;

int main() {
    Point p1(10, 20);
    Point p2(30, 40);
    Point p3 = p1 + p2;  // (40, 60)

    Rect rect(Point(0, 0), Point(100, 100));
    double area = rect.area();  // 10000

    return 0;
}
```

## 注意事项

1. lib2geom 编译为静态库（lib2geom.a），无可执行文件
2. 使用前需设置 `PKG_CONFIG_PATH=$HOME/usr/local/lib/pkgconfig`
3. GSL预编译包不完整，需手动编译完整版本

## 版权

- LGPL-2.1 或 MPL-1.1 双许可
- Copyright 2007-2014 Inkscape Authors

## 维护者

- Inkscape 开发团队
- OpenHarmony 适配: OpenDesk AI 智能体

---

**最后更新**: 2026-05-30