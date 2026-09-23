# libbiosoup（biosoup）

> 生物信息学用的 C++ 头文件数据结构集合。

## 简介

biosoup 是一组 header-only 的 C++ 数据结构，用于生物信息学工具中的存储与记录：

- `biosoup::NucleicAcid`：把 A/C/G/T 以 2 bit 编码压缩存储的核酸序列（含质量分），
  支持 `InflateData()` / `InflateQuality()` / `ReverseAndComplement()`；
- `biosoup::Sequence`：可直接读写 `data`/`quality` 字符串的轻量序列；
- `biosoup::Overlap`：重叠记录（lhs/rhs 区间、score、strand、可选 cigar）；
- `biosoup::Timer`：计时器；
- `biosoup::ProgressBar`：终端进度条。

## OHOS 适配要点

- header-only：包内安装 `include/biosoup/*.hpp`，引用为 `#include <biosoup/nucleic_acid.hpp>`。
- 无外部依赖；使用 `Sequence`/`NucleicAcid` 时需由使用方定义
  `std::atomic<std::uint32_t> biosoup::<Class>::num_objects{0};`。
- 上游测试依赖 GoogleTest（meson subproject），CI 不可用；本包在 `test_package`
  中复用上游期望值做 14 项检查。
- CMake 目标：`biosoup::biosoup`。

## 依赖

| 依赖 | 版本 | 说明 |
| --- | --- | --- |
| （无） | - | 仅 C++ 标准库 |

## 功能验证

```cpp
#include <biosoup/nucleic_acid.hpp>
#include <biosoup/sequence.hpp>
#include <biosoup/overlap.hpp>
#include <biosoup/timer.hpp>

std::atomic<std::uint32_t> biosoup::NucleicAcid::num_objects{0};
std::atomic<std::uint32_t> biosoup::Sequence::num_objects{0};
```

## 参考

- [源码仓库](https://github.com/rvaser/biosoup)
- [上游 README](https://github.com/rvaser/biosoup/blob/master/README.md)
