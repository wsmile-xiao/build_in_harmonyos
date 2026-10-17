# libaegis 0.10.6 适配笔记

## 编译环境
- 构建系统: cmake (>= 3.10, 无第三方依赖, 纯 C99)
- 编译日期: 2026-09-27
- 编译器: clang 15 (aarch64-unknown-linux-ohos, musl libc)
- 状态: built

## 上游信息核实

| 项 | 值 | 验证方式 |
|---|---|---|
| 源码 URL | `https://github.com/aegis-aead/libaegis/archive/refs/tags/0.10.6.tar.gz` | curl 实测下载 |
| Tag commit | `3992508d3c9dfd87ed7ed769e65bb26a9281e592`（annotated tag `0.10.6` -> `c331001cba8cf148e79700e3c74d7c6994950b82`） | GitHub API git/ref/tags + git/tags 实测 |
| SHA256 | `aaa17587424e1f4992b04abb4efa32c406965625f60fe34857c8679eea9fb7ce` | sha256sum 实测（官方 tag tarball） |
| License | MIT | tarball 内 LICENSE 文件首行 "MIT License" |
| 构建系统 | CMake >= 3.10 (主) / Zig 0.16 (仅测试) | CMakeLists.txt:1, build.zig.zon |
| SONAME | libaegis.so.0 (SOVERSION 0) | CMakeLists.txt `set_target_properties(... SOVERSION 0)` |
| 库名 | aegis (target 名) | CMakeLists.txt |
| 依赖 | 无（header-only 使用: stdint.h, stddef.h, arm_neon.h, sys/auxv.h） | CMakeLists.txt 无 find_package |
| 上游测试 | Zig: `zig build test` (main 43 + raf 99 + kdf 2 = 144 个 test) | build.zig |

## CPU 后端审计（核心，与 0.10.3 一致）

- 编译期 `HAS_HW_AES` 仅当 `__ARM_FEATURE_CRYPTO && __ARM_FEATURE_AES && __ARM_NEON` 时定义；OHOS profile 不传 `-march=+crypto` → 未定义
- NEON+AES 后端按函数粒度 `#pragma clang attribute target("neon,crypto,aes")` 开启，soft 后端恒编译
- 运行时 `getauxval(AT_HWCAP) & HWCAP_AES` 决定 has_neon_aes；本机实测 neon=1, neon_aes=1, neon_sha3=1, sve2_aes=0
- 交叉架构 TU（aesni/altivec/avx2/avx512）被预处理排除 → 静态库中 18 个空目标文件属预期
- 禁止给全局 flags 加 `-march=+crypto` / `+simd`（会启用编译期 HAS_HW_AES，破坏 soft 回落）

## 编译步骤

```bash
# 本机即 OHOS aarch64 设备，用 ohos-aarch64 profile
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 Zig 测试无法运行 | ziglang wheel 0.0.0 空壳无 zig 二进制，网络不可达装不了 zig >= 0.16 | 144 个 Zig test 未在任何环境运行；改为对构建出的 libaegis.so.0.10.6 全量复跑 rooterberg KAT（见下节），test_package 内嵌 KAT 子集保证消费侧覆盖 |
| 2 | 共享库无 DT_SONAME（libaegis.so 直接产出、无版本链） | CMake 无 Platform/HarmonyOS 模块，`CMAKE_SHARED_LIBRARY_SONAME_C_FLAG` 未定义，上游 `set_target_properties(SOVERSION 0)` 不生效 | conanfile generate() 中定义该 flag 为 `-Wl,-soname,`（同 libharu 2.3.0 先例），产出 libaegis.so.0.10.6 + .so.0/.so 符号链，SONAME=libaegis.so.0 |

## 源码修改

无补丁。SONAME 修复仅通过 Conan CMakeToolchain 变量注入，未改动上游源码。

## 上游测试实际运行记录

- 上游入口 `zig build test`（zig >= 0.16.0）：**未运行**——本机与 CI worker 均无可用 zig（0.0.0 空壳 wheel、无网络下载），144 个 Zig test（main 43 + raf 99 + kdf 2）不能声称已跑。
- 替代验证（实际执行，2026-09-27）：对 conan 构建出的 `libaegis.so.0.10.6` 用 ctypes harness 全量复跑上游 rooterberg KAT——与上游 Zig 套件同语义（`aegis128l_decrypt_detached` / `aegis256_decrypt_detached`，valid 解密+明文比对、invalid 拒绝）：
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
libaegis.so.0.10.6 + libaegis.so.0 -> libaegis.so.0.10.6 + libaegis.so -> libaegis.so.0
readelf -d: SONAME libaegis.so.0; NEEDED libc.so（仅此一项）
readelf -S: .codesign 节存在

# 全量 KAT (ctypes, 见上节): 484/484 + 6/6 负向
# 运行时探测: neon=1 neon_aes=1 neon_sha3=1 sve2_aes=0

# test_package: 37/37 checks passed
```

## 依赖版本

无第三方依赖（libc/m 即可）。

## 注意事项

- 不要给全局 flags 加 `-march=+crypto` / `+simd`：会启用编译期 `HAS_HW_AES` 并隐含假定所有目标机有 AES，破坏 soft 回落安全性
- `FAVOR_PERFORMANCE=ON` 移除侧信道缓解，默认 OFF 保持
- 共享库 SONAME=libaegis.so.0（依赖 conanfile 注入的 soname flag，OHOS 下 CMake 自身不生成）；ABI 未承诺稳定，升级版本注意 SOVERSION 变化
- one-shot API 语义：`aegis128l_encrypt(c, maclen, ...)` 把 tag 追加写在 `c[mlen..mlen+maclen]`；对应 `aegis128l_decrypt` 的 `clen` 是 **ciphertext+tag 总长**，tag 位于 `c[clen-maclen]`
- AEGIS 在 draft-irtf-cfrg-aegis-aead 草案中，API 仍可能演进
---

**编译结束**: 2026-09-28 11:31
**最终状态**: built
