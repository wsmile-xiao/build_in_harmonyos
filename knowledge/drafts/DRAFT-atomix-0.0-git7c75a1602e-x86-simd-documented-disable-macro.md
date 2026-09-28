# Draft: aarch64 上 x86 SIMD 内建头不可用 — 优先使用上游文档化禁用宏

> 对应 `.kv`：`DRAFT-atomix-0.0-git7c75a1602e-x86-simd-documented-disable-macro.kv`
> 来源库：atomix 0.0-git7c75a1602e（BareRose，header-only 混音库）
> 状态：草稿（部分覆盖 DRAFT-jsonifier-neon-cpu-instructions-bits，本轮新增差异待 promote）

## 问题

库默认启用 x86 SIMD 内建（SSE/AVX）时，在 OHOS aarch64 上编译报错：

```
/data/.../xmmintrin.h:14:2: error: "This header is only meant to be used on x86
and x64 architecture"
```

根因：clang 的 `xmmintrin.h`/`mmintrin.h`/`immintrin.h` 仅在 x86/x64 目标可用；
aarch64 无 SSE，遇到即报错。

## 根因

- 库源码（或示例）默认 `#include <xmmintrin.h>` 走 SSE 优化路径；
- OHOS aarch64 工具链目标不支持 x86 intrinsics；
- 若上游已在文档/头注释中提供**禁用宏**（例如 atomix 的 `ATOMIX_NO_SSE`），
  则无需改源码即可走纯 C 路径。

## 方案（推荐顺序）

1. **先查上游文档化禁用宏**：`grep -i "no_sse\|no-sse\|disable.*simd" README.md *.h`
   —— atomix 头注释明确列出 `ATOMIX_NO_SSE`（"Disables all SSE optimizations"）；
2. 编译期定义该宏（`-DATOMIX_NO_SSE` 或消费者源码 `#define ATOMIX_NO_SSE`），
   零补丁完成 aarch64 适配；
3. 仅当上游**没有**文档化禁用开关时，才评估 NEON 移植 / 分支补丁
   （参考 DRAFT-jsonifier-neon-cpu-instructions-bits 的 NEON 路线）。

## 验证（atomix 0.0-git7c75a1602e 实测）

| 项 | 命令 | 退出码 |
|----|------|--------|
| 消费者/示例编译 | `/data/service/hnp/bin/clang -O2 -DATOMIX_NO_SSE test.c -o test` | 0 |
| 运行（基准段） | `./atomix-test mu.ogg so.ogg` | 0 |
| 对照（未定义宏） | 默认编译 → `xmmintrin.h only meant to be used on x86` | 非 0 |

## 适用边界 / 反例

- **适用**：上游提供文档化 SIMD 禁用宏的 C/C++ 库（单文件库常见）；
- **反例/不适用**：上游无任何禁用开关且 SIMD 为功能核心（如图形/编解码加速）——
  此时须 NEON 移植或接受性能差异（见 jsonifier 草稿）；
- **注意**：`ATOMIX_NO_SSE` 只是禁掉 SSE，纯 C 路径功能完整；文档原文提示
  性能约 4 倍差距，属可接受 trade-off，非功能缺陷。

## 查重关系

- `similar_to`：DRAFT-jsonifier-neon-cpu-instructions-bits（NEON 路线）、
  E429-draft-EE6C（zpl.h 同签名）、E006 / E016（disable-asm 家族）
- 与 jsonifier 草稿**互补不冲突**：本候选填补「先查文档化禁用宏」的零成本决策步骤