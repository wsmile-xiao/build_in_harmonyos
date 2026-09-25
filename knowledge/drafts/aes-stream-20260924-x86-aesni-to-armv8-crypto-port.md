# x86 AES-NI intrinsics-only 库的 OHOS arm64 移植：AESE 语义实证与 bit-exact 对拍

> Draft: `DRAFT-AES-STREAM-20260924-AESNI-TO-ARMV8-CRYPTO-PORT`
> Stem: `aes-stream-20260924-x86-aesni-to-armv8-crypto-port` — pairs with the same-stem `.kv`
> 来源任务：aes-stream 20260924 第一轮完整适配（executor pc2-41）

## 基本信息

- **ID**: DRAFT-AES-STREAM-20260924-AESNI-TO-ARMV8-CRYPTO-PORT
- **严重度**: 2
- **类别**: portability|crypto|arm64|intrinsics|ohos-platform
- **触发工具**: clang|conan|make
- **阶段**: compilation|linking|testing
- **验证方式**: FIPS-197 KAT 穷举 + 标量 oracle bit-exact 对拍（未内嵌全文不否定实际运行；对拍日志 sha256 见 attachment 说明）

## 错误特征

首个真实编译错误（OHOS aarch64 目标，clang 15）：

```
clang -c aes-stream.c -O2
→ immintrin.h:14:2: error: "This header is only meant to be used on x86 and x64 architecture"
```

后续全部错误（mmintrin.h / x86gprintrin.h 内联汇编约束）都是同一根因的连锁：
上游 aes-stream.c 的 244 行核心逻辑（AES 密钥扩展、8 路 AES-PRF 流生成、
快速密钥擦除）全部基于 x86 AES-NI intrinsics（`__m128i`、
`_mm_aesenc_si128`、`_mm_aesenclast_si128`、`_mm_aeskeygenassist_si128`）。

## 根因分析

1. 上游只有两种文件：`src/aes-stream.c`（x86-only intrinsics）与
   `src/aes-stream.h`（可移植公开头），**没有任何可移植参考路径**；
2. OHOS PC 目标是 aarch64，`immintrin.h` 在非 x86 上直接 `#error`；
3. 设备 CPU 具备 ARMv8 crypto extension（`/proc/cpuinfo` 含
   `aes pmull` 特性），所以正确做法是 ARMv8 crypto intrinsics
   （`arm_neon.h`：`vaeseq_u8` / `vaesmcq_u8` / `vaesimcq_u8`）移植。

### 关键坑：本平台 AESE 指令语义与 x86 AESENC 相反

实测（原语对照探针）：`vaeseq_u8(d, rk) = ShiftRows(SubBytes(d XOR rk))`，
即 **先 AddRoundKey、再 SubBytes、再 ShiftRows**；而 x86 `AESENC(d, rk)` 是
ShiftRows → SubBytes → MixColumns → AddRoundKey（密钥在最后）。因此：

- 直接套 `vaesmcq_u8(vaeseq_u8(st, rk))`（OpenSSL x86 习惯）在这个平台上
  无法复现标准 AES 轮；
- 把轮密钥做 `InvMixColumns` 变换再进 AESE（另一种常见推导）也实测不命中；
- **唯一命中的组合**（穷举 init/内部轮/末轮 × plain/MC/IMC/ZERO 四种密钥
  处理，共 3×4×4=48 组合对 FIPS-197 KAT 实证）：
  ```
  内部轮: st' = veor( AESMC( AESE(st, 0) ), rk_i )   // AESE(0) 只做 SB+SR
  末  轮: st' = veor( AESE(st, 0), rk_Nr )
  ```
  即让 AESE 以零密钥只贡献 SubBytes+ShiftRows，AESMC 贡献 MixColumns，
  轮密钥用 `veor` 在轮末加入——精确复现标准 AES 轮。

## 方案

1. **先固定 AES 语义**：用 FIPS-197 KAT（AES-128 `69c4e0d8…b4c55a`、
   AES-256 `8ea2b7ca…496089`）穷举候选指令组合，找唯一命中，不靠纸面推导；
2. **写可移植标量参考（oracle）**：逐位镜像上游构造——AES-PRF
   （第 4 轮后中间状态 s 与最终密文 XOR）、counter 增量（低 64 位）、
   快速密钥擦除（counter 高 64 位 bit63 翻转后用输出块重新扩展密钥）；
   先过 FIPS-197 KAT，再与 ARM 移植版做 **bit-exact 对拍**
   （AES-128/256 × 4 seed × 3 长度 137/64/1025，diff 全部为空）；
3. **配方携带移植源文件**：`exports_sources = "src/*"`，
   `build()` 用 `clang -march=armv8-a+crypto` 直接编译
   `aes-stream-arm.c`，产出静态库 + 官方头 + test_package；
4. **上游零测试的处理**：官方源码无任何测试入口（台账见
   `archives/a/aes-stream/20260924/notes.md`），不冒充上游用例；
   鸿蒙专项由 test_package 的 KAT / 确定性 / 非全零 / key-erasure 断言承担，
   双口径统计如实填 0/0 (N/A)。

## 适用边界与反例

- **适用**：仅 x86 SIMD/intrinsics、无构建系统（或构建系统不可用）的
  C/C++ 库移植 OHOS arm64；尤其 AES/AES-PRF/AES-CTR 类实现；
- **反例/不适用**：目标设备无 crypto extension（`/proc/cpuinfo` 无 `aes`）时
  改用可移植标量 AES 回退（本条目 fallback）；已有 `sse2neon` 之类完整
  intrinsics 映射的库不需要逐条手写移植；携带了可移植参考路径的库直接走
  参考路径即可。
- **边界提示**：AESE 语义是平台/工具链相关的（本设备 clang 15 实测为
  key-first），换工具链版本时先用 FIPS-197 KAT 复验一次，别照搬轮函数。

## 验证记录（实际执行）

| 步骤 | 命令 | 结果 |
|------|------|------|
| 首错复现 | `clang -c aes-stream.c -O2` | exit≠0, immintrin.h #error |
| S-box 锚点 | 标量参考自检 sbox(00/01/53/ff) | 63/7c/ed/16 ✓ |
| AES KAT | 标量参考 AES-128/256 加密 | 2/2 ✓ |
| 轮语义穷举 | arm_brute.c 48 组合 | 唯一命中 veor(AESMC(AESE(st,0)),rk) |
| bit-exact 对拍 | diff oracle{10,14}.out arm_{10,14}.out | R10/R14 全部为空 |
| 静态库 | llvm-ar rcs libaes_stream.a | ✓ |
| 消费者冒烟 | consumer_smoke（官方头+静态库） | OK exit 0 |
| conan-verify | G0-G4 + L2/L4/L5 | 全部 PASS |
| W3 本地 CI | conan create + test_package（含 KAT 断言） | PASS，`status: published` |

## 关系

- `similar_to`: E999（FindSSE.cmake 注入 -msse2 至 aarch64）——同为
  "x86 SIMD 头在 aarch64 不可用"，但 E999 触发面是 CMake cache 误判、
  方案是配方层拦截；本条目是 intrinsics 源码级移植 + 指令语义实证；
- `similar_to`: E506（arm_neon 源选择与 CMake 列表不一致）——同为
  arm_neon 相关，但故障面是链接期 undefined symbol，非指令语义；
- `prerequisite_of`: 无；
- `caused_by`: 无（独立移植问题）；
- `conflicts_with`: 无。