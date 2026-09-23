# earcut

## 简介
mapbox/earcut.hpp：单文件 header-only 的 C++ 多边形三角剖分库（earcut.js 的 C++ 移植版），
在 O(n log n) 时间内对二维多边形（含洞）进行三角剖分，无任何第三方运行时依赖。

## 功能概述
- 单头文件 `include/mapbox/earcut.hpp`（1207 行，C++14 兼容）
- 支持带洞多边形、退化/共线输入、Steiner 点与 `mapbox::refine()` Delaunay 后处理
- 可配置索引类型（默认 `uint32_t`，支持大顶点数）
- ISC 许可证

## OHOS 适配
### 适配要点
1. **无源码改动**：纯算法 header-only 库，仅提供头文件，HarmonyOS aarch64 直接编译通过
2. **v3.2.3 现代化 API**：`mapbox::earcut<N>(poly)` 直接返回 `std::vector<N>` indices
   （旧版 2.x 为 `earcut(indices, poly)` 双参形式），`mapbox::refine(triangles, coords)` 可选后处理
3. **上游测试网络依赖裁剪**：上游 CMakeLists 无条件 `FetchContent_MakeAvailable(earcut_js/picojson)`，
   HarmonyOS 无 GitHub 直连环境下打补丁（0001-guard-fixtures-fetchcontent.patch）把 fixtures 拉取
   包进 `EARCUT_BUILD_TESTS/BENCH/VIZ` 条件块，纯 header 打包不再需要网络
4. **测试验证**：上游 gtest 全量 69/69 通过；新增消费者冒烟测试 + HarmonyOS 专项测试
   （瓦片级大坐标/共线退化/70000 顶点 uint32 索引）全部通过

## 构建与测试
```bash
# 直接使用（header-only）
#include <mapbox/earcut.hpp>

# 运行上游测试（需网络拉取 earcut.js fixtures/googletest）
cmake -DEARCUT_BUILD_TESTS=ON -DEARCUT_BUILD_BENCH=OFF -DEARCUT_BUILD_VIZ=OFF -B build && cmake --build build && ctest --test-dir build
```