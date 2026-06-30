# CGAL - Computational Geometry Algorithms Library

CGAL 是计算几何算法库（Computational Geometry Algorithms Library），提供高效可靠的几何算法实现。

## 主要功能
- **三角剖分**：2D/3D Delaunay 三角剖分
- **多边形处理**：布尔运算、偏移、简化
- **网格生成**：表面重建、体积网格
- **几何优化**：凸包、最近邻、空间搜索
- **曲线曲面**：样条曲线、曲面拟合

## 编译状态
| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 6.1.1 | built | 2026-05-21 | header-only |

## 依赖
- GMP 6.3.0（必需）
- MPFR 4.2.1（必需）
- Boost（可选）
- zlib（可选）

## 使用方法
CGAL 是 header-only 库，使用时只需包含头文件：
```cpp
#include <CGAL/Simple_cartesian.h>
#include <CGAL/Point_2.h>

typedef CGAL::Simple_cartesian<double> Kernel;
typedef Kernel::Point_2 Point_2;

Point_2 p(1.0, 2.0);
```

CMake 项目使用：
```cmake
find_package(CGAL REQUIRED)
add_executable(myapp main.cpp)
target_link_libraries(myapp CGAL::CGAL)
```

## 许可证
GPL-3.0 OR LGPL-3.0

## 官方文档
https://doc.cgal.org/