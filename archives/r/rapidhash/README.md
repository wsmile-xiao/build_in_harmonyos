# rapidhash

Very fast, high quality, platform-independent 64-bit hash functions
(header-only C/C++)。

- 上游仓库: https://github.com/Nicoshev/rapidhash
- 版本: 3（上游唯一发布形态为 git tag `rapidhash_v3`）
- 许可证: MIT（bench/ 与 collisions/ 附属研究工具分别为 GPL-2.0/BSD，不随包分发）
- 类型: header-only（仓库根一对头文件：`rapidhash.h` + 伴随 `secret.h`）
- 构建系统: 无（上游无任何构建脚本；包只安装头文件）

## 用途

三个哈希函数家族：`rapidhash`（通用）、`rapidhashMicro`（≤512 字节更快）、
`rapidhashNano`（嵌入式/移动端，≤48 字节最快）。API 形如
`uint64_t rapidhash(const void *key, size_t len)`，另有 `_withSeed` 变体。
仅依赖 `<stdint.h>`/`<string.h>`；C99 与 C++11+ 均可编译（本设备实测
c11/c++11/c++17/c++20 全通过）。

## 在 OpenHarmony / HarmonyOS PC 上

- 包安装路径：`include/rapidhash/rapidhash.h` 与 `include/rapidhash/secret.h`
  （命名空间化安装，避免通用名 `secret.h` 污染消费方 include 路径）。
- 消费方：`find_package(rapidhash REQUIRED)` + `target_link_libraries(... rapidhash::rapidhash)`，
  然后 `#include <rapidhash/rapidhash.h>`。
- `rapidhash.h` 的 API 虽以 `constexpr` 标注，但 internal 含
  `(const void*)` 转换，C++17/20 常量表达式不可求值（P2738 需 clang>=19）；
  编译期 `static_assert` 求值会失败，KAT 断言请走运行期（见知识草稿 E560）。
- `secret.h` 非自包含：需先包含 `rapidhash.h` 再包含 `secret.h`（其
  `wyrand` 依赖 `rapid_mix`）。

## 使用

```cmake
find_package(rapidhash REQUIRED)
target_link_libraries(my_target PRIVATE rapidhash::rapidhash)
```

```c
#include <rapidhash/rapidhash.h>
uint64_t h = rapidhash(data, len);
```
