# libGDSII - GDSII 几何文件读取库

## 简介
libGDSII 是一个 C++ 库，用于读取（及基础写入）GDSII 版图数据文件，提供多边形/文本元素的平铺提取 API，常与 scuff-em 等电磁仿真工具配合使用。

## 功能
- 解析 GDSII binary 文件（structure/boundary/text/sref 等元素）
- 按图层提取多边形（GetPolygons）与文本字符串（GetTextStrings）
- 层级结构平展（Flatten）、几何查询（PointInPolygon）
- 附带 GDSIIConvert 工具与 Gmsh 格式导出

## 上游
- https://github.com/HomerReid/libGDSII （tag 0.2）
