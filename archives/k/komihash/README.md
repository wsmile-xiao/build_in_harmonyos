# komihash

komihash 是 Aleksey Vaneev 维护的快速 64 位哈希函数库，单头文件
（ISO C99，编译 C++ 时自动提供完整 C++ 兼容），同时提供 `komirand`
64 位 PRNG 与流式哈希接口。函数通过全部 SMHasher 与 SMHasher3 测试。

## OHOS 适配

- 上游无构建系统：配方按 header-library 模式打包 `komihash.h`，
  保持 `#include "komihash.h"` 的上游使用惯例。
- 配方 `build()` 内使用 OHOS profile 编译器直接编译并运行上游唯一
  测试程序 `testvec.c`，校验完整向量输出结构。
- 提供真实消费者测试：README 官方参考向量断言、流式与单发一致性、
  `komirand` PRNG 行为等 6 项断言。

## 依赖

无。

## 参考

- https://github.com/avaneev/komihash
