# tinygltf

tinygltf 是 Syoyo Fujita 维护的 glTF 2.0 加载器/写出器，header-only
C++11，内嵌 json.hpp 与 stb_image（无外部依赖），支持 ASCII glTF 与
二进制 GLB，含 PBR 材质、皮肤动画等完整 glTF 2.0 核心特性。

## OHOS 适配

- 使用上游 CMake `TINYGLTF_HEADER_ONLY=ON` 模式：INTERFACE 目标 +
  安装 4 个头文件与 CMake 导出，保持 `#include "tiny_gltf.h"` 上游惯例。
- 配方 `build()` 内使用 OHOS profile 编译器编译并运行上游全部测试：
  tests/tester.cc（内嵌 Catch，34 个用例）的 tester 与 tester_noexcept
  两个变体各 303 断言全部通过。
- 提供真实消费者测试：以 TINYGLTF_IMPLEMENTATION 模式解析内嵌最小
  glTF 2.0 资产，5 项断言。

## 依赖

无。

## 参考

- https://github.com/syoyo/tinygltf
