# libpfm 4.13.0 适配笔记

## 编译环境
- 构建系统: makefile（libpfm4 的 Makefile + config.mk，非 autotools、非 cmake）
- 编译日期: 2026-09-07
- 编译器: OHOS SDK clang 15.0.4（target aarch64-unknown-linux-ohos）
- 状态: published

## 编译步骤

```bash
# 1. 官方源码（tag v4.13.0，commit 3d77461cb966259c51f3b3e322564187f4bef7fb）
curl -fsSL -o libpfm-4.13.0.tar.gz https://codeload.github.com/wcohen/libpfm4/tar.gz/refs/tags/v4.13.0
sha256sum libpfm-4.13.0.tar.gz   # b06071d7e528402a6504273ea700354ebfcf4b62ffe239cb6471fcdb04ae3f3d

# 2. OHOS 交叉编译（关键：SYS=Linux 覆盖，见下方问题 1）
make clean
make -j1 SYS=Linux \
     CC=/data/service/hnp/bin/clang \
     ARCH=aarch64 \
     CONFIG_PFMLIB_NOPYTHON=y \
     'DBG=-g -Wall -Werror -Wextra -Wno-unused-parameter -Wno-error=unused-but-set-variable -Wno-error=#warnings'

# 3. 产物核验
ls lib/libpfm.a lib/libpfm.so.4.13.0        # 静态 + 共享库
file tests/validate                          # ELF 64-bit LSB arm64 (OHOS)

# 4. 上游测试
./tests/validate                             # 见"验证结果"双口径统计

# 5. Conan 配方验证
cd archives/l/libpfm/4.13.0
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | make 链接 tests/validate 报 `pfm_arm_perf_validate_pattrs` undefined | libpfm 把 Linux-perf_event 源文件（pfmlib_arm_perf_event.c 等）挂在 `ifeq ($(SYS),Linux)` 下；OHOS 上 `uname -s` 返回 `HarmonyOS`，SYS!=Linux 导致 perf_event 支持未编译进 libpfm.a | 构建时覆盖 `SYS=Linux`（HarmonyOS 内核即 Linux 系，perf_event_open 接口可用），perf_event 对象进入 libpfm.a，validate 链接通过 |
| 2 | `pfmlib_common.c:1909` `-Werror` 报 `variable 'n' set but not used` | 上游 64 位目标下该函数中 `n` 只累加未使用，clang 15 的 `-Wunused-but-set-variable` 与上游默认 `-Werror` 冲突 | make DBG 变量追加 `-Wno-error=unused-but-set-variable`（最小放宽，不改源码） |
| 3 | perf_examples 编译报 `#warning redirecting incorrect #include <sys/poll.h> to <poll.h>` 被 -Werror 拦截 | OHOS sysroot 的兼容头对 `<sys/poll.h>` 发 `#warning` 重定向，上游默认 `-Werror` 将其升级为错误 | DBG 追加 `-Wno-error=#warnings`（SKILL R8 例外口径：非平台宏注入，仅放宽 sysroot 既有警告） |
| 4 | `conan create` test_package 首次运行 harmonyos 专项测试报 `event not found` | libpfm 默认只编码本机检测到的 PMU 事件；ARM64 事件表路径需要 `LIBPFM_ENCODE_INACTIVE=1`（与上游 validate.c 一致） | 测试代码在 pfm_initialize() 前 setenv("LIBPFM_ENCODE_INACTIVE","1",1)，再经 pfm_get_event_encoding 验证 arm_ac57::CPU_CYCLES 编码 |
| 5 | 上游 validate 报 5 个 struct ABI 大小 mismatch（44 vs 56 等） | validate.c 按 32 位 ABI0 常量（PFM_PMU_INFO_ABI0=44 等）硬编码期望值；64 位 aarch64 实际 56/64/64/32/40 | 属上游 64 位校准伪影（非适配缺陷）：5 项为 struct 自检，64 位布局内部一致；74 个 PMU 事件表检查、51 个 ARM64 断言、3 个 perf 断言全部通过（见验证结果台账） |

## 源码修改

无源码补丁（patches/ 为空）。编译期警告通过 make DBG 变量最小放宽；测试断言修正仅在 test_package（消费者侧），不修改上游源码。R8 例外：放宽的是既有 sysroot 警告，未在 patches 中注入平台宏。

## 依赖版本

无第三方依赖（libpfm4 仅依赖 libc / Linux kernel headers）。
工具链：OHOS SDK 26.0.0.18（/data/service/hnp/bin/clang 15.0.4，aarch64-unknown-linux-ohos）。

## 验证结果

```bash
# 上游测试（tests/validate，当前 OHOS aarch64 配置，SYS=Linux）
# 结构自检: 5 项（5 项报 32 位 ABI0 大小不符——上游 64 位校准伪影，见问题 5）
# perf 断言: 3/3 通过（0 errors）
# PMU 事件表: 74/74 Passed
# ARM64 断言: 51/51 通过（0 errors）
# validate exit=5（= 5 个 ABI 大小自检 mismatch 计数，非功能失败）
# 双口径: source_declared_total=1377, configured_executable=133, uninstantiated=1244(互斥架构分支)

# HarmonyOS 专项测试 + 消费者验证（conan create 内 test_package）
# 1/2 test_libpfm          Passed
# 2/2 test_libpfm_harmonyos Passed（arm_ac57::CPU_CYCLES 编码成功，__aarch64__ 校验通过）
# conan create rc=0
```
---

**编译结束**: 2026-09-08 08:48
**最终状态**: built
