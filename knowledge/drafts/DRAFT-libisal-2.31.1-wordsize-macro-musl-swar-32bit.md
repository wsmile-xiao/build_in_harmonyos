# 上游 64 位 SWAR 检测用 glibc 私有宏 __WORDSIZE，musl/OHOS 落入 32 位常量分支

- **草稿 ID**: DRAFT-libisal-2.31.1-wordsize-macro-musl-swar-32bit
- **来源**: libisal 2.31.1 HarmonyOS PC 适配（pq_check_test end test 失败 → 纯 C 基础实现互斥实锤 → 宏条件补 __LP64__ 修复）
- **分类**: portability / musl / glibc-macro / swar / gf / raid / upstream-bug
- **状态**: 本地草稿（路径 B 知识库扩展申请中）
- **严重级**: 2（静默数据错误，且是可向上游提交的真 bug）

## 问题 / 错误签名

- `make check` 中 `pq_check_test` 的 end test 阶段失败：`fail end test - offset: 0, len: 1024`（先以 `pq_gen_base` 生成校验数据，再 `pq_check` 验证 GOOD data 却返回非 0）。
- 决定性实验：消费者程序里 `pq_gen_base` 生成 P/Q 后调 `pq_check_base`（**两个都是纯 C 基础实现**）返回 `6 = i|2`，即 **i=4 处 Q 不匹配**——恰为每个 8 字节 SWAR 块的第一个高半字节。
- `-O0` 与 `-O2` 结果相同，排除编译器优化因素。

## 根因

```c
#if __WORDSIZE == 64 || _WIN64 || __x86_64__      // raid_base.c:33 / ec_base.c:182
#define notbit0 0xfefefefefefefefeULL             // 64 位 SWAR 常量
#else
#define notbit0 0xfefefefeUL                      // 32 位常量 ← OHOS 走进这里
#endif
```

`__WORDSIZE` 是 **glibc `<bits/wordsize.h>` 私有宏**，musl 不定义；aarch64 上 `_WIN64`/`__x86_64__` 均为假 → 选中 32 位掩码（`0xfefefefeUL`）配 8 字节 `unsigned long` 的 SWAR 位移运算，掩码只盖住低 32 位 → 每 8 字节块**高 4 字节的 GF(2) 乘法（Q 路径）全错**。

**为什么上游 CI 没发现**：x86_64 有 `__x86_64__` 兜底、glibc 系有 `__WORDSIZE`，唯 **aarch64 + musl**（OHOS、Alpine arm 等）组合暴露。

## 最小修复

```diff
-#if __WORDSIZE == 64 || _WIN64 || __x86_64__
+#if __LP64__ || __WORDSIZE == 64 || _WIN64 || __x86_64__
```

补丁 `0002-fix-64bit-swar-detection-for-musl-aarch64.patch`（raid_base.c + ec_base.c 两处，后者保留小端联合条件）。`__LP64__` 是编译器内建宏，所有 LP64 目标均定义，glibc/x86 行为不变，**适合直接向上游提交**。修复后 frp 真机 make check **16/16 全绿**。

## 推广

- 任何用 `__WORDSIZE` 探测位宽的上游库在 musl/aarch64 都要警惕；`grep -rn "__WORDSIZE"` 是快速排查手段。
- libisal 2.31.1 同款条件还有两处：`ec_highlevel_func.c:453`（x86-only 源文件，aarch64 不编译）与 `igzip/igzip_inflate_test.c:41`（仅测试代码）。
- 备选：配方 `-D__WORDSIZE=64` 强制注入可用但不推荐（污染命名空间、掩盖上游问题）。
