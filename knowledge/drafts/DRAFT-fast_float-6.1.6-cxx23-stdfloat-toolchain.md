# 路径 B 简要草稿大纲 — fast_float 6.1.6：fixedwidthtest 未运行为 OHOS 工具链平台限制

## error_signature
```
clang++ -std=c++23 ... fixedwidthtest.cpp
error: invalid value 'c++23' in '-std=c++23'        # clang 15 无正式 C++23，仅 c++2b 草稿
clang++ -std=c++2b ... fixedwidthtest.cpp
fatal error: 'stdfloat' file not found              # libc++ 无 <stdfloat>
```
上游条件：tests/CMakeLists.txt `CMAKE_CXX_STANDARD>=23` + `cxx_std_23`；源码 `#include <stdfloat>`。

## root_cause
OHOS 工具链（clang 15.0.4，triplet aarch64-unknown-linux-ohos）缺少两项 C++23 前置能力：
1. 编译器不识别 `-std=c++23`（最高仅 c++2b 工作草案，c++23 值被拒，退出码 1）；
2. 配套 libc++ 缺少 `<stdfloat>` 头（c++2b 下 `-include stdfloat` 失败，退出码 1）。
属外部工具链能力阻塞，非 fast_float 源码/recipe/测试缺陷。

## status
external_blocked
- fixedwidthtest 未执行、未通过：当前 OHOS 工具链不具备 C++23 与 `<stdfloat>` 前置能力；
- 不得将未执行项计为通过/失败/跳过，不得宣称上游测试全量通过；
- 未伪造 `<stdfloat>`、未将 c++2b 写成 c++23、未要求修改 fast_float 绕测试、未写成"平台限制已解决"。

## applicability
仅当同时满足：上游要求 C++23（CMAKE_CXX_STANDARD>=23 或 cxx_std_23）+ 源码含 `<stdfloat>`
+ 当前 OHOS 工具链/标准库不具备（clang 无 -std=c++23、libc++ 无 <stdfloat>）。

## counterexamples
- 上游仅要求 C++17/20（如 E096 C++17/20 CMake 标准显式检测）：不适用，不得用 E096 方案冒充；
- 编译失败源于目标库自身语法/链接错误而非工具链能力缺失：不适用；
- 编译器支持 C++23 但标准库缺 `<stdfloat>`（或反之）：仅满足其一仍部分不适用。

## recovery_condition
提供兼容 C++23 且包含 `<stdfloat>` 的 OHOS 工具链后，以 `CMAKE_CXX_STANDARD=23` +
`FASTFLOAT_FIXEDWIDTH_TESTS=ON` 重新配置并构建运行 fixedwidthtest。
该工具链尚未在当前环境验证；恢复条件为待实际验证表述，未宣称 clang16+/GCC13+ 已在本机可用。

## evidence
- R04 实际复现（命令/退出码真实记录，未重跑长时测试）：
  - `-std=c++23` 冒烟 → error: invalid value 'c++23'，退出码 1；
  - `-std=c++2b -include stdfloat` → fatal error: 'stdfloat' file not found，退出码 1；
  - fixedwidthtest 编译（-std=c++23）→ 退出码 1；
- 台账：发现 24 入口级，实际执行 23、通过 23、失败 0，未执行 1（fixedwidthtest，工具链外部阻塞）；
- 本草稿仅表达平台限制候选与恢复路径，未创建正式条目。
