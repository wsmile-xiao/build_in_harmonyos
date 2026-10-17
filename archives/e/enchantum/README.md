# enchantum

[Enchantum](https://github.com/ZXShady/enchantum)（"enchant enum"）是现代 C++17
header-only 编译期枚举反射库：无需宏、无侵入，提供枚举值/名称/位标志的快速轻量
访问（to_string、cast、索引转换、遍历、bitset 适配器等），支持 C++26 反射。

## OHOS 适配

- **构建系统**: CMake（INTERFACE 库，C++17）
- **平台**: HarmonyOS PC（arm64），clang15 + OHOS SDK
- **配方**: `package_type=header-library`，无编译产物，无第三方运行时依赖
- **上游测试**: C++17 规范配置下 362/362 通过（100%）；新增 OHOS aarch64 专项测试 PASS
- **版本**: 0.4.0（上游 tag，无修复后缀）

## 使用

```cpp
#include <enchantum/enchantum.hpp>
enum class Music { Rock, Jazz, Metal };
auto name = enchantum::to_string(Music::Rock);   // "Rock"
```

## 依赖

无第三方运行时依赖（测试依赖 Catch2 / {fmt}，仅上游测试使用）。