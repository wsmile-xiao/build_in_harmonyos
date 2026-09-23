# libaegis 0.10.3 适配笔记

## 编译环境
- 构建系统: cmake (>= 3.10, 无第三方依赖, 纯 C99)
- 编译日期: 2026-09-10
- 编译器: clang 15 (aarch64-unknown-linux-ohos, musl libc)
- 状态: built

## 上游信息核实

| 项 | 值 | 验证方式 |
|---|---|---|
| 源码 URL | `https://github.com/jedisct1/libaegis/archive/refs/tags/0.10.3.tar.gz` | curl 实测下载 |
| SHA256 | `2f2682c1d08d9a5510caca1c82e3f8ea91f7085fef2ecbed0c398b2a921c79b1` | sha256sum 实测 |
| License | MIT | tarball 内 LICENSE 文件首行 "MIT License" |
| 构建系统 | CMake >= 3.10 (主) / Zig 0.16 (仅测试) | CMakeLists.txt:1, build.zig.zon |
| SONAME | libaegis.so.0 (SOVERSION 0) | CMakeLists.txt `set_target_properties(... VERSION 0.10.3 SOVERSION 0)` |
| 库名 | aegis (target 名) | CMakeLists.txt |
| 依赖 | 无（header-only 使用: stdint.h, stddef.h, arm_neon.h, sys/auxv.h） | CMakeLists.txt 无 find_package |
| 上游测试 | Zig: `zig build test` (main 43 + raf 99 + kdf 2 = 144 个 test) | build.zig |

## CPU 后端审计（核心）

上游 6 个算法变体(aegis128l/128x2/128x4/256/256x2/256x4)各自带多后端，分发机制统一：

### 编译期
- `src/common/cpu.h`: `HAS_HW_AES` 仅当 `__ARM_FEATURE_CRYPTO && __ARM_FEATURE_AES && __ARM_NEON`（或 x86 `__AES__ && __AVX__`）时定义
- OHOS profile 不传 `-march=+crypto`，默认 target aarch64-unknown-linux-ohos 不定义这些宏 → **`HAS_HW_AES` 未定义**
- 无 `HAS_HW_AES` 时每个变体仍编译 `*_neon_aes.c`，但其函数体用 `#pragma clang attribute push(__attribute__((target("neon,crypto,aes"))), apply_to = function)` 包裹，即 **NEON+AES 指令按函数粒度开启**，TU 其他代码不受影响
- 软件后端 `*_soft.c`（bit-sliced AES，softaes.h）恒被编译，作为回落实现
- 交叉架构后端 TU（`*_aesni.c`/`*_altivec.c`/`*_avx2.c`/`*_avx512.c`）在 aarch64 下被各自的 `#if defined(__x86_64__)` / `__ALTIVEC__` 预处理守卫整体排除，**编译为空目标文件**——静态库中 50 个 .obj 有 18 个是这种空壳，属预期而非打包错误

### 运行时
- `src/common/common.h`: `__linux__` → `HAVE_SYS_AUXV_H` + `HAVE_GETAUXVAL`（OHOS/musl 同样命中，getauxval 为 musl 标准符号）
- `aegis_runtime_get_cpu_features()` 在 `aegis_init()` 时调用一次
- aarch64 路径 (`src/common/cpu.c`):
  - `has_neon`: aarch64 恒 1
  - `has_neon_aes`: **无编译期宏时回落 `getauxval(AT_HWCAP) & HWCAP_AES`**，真实内核报告
  - `has_neon_sha3`: 同理回落 `AT_HWCAP & HWCAP_SHA3`；`has_sve2_aes` 用 `AT_HWCAP2`
- 分发 `aegis128l_pick_best_implementation()`: neon_sha3 → neon_aes → soft，按运行时探测结果选择

### 结论（禁止伪造 CPU 特性的合规性）
1. **无伪造**：OHOS 构建不启用编译期 `HAS_HW_AES`，AES 后端是否可用完全由 `getauxval(AT_HWCAP)` 运行时决定
2. **降级安全**：无 AES 硬件的 CPU 上自动用 soft 实现，二进制在两种机器上均正确
3. **本机实测**：OHOS aarch64 开发机运行时探测 `has_neon=1, has_neon_aes=1, has_neon_sha3=1, has_sve2_aes=0`（本 CPU 有 FEAT_AES/FEAT_SHA3、无 SVE2 AES），全部由内核 auxv 报告，test_package 实际走了 NEON 后端加解密
4. x86 侧 `_cpuid` 路径仅 `HAVE_CPUID`（x86 宏）下编译，OHOS aarch64 构建完全不涉及

## 编译步骤

```bash
# 本机即 OHOS aarch64 设备，用 ohos-aarch64 profile
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | KAT `.json.zst` 无法解压（无 zstd 二进制、pip 无 zstandard） | worker 无 zstd 工具链 | 用 pillow 自带 libzstd 经 ctypes `ZSTD_decompressDCtx` 解出 4 文件 484 向量（argtypes 必须显式声明 c_void_p，否则段错误） |
| 2 | 上游 Zig 测试无法运行 | ziglang wheel 0.0.0 空壳无 zig 二进制，网络不可达装不了 zig >= 0.16 | 144 个 Zig test 未在任何环境运行；改为对构建出的 libaegis.so.0.10.3 全量复跑 rooterberg KAT（见下节），test_package 内嵌 KAT 子集保证消费侧覆盖 |
| 3 | 共享库无 DT_SONAME（libaegis.so 直接产出、无版本链） | CMake 无 Platform/HarmonyOS 模块，`CMAKE_SHARED_LIBRARY_SONAME_C_FLAG` 未定义，上游 `set_target_properties(SOVERSION 0)` 不生效 | conanfile generate() 中定义该 flag 为 `-Wl,-soname,`（同 libharu 2.3.0 先例），产出 libaegis.so.0.10.3 + .so.0/.so 符号链，SONAME=libaegis.so.0 |
| 4 | aegis-aead 官方对照哈希无法验证 | github.com 443 超时 | 以 jedisct1/libaegis tarball（已验证 SHA256）为准 |

## 源码修改

无补丁。SONAME 修复仅通过 Conan CMakeToolchain 变量注入，未改动上游源码。

## 上游测试实际运行记录

- 上游入口 `zig build test`（zig >= 0.16.0）：**未运行**——本机与 CI worker 均无可用 zig（0.0.0 空壳 wheel、无网络下载），144 个 Zig test（main 43 + raf 99 + kdf 2）不能声称已跑。
- 替代验证（实际执行，2026-09-10）：对 conan 构建出的 `libaegis.so.0.10.3` 用 ctypes harness 全量复跑上游 rooterberg KAT——与上游 Zig 套件同语义（`aegis128l_decrypt_detached` / `aegis256_decrypt_detached`，valid 解密+明文比对、invalid 拒绝）：
  - 4 组 × 121 向量 = **484**（每组 57 valid + 64 ModifiedTag 负向）
  - valid：**228/228** 解密成功且明文逐字节一致
  - invalid：**256/256** 返回 -1 拒绝
  - 另 6 个 API 守卫负向（aegis128l/256 maclen=15/17/33、clen<maclen）全部 -1
- 结论：KAT 有效负载 484/484 通过；上游 Zig 专有逻辑（streaming、RAF、KDF 单元）未覆盖，已在 manifest validation.pending 标注。

## 验证结果（实测）

```bash
# conan create (static)
libaegis.a: 50 个目标文件（32 个含代码；18 个空壳 = x86 AESNI/AVX/AVX512 与 AltiVec 后端被预处理排除）
include/: 8 个头文件 (aegis.h, aegis128l.h, aegis128x2.h, aegis128x4.h, aegis256.h, aegis256x2.h, aegis256x4.h, aegis_raf.h)

# conan create (shared)
libaegis.so.0.10.3 + libaegis.so.0 -> libaegis.so.0.10.3 + libaegis.so -> libaegis.so.0
readelf -d: SONAME libaegis.so.0; NEEDED libc.so（仅此一项）
readelf -S: .codesign 节存在（36 号 PROGBITS）

# 全量 KAT (ctypes, 见上节): 484/484 + 6/6 负向
# 运行时探测: neon=1 neon_aes=1 neon_sha3=1 sve2_aes=0

# test_package: 37/37 checks passed
#  1    aegis_init 运行时分发
#  2-17 KAT 嵌入向量（4 组 × tcId 1/2/3 valid + tcId 121 负向）
#  18-29 aegis128l/aegis256 roundtrip（mlen=0/1/RATE/RATE+1、adlen、maclen=32）
#  30-32 x2/x4 变体 roundtrip（mlen=0/1/33）
#  33-35 认证失败负向（篡改密文/篡改MAC/错误密钥均 -1）
#  36-37 确定性输出、增量 API 与 one-shot 一致
```

## 依赖版本

无第三方依赖（libc/m 即可）。

## 注意事项

- 不要给全局 flags 加 `-march=+crypto` / `+simd`：会启用编译期 `HAS_HW_AES` 并隐含假定所有目标机有 AES，破坏 soft 回落安全性
- `FAVOR_PERFORMANCE=ON` 移除侧信道缓解，默认 OFF 保持
- 共享库 SONAME=libaegis.so.0（依赖 conanfile 注入的 soname flag，OHOS 下 CMake 自身不生成）；ABI 未承诺稳定，升级版本注意 SOVERSION 变化
- one-shot API 语义：`aegis128l_encrypt(c, maclen, ...)` 把 tag 追加写在 `c[mlen..mlen+maclen]`；对应 `aegis128l_decrypt` 的 `clen` 是 **ciphertext+tag 总长**，tag 位于 `c[clen-maclen]`
- AEGIS 在 draft-irtf-cfrg-aegis-aead 草案中，API 仍可能演进
