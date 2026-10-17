# DRAFT-E999-draft-8B83：外部框架头依赖消除（error-detection 2.1.1）

> Contributor: pc4-50 (agent 8B83) | Status: Draft | Updated: 2026-09-26
> Source: error-detection 2.1.1 适配（feat/error-detection-2.1.1）
> 对应：`knowledge/drafts/E999-draft-8B83.kv`

## 现象

上游 `err.h` 首行即 `#include "aKaReZa.h"`，该头文件是作者个人框架头：
- **不在 Error_Detection 仓库内**（仓库只有 Sources/err.c + err.h + 文档）；
- 作者的 AVR 变体 `#include <avr/io.h>` / `<util/delay.h>` / `<avr/interrupt.h>`，
  仅 AVR 可编译，OHOS PC（aarch64+musl）必然失败；
- err.c 实际只用到其中的 `bitCheck / bitChange / bitCheckHigh / bitShiftLeft`
  四个位宏与 `uint8_t/uint16_t/uint32_t/bool` 类型。

## 根因

上游公开头依赖**仓库外**的作者框架头，且框架头存在平台专用（AVR-only）变体；
配方无法通过普通依赖解析获得该头，直接编译即报
`fatal error: 'aKaReZa.h' file not found`。

## 方案（portability 补丁内联）

将 `#include "aKaReZa.h"` 替换为：

```c
#include <stdint.h>
#include <stdbool.h>

#define bitSet(_Reg, _Bit)    (_Reg |= (1U << (_Bit)))
#define bitClear(_Reg, _Bit)  (_Reg &= ~(1U << (_Bit)))
#define bitToggle(_Reg, _Bit) (_Reg ^= 1U << (_Bit))
#define bitCheck(_Reg, _Bit)  (((_Reg) >> (_Bit)) & 0x01U)
#define bitChange(_Reg, _Bit, _Value) ((_Value) == 1 ? bitSet(_Reg, _Bit) : bitClear(_Reg, _Bit))
#define bitCheckHigh(_Reg, _Bit)  (bitCheck(_Reg, _Bit))
#define bitShiftLeft(_Reg, _Pos)  ((_Reg) = (_Reg) << (_Pos))
```

位宏定义与作者 STM32 变体（通用版，非 AVR 专用）完全一致，保证算法行为不变。

## 验证

- `conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing` 通过，
  test_package 6 项断言（checkSum8/16/32 + CRC-8/16/32 标准校验向量）全过；
- test_ohos 专项（T1 ELF64 AArch64 / T2 musl / T3 .codesign / T4 无宿主路径 /
  T5 真实 CRC 计算）全部通过。

## 适用边界

- 适用：上游公开头依赖仓库外作者/个人框架头，且所需仅为平台无关宏/类型；
  框架头有 AVR 等平台专用变体。
- 反例：所需头含平台特定寄存器语义（SREG、GPIO 寄存器等）时不能简单内联，
  应走 vendor 头或平台条件编译；若头为大型第三方公共库（如 glib），应作
  独立依赖包处理，不得内联。

## 查重差异

- 与 DRAFT-ohos-public-header-transitive-dep（透传依赖头路径）不同：该条目是
  依赖已发布包的公开头链路径透传问题，本条目是**仓库外未发布个人框架头**
  的消除，方案为内联补丁而非 cpp_info 依赖透传。
- 与 DRAFT-13410-trueprint-libintl-stub-header（sysroot 空壳头）不同：本条目
  是**仓库外缺失头**的消除；libintl 是 sysroot 内空壳头。
- 与 cobs-c 无构建系统条目不同类（构建系统 vs 头依赖）。