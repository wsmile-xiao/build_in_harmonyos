# pcg-cpp

pcg-cpp 是 Melissa O'Neill 维护的 PCG 伪随机数生成器 C++ 实现家族，
header-only（C++11），提供 pcg8/16/32/64/128 各尺寸与 _once_insecure/
_oneseq/unique/fast/k*/c* 等变体，附 pcg_extras 实用工具（seed_seq_from、
shuffle 等）。可通过全部 TestU01（SmallCrush/Crush/BigCrush）测试。

## OHOS 适配

- 上游为头文件库：配方按 header-library 模式打包 `include/*.hpp`，
  保持 `#include <pcg_random.hpp>` 的上游使用惯例。
- 配方 `build()` 内使用 OHOS profile 编译器编译 test-high/ 全部 42 个
  上游 check-* 测试程序并运行其中 41 个，独立 diff 校验 40 个 golden
  输出全部一致（check-pcg32_unique 未被上游脚本调用）。
- 提供真实消费者测试：pcg32/pcg64 上游 golden 序列复现、backstep 回退
  重放、pcg_extras 重播种共 4 项断言。

## 依赖

无。

## 参考

- https://www.pcg-random.org
- https://github.com/imneme/pcg-cpp
