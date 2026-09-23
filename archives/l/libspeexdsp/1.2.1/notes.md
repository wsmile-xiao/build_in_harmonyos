# libspeexdsp 1.2.1 — 适配笔记

> 档案创建时间: 2026-09-18
> 最后更新: 2026-09-18

## 一、基本信息
| 项目 | 值 |
|------|-----|
| 软件 | libspeexdsp（Xiph Speex DSP 处理库：重采样/AEC 降噪/AGC/Jitter buffer） |
| 版本 | 1.2.1 |
| 状态 | built |
| 构建系统 | autotools |
| 源码路径 | https://downloads.xiph.org/releases/speex/speexdsp-1.2.1.tar.gz |
| 依赖 | 无（零外部依赖叶子，FFT 内置 kiss_fft/smallft） |

## 二、包名说明（多包名并存先例）

本配方包名 **libspeexdsp**，与既有归档 `speexdsp/1.2.1` **不同包名、可并存**——同
`vorbis`/`libvorbis`、`ogg`/`libogg`、`opus`/`libopus` 先例。上游 pkg-config 名
`speexdsp`（lib/pkgconfig/speexdsp.pc），Debian 二进制包名 libspeexdsp1。
上游源码仓库 https://github.com/xiph/speexdsp（tag SpeexDSP-1.2.1，官方发布
tarball 出自 downloads.xiph.org）。

## 三、编译阶段（speexdsp/1.2.1 打法直接复用）

### Phase 2: 编译（autotools）
- [x] 三补丁干净适用（官方 tarball config.guess 为**新式** GUESS= 风格，
  `grep -c '^GUESS='` = 1；0001-config.h.in + 0003-config.guess + 0004-config.sub）
- [x] 打补丁后 `sh config.guess` → `aarch64-unknown-linux-ohos`；
  `sh config.sub aarch64-unknown-linux-ohos` 原样接受
- [x] configure mktemp E002 修复（配方 build() replace_in_file：
  `mktemp -d "./confXXXXXX"` → `${TMPDIR:-/tmp}/conan-cs-$$`）
- [x] make -j 全绿（libspeexdsp.a + 5 个示例/测试程序）
- [x] conan create + test_package 全绿（clang 直链 -lspeexdsp 重采样 API 真调用）

### Phase 3: 上游测试（上游测试铁律：本地执行+附证据）

**上游测试注册口径**：上游 autotools **无 TESTS 注册**（Makefile.am 无 TESTS 变量，
`make check` 无测试目标）；`libspeexdsp/Makefile.am` BUILD_EXAMPLES 块（configure
--disable-examples 可关，默认开）注册 **5 个 noinst_PROGRAMS 测试程序**——即上游
测试形态，N=5。

**本地实测（HarmonyOS PC aarch64 真机，2026-09-18）**：

| # | 测试程序 | 功能 | 执行方式 | 结果 |
|---|---------|------|---------|------|
| 1 | testdenoise | 预处理器降噪/AGC/去混响（stdin PCM 循环） | `./testdenoise < /dev/null` | PASS exit=0（空输入即退） |
| 2 | testecho | AEC/MDF 回声消除（mic/ref/out 三文件） | `./testecho ref.sw mic.sw out.sw`（本地生成 8kHz 正弦+延迟回声 PCM） | PASS exit=0，out.sw 产出 16128B 残差 |
| 3 | testjitter | Jitter buffer 自含断言（fill/frozen-sender resync） | `./testjitter` | PASS exit=0，输出 "Frozen sender: Jitter 0" |
| 4 | testresample | 重采样示例（stdin→stdout 多速率切换） | `cat ref.sw \| ./testresample > /dev/null` | PASS exit=0 |
| 5 | testresample2 | float 路径重采样（自含正弦有界循环 rate 1000→128000） | `./testresample2` | PASS exit=0，有界退出（约 7MB float 输出） |

### test_package（消费者视角）
- [x] test.c：speex_resampler_init→process_int→destroy 真调用 →
  PASS "speexdsp test: resampled 235 -> 256 samples OK"

## 四、关键发现

### 1. tarball 补丁后时间戳触发 automake 重生成规则（本地实测小坑）
官方 tarball 打补丁后 mtime 变新，`make` 判定 Makefile.in 过期触发 automake-1.16
重生成规则（本机无 automake → "automake-1.16: inaccessible or not found"）。
conan create 环境不受影响（conan 源码导出到全新目录 mtime 全新、build 在独立目录）；
本地源码树直接 make 时 `touch aclocal.m4 configure Makefile.in config.h.in` 即可。
这是 tarball+patch 流程的通用现象（非本库特有），不构成适配阻塞。

### 2. NEON 重采样路径（B 素材观察）
上游 configure 带 NEON 探测（configure.ac:78 AC_MSG_CHECKING(for NEON in
current arch/CFLAGS)——arm_neon.h 编译探测），aarch64 clang 下 has_neon=yes，
resample.c 内 `#ifdef USE_NEON` 走 resample_neon.h 内建函数路径。OHOS aarch64
clang 15 + arm_neon.h 直接可用，无需额外适配（1.2.1 时代 resample NEON 仅 ARMv7
汇编 + 少量 intrinsics，aarch64 无专属分支，自然走 C/通用路径+NEON 头守卫编译通过）。
浮点路径（FLOATING_POINT）经 config.h.in 补丁开启，testresample2 float 全链路验证 PASS。

## 五、最终状态
- **最终状态**: built（本地 conan create + test_package 全绿 + 上游 5 测试程序全 PASS）
- **结束时间**: 2026-09-18
