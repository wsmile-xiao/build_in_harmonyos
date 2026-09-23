# ryu

Ryu — 浮点数到最短十进制字符串转换算法的 C 实现（Ryu & Ryu Printf，作者 Ulf Adams）。

- 上游: https://github.com/ulfjack/ryu
- 许可: Apache-2.0 OR Boost（BSL-1.0）双许可
- 本仓适配版本: 2.0

## 包内容

上游使用 Bazel 构建，`ryu/BUILD` 定义了多个独立 cc_library。本包收录上游**默认目标**
`//ryu`：

- 源文件: `ryu/d2s.c`、`ryu/f2s.c`
- 公共头: `ryu/ryu.h`（安装为 `<prefix>/include/ryu/ryu.h`，保留上游 `#include "ryu/ryu.h"` 引用形式）
- 产物: 静态库 `libryu.a`（默认；`shared=True` 时为 `libryu.so`）

公开 API（ryu.h）：

```c
int  d2s_buffered_n(double f, char* result);  /* 返回写入长度 */
void d2s_buffered(double f, char* result);
char* d2s(double f);                          /* 堆分配版本，调用方 free */
int  f2s_buffered_n(float f, char* result);
void f2s_buffered(float f, char* result);
char* f2s(float f);
```

## 上游其他组件（未入包）

- `//ryu:generic_128`（generic_128.c，ryu_generic_128.h）: 通用 128 位实现。
  其 `long_double_to_fd128` 硬编码 x86 80-bit 布局，在 aarch64（IEEE binary128 quad）
  上结果错误（上游可移植性缺陷，详见 2.0/notes.md），故不入包。
- `//ryu:ryu_printf`（d2fixed.c，ryu2.h）: printf 风格定长/指数格式化，aarch64 实测
  上游测试 24/24 通过，如需可另立任务扩展。
- `//ryu:d2s_intrinsics`: 纯头文件算术辅助（static inline）。

## 构建与测试

- 配方: `2.0/conanfile.py`（CMake，自带最小 CMakeLists.txt；上游本身只有 Bazel）
- 测试: `2.0/test_package/`（消费者测试，25 项断言）；上游 gtest 测试运行说明见
  `2.0/notes.md` 与 `2.0/reports/test-report.md`
