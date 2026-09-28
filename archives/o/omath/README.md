# omath

omath 是一个 header-first 的通用 C++ 数学库，面向游戏/逆向场景的数学与几何计算。

## 功能概述

- 线性代数：`Vector2/3/4`、`Mat<R,C>`、四元数、`std::formatter` 格式化输出
- 三角与角度：`Angle<Type, Min, Max, Flags>`（归一/夹取策略模板）、`ViewAngles`、视角投影
- 碰撞：GJK / EPA、AABB/OBB、线段与射线追踪（`line_tracer`）、`MeshCollider`
- 路径查找与导航网格、A*、射击预测（`projectile_prediction`）
- 模式扫描与 PE/ELF/Mach-O 文件解析（`pattern_scan`、`hashing` 等非模板部分可独立使用）

构建产物为静态库 `libomath.a` + 头文件，无运行期依赖（上游 `vcpkg.json` 只有宿主工具）。

## OHOS 适配要点

1. **编译器**：上游核心模板 `omath::Angle` 的 `Min/Max` 是 C++20 浮点非类型模板参数，
   OHOS SDK 自带 clang 15.0.4 不支持（`sorry, non-type template argument of type 'float' is not yet supported`），
   本包改用 ohpcd 制品仓的 `clang/22.1.8`（`tool_requires`）。**下游消费者若实例化该模板，
   同样需要 clang≥18。**
2. **标准库缺口**：SDK libc++15 缺 `<expected>/<print>/<source_location>/<memory_resource>`，
   本包以同名兼容头随包交付在 `files/compat/`（安装后进入 `include/`）；
   `<format>` 需要 `-fexperimental-library` + `-lc++experimental`（已随 `cpp_info` 传递）。
3. **AVX2**：aarch64 上上游的 `-mavx2` 探测仍返回真，必须显式 `-DOMATH_USE_AVX2=OFF`。
4. **本版本共 2 个补丁**：`patches/0001-tests-CMakeLists.txt.patch`（Conan CMakeDeps 的 gtest 目标名与上游
   vcpkg 假设不符，补 `GTest::*` 包装目标）、`patches/0002-tests-general-mem_fd_helper.hpp.patch`
   （OHOS 禁止经 `/proc/self/fd` 重开 memfd，补运行期回退）——**只动构建接线与测试夹具，不改任何测试用例与
   算法**；其余差异由配方与 `files/compat/` 兼容头承载。
5. **已知限制**：`files/compat/` 的四个同名兼容头随包进入 `include/`，会遮蔽下游对同名标准头的解析；
   它们只在 libc++ 缺这些头的平台（如本 SDK 的 15.0.4）上有意义，目标平台若已原生提供请勿复用。

详细问题/根因/方案对照见 `5.6.0/notes.md`。

## 依赖关系

- 编译依赖：0（可选 `lua`/`sol2`/`safetyhook`/`imgui`/`benchmark` 按上游默认关闭）
- 构建期工具：`clang/22.1.8`（编译器）
- 测试期：`gtest/1.17.0`（上游 GoogleTest 单测）

## 参考资料

- 源码仓库：<https://github.com/orange-cpp/omath>
- 许可证：Zlib（`LICENSE`）
