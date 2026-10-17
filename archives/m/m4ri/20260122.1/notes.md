# m4ri 20260122.1 编译笔记（HarmonyOS PC · 标准 Conan autotools）

> 版本号说明（R37）：上游源码仍为 20260122（conandata.yml 的 URL/sha256 不变）。
> 制品仓已发布 `m4ri/20260122`，且本版修改了配方（tmpfile shim、HarmonyOS 专项
> 测试），cnb.cool 不支持同版本多 revision 并存，按 R37 递增适配修订后缀为
> `20260122.1`。
>
> 下游 brial/1.2.15、m4rie/20250128 仍钉 `m4ri/20260122`：旧制品仍在制品仓且
> 两包的构建验证均基于它，按「让最少的包重建」原则（brial notes 先例）不随
> 本 PR 迁移——否则级联 R37（两包已发布，改 requires 即需各自再 bump）。

## 定位
GF(2) 上的稠密矩阵运算库（Method of Four Russians），产出 `libm4ri.so`。
是 SageMath 系（linbox / fflas-ffpack 等）与 passagemath 的底层依赖。

## 关键适配
- **必须依赖 libpng**：`m4ri/io.c:29` 无条件 `#include <png.h>`，上游 configure
  并未把 PNG 做成可选项，缺头文件直接编译中断（首轮实撞
  `io.c:29:10: fatal error: 'png.h' file not found`）。故 recipe 里 `requires("libpng/1.6.58")`。
- 修 configure 的 umask 077→022（HMDFS E011）
- 删除 `lib/*.la`：其中烤死 libdir 绝对路径，会把下游 libtool 引到 `//lib/` 死路

## 上游测试（make check，15 项 TESTS 真实执行）
- automake TESTS 共 15 个可执行测试（elimination / multiplication / pluq / ple /
  trsm / invert / kernel / misc / …），recipe build() 里 `make check -j1` 真实运行，
  任一失败 make 非零退出，**不允许用 test_package 替代上游测试**。
- 2026-09-29 实测：**15/15 全绿**（`# TOTAL: 15 / # PASS: 15 / # FAIL: 0`）。

## OHOS musl tmpfile() EACCES：上游测试唯一失败项的根因与修复
- 症状：`test_misc` SIGABRT（exit 134），其余 14 项通过。
- 根因链（repro.c 细粒度追踪实锤）：`tests/test_misc.c:60` `FILE *fh = tmpfile()`
  → OHOS musl 的 tmpfile() 硬编码只读 /tmp、忽略 TMPDIR → 恒 EACCES(13) 返回 NULL
  → NULL 传 `mzd_to_png_fh` → libpng `png_init_io` abort。
  同文件**文件路径** PNG 往返正常，崩溃仅在 tmpfile 段——与 E272
  （arm-none-eabi-binutils ctf-compressed）、DRAFT-8959（libei munit）同根因。
- 修复（E272 先例，路径 A 复用）：`tmpfile-shim.c` 恢复 POSIX 语义
  （mkstemp 到 $TMPDIR + 立即 unlink + fdopen "w+b" + FD_CLOEXEC），build() 里
  编译成 `tmpfile-shim.so`，仅 `make check` 期以 shell 前缀注入：
  `LD_PRELOAD=<shim> TMPDIR=<build>/check-tmp make check`。
  **不改上游源码、不改测试期望、不进生产 package**——m4ri 库本体不调用
  tmpfile()，全树仅 test_misc.c:60 一处使用（grep 实证），包消费方不受影响。
- 坑：conan 2.x `self.run(env=[...])` 把 list 项当 env 文件名（binutils 实撞），
  LD_PRELOAD/TMPDIR 必须以命令前缀字符串注入。

## 交叉编译 CPU/编译器探测差异（OHOS aarch64）
- **SSE2**：`__M4RI_HAVE_SSE2=0` 正确——configure 无构建机特征串台；
  m4ri_config.h 的条件启用 `#if defined(__SSE2__)` 在 AArch64 上不成立，双保险。
- **cache 探测**：`/sys/devices/system/cpu/cpu0/cache/` 不存在、sysctl
  `hw.l1dcachesize` 等键 unknown → m4ri_config.h `__M4RI_CPU_L[123]_CACHE=0/0/0`；
  `misc.h:569-599` 编译期把 0 回退为 16K/256K/4M 标准值——安全退化，不 patch，
  正确性由 mul/rank 断言兜底（`m4ri_opt_k` 对 k<2 钳位到 2）。
- **字长/端序**：word=uint64_t、m4ri_radix=64、小端，与 OHOS aarch64 目标一致
  （test_ohos 断言实证）。

## m4ri API 契约（测试期实撞）
- `mzd_transpose` 内核用 RESTRICT 限定 dst/src——**不支持就地转置**，
  `mzd_transpose(T,T)` 静默产出错误结果（test_ohos 首版实撞），须两次独立转置。

## 真机验证
### 2026-08-12（HarmonyOS PC MateBook）
`conan create -pr ohos-native` 通过，test_package 真实计算断言全绿：
`m4ri: I*B==B 通过；rank(I3)=3 通过`（3×3 逐元素校验）。

### 2026-09-29（本机 OHOS aarch64，profile ohos-aarch64）
- `conan create` 全绿：**上游 make check 15/15** + test_package。
- 通用 test.c：I*B==B 逐元素校验、rank(I₃)=3。
- **HarmonyOS PC 专项 test_ohos.c**（13 项断言全过）：
  - OHOS 目标属性：`__OHOS__`/`__OHOS_FAMILY__`/`__MUSL__`/`__aarch64__`、
    小端、word=8 字节、m4ri_radix=64；
  - 探测自洽：SSE2==0（AArch64 正确禁用）、libpng==1；
  - 核心 API 真实运行（70 列跨 64 位字边界）：I₇₀·A==A、rank(I₇₀)=70、
    重复一行后 rank=69、(Aᵀ)ᵀ==A、A+A==0（GF(2) 自逆）、PNG 文件往返逐位相等。
- test_package 坑：`/data/service/hnp/bin/bash` 不存在 → Error 127；
  self.run 本就经 /bin/sh 执行，`${VAR:+:$VAR}` POSIX sh 原生支持，去掉 bash 包装。
- 本机高负载时后台 conan 可能无声死亡（日志停在链接期、无错误输出，疑似 OOM），
  重跑即恢复；长构建建议分阶段确认日志在增长。
