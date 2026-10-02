# BOOST_INCLUDE_LIBRARIES 漏 header-only 组件：CGAL 找不到 boost/heap、boost/stl_interfaces

## 现象

sfcgal/2.3.0 编译 CGAL 头时报：
```
CGAL/AABB_tree/internal/AABB_ray_intersection.h:27:10: fatal error: 'boost/heap/priority_queue.hpp' file not found
CGAL/Triangulation_2/internal/Polyline_constraint_hierarchy_2.h:29:10: fatal error: 'boost/stl_interfaces/iterator_interface.hpp' file not found
```

## 根因

Boost CMake 构建只把 `BOOST_INCLUDE_LIBRARIES` 里列出的库装到包的 include/ 目录。`heap` 和 `stl_interfaces` 是 header-only 库（无 .so），但它们的 include 目录只有在被列入 `BOOST_INCLUDE_LIBRARIES` 时才会被安装。

之前的组件列表是按「谁链接了 .so」配的，没考虑 CGAL 这种直接 `#include <boost/heap/...>` header-only 头的下游。

## 修复

在 `BOOST_INCLUDE_LIBRARIES` 末尾加 `heap;stl_interfaces`。这两个全 header-only，零新编译时间。

## 教训

- header-only boost 库也必须列进 `BOOST_INCLUDE_LIBRARIES`，否则头文件不安装。
- 下游报 `boost/X.hpp not found` 时，先查这个 X 对应的 boost 库名（X 不等于库名），再看列表里有没有。
