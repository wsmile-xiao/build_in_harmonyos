# libigl 2.6.0 适配笔记

## 上游信息

- **项目**: libigl — header-only C++ 几何处理库
- **GitHub**: https://github.com/libigl/libigl
- **Tag**: v2.6.0（发布于 2025-05-15）
- **License**: MPL-2.0（核心），copyleft 目录为 GPL
- **Homepage**: https://libigl.github.io/

## 源码验证

- **URL**: https://github.com/libigl/libigl/archive/refs/tags/v2.6.0.tar.gz
- **SHA256**: fe3bf58571cccbef774947261284ccf6b7fdf04fcab5f7181e31931e42a0b14f
- **验证**: Windows 下载后 sha256 匹配，tar 内含 include/igl/cotmatrix.h 与 tests/include/igl/*.cpp
- **大小**: 约 1.25MB（压缩包）

## 包特性

- **package_type**: header-library（纯头文件，无编译）
- **依赖**: eigen/3.4.0（header-only，已在制品仓，transitive_headers）
- **C++ 标准**: C++17（OHOS profile 兼容）
- **CMake 目标**: igl::core（对齐上游 cmake/igl 用法）
- **补丁**: 无（核心头文件仅依赖 Eigen + STL，无平台相关代码）

## 头文件结构

```text
include/igl/*.h          — 核心（仅 STL + Eigen），如 cotmatrix.h、massmatrix.h
include/igl/copyleft/*   — GPL 模块（CGAL/TetGen 等，需可选依赖，本包不启用）
include/igl/embree/*     — 可选 Embree 光追模块（本包不启用）
```

消费者通过 `#include <igl/cotmatrix.h>` 等使用。

## 上游测试

- 上游测试框架为 Catch2，共 146 个 `tests/include/**/*.cpp` 文件，294 个 `TEST_CASE`。
- 多数用例通过 `test_common::data_path()` 加载网格数据（需下载 libigl-tests-data），部分依赖 CGAL/Embree/TetGen 等可选原生依赖。
- OHOS 适配在 test_package 中 vendor 8 个无数据依赖的子集（accumarray/cat/adjacency/unique/sort/doublearea），其余 286 个作为资源门控排除（total=294 excluded=286），详见 test_package/MANIFEST.yml。
- test_igl.cpp 提供 6 个消费者几何检查（cotmatrix/massmatrix/法线/面积/边长/邻接）。

## 真机验证

- 本轮仅完成未提交工作树，尚未执行 HMBS 真机预检。
- 待 HMBS 回填：conan create 日志中的 ctest 输出与 HMBS 标记行。
