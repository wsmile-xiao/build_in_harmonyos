# libosmo-abis 2.0.0 适配笔记

## 编译环境
- 构建系统: autotools（osmocom 系标准）
- 编译日期: 2026-10-09
- 编译器: clang（/data/service/hnp/bin/clang）
- Profile: ohos-aarch64（os=OHOS os.version=6.0 arch=armv8）
- 状态: published（conan-verify G0–G3 全 PASS）

## 任务背景

- 上游 https://osmocom.org/projects/libosmo-abis tag 2.0.0
  （downloads.osmocom.org 官方发布包，sha256
  e4cd2682e0870f5475a81454bc8bf82a74603cad7f6565fc6755b3bfccd4a698）
- 两个库：
  - `libosmoabis`（libosmoabis.so.15）A-bis 接口抽象层：E1/T1 与 IP 承载
    （LAPD over TCP/UDP、IPA），子通道复用/解复用，DAHDI 驱动（本平台禁用）
  - `libosmotrau`（libosmotrau.so.11）TRAU 帧处理：RRA Prime 编解码 +
    RTP 帧转换（trau2rtp_*）
- 上游 configure.ac 真实依赖声明：
  ```
  PKG_CHECK_MODULES(LIBOSMOCORE,  libosmocore  >= 1.11.0)
  PKG_CHECK_MODULES(LIBOSMOVTY,   libosmovty   >= 1.11.0)
  PKG_CHECK_MODULES(LIBOSMOGSM,   libosmogsm   >= 1.11.0)
  PKG_CHECK_MODULES(LIBOSMOCODEC, libosmocodec >= 1.11.0)
  PKG_CHECK_MODULES(LIBOSMONETIF, libosmo-netif >= 1.6.0)
  ```
  后三者由 libosmocore 同一 conan 包的 LIB_COMPONENTS 提供。

## W0 依赖核验（R35：conan download -r=ohpcd --only-recipe）

| 依赖 | 版本 | 退出码 |
|---|---|---|
| libosmocore | 1.11.0 | 0（revision c3c915a2…） |
| libosmo-netif | 1.6.0 | 0（revision 2a6ff937…） |
| talloc（libosmocore 传递） | 2.4.4 | 0 |
| libmnl / libusb / pcsc-lite（libosmocore 传递，可选） | 1.0.5 / 1.0.27 / 2.4.0 | 0 |

## 构建步骤（本地实测命令链）

```bash
conan create archives/l/libosmo-abis/2.0.0 -r=ohpcd \
  -pr:h=ohos-aarch64 -pr:b=default
# 退出码 0；上游 make check 在 build() 内执行（见下）
```

configure 选项（由 conanfile generate() 注入）：
`--disable-ortp --disable-dahdi --enable-shared --disable-static`

## 适配要点（补丁集，5 个 portability 补丁）

| # | 补丁 | 内容 |
|---|------|------|
| 1 | 0001-config.guess.patch | 识别 HarmonyOS host triplet + 临时目录去掉 `umask 077`（HMDFS 不支持） |
| 2 | 0002-config.sub.patch | 接受 `*-linux-ohos` 目标三元组 |
| 3 | 0003-configure.patch | config.status 临时目录去掉 `umask 077` |
| 4 | 0004-include-mISDNif.h.patch | mISDNif.h 无条件用 libc sys 头，去掉内核 uapi `<linux/socket.h>` |
| 5 | 0005-tests-ipa_recv-ipa_recv_test.c.patch | musl `strerror(EIO)` 文案 "I/O error" 对齐 glibc 期望文件 |

**补丁 1–3** 与 libosmocore/1.11.0 同源问题（ohos 三元组 + HMDFS umask），
补丁文本按 libosmo-abis 2.0.0 自己的 configure/config.guess/config.sub
重新生成（libosmocore 的 0003 补丁尾部上下文不同，conan 严格 patch 引擎拒绝
跨包复用——首次 conan create 因此失败，重生成后通过）。

**补丁 4 根因**：`src/input/misdn.c` 无条件 `#include <mISDNif.h>`，
命中 tarball 自带的 `include/mISDNif.h`（-I$(top_srcdir)/include）；
该头 `#ifdef linux` 分支引入内核 uapi `<linux/socket.h>`，而 OHOS sysroot
的 linux/socket.h 重定义 `struct sockaddr_storage`，与 `<sys/socket.h>`
冲突（同 libosmocore 0007 系问题）。头内 `struct sockaddr_mISDN`
自包含，`sa_family_t`/`AF_*` 均由 libc sys 头提供，改为无条件 sys 头即可。
（mISDN 无 conan 包、OHOS sysroot 无内核 mISDN 头，本平台 mISDN 驱动
路径不可运行，但编译期可自包含通过。）

**补丁 5 根因**：musl `strerror(EIO)` 返回 "I/O error"（glibc 为
"Input/output error"），`tests/ipa_recv/ipa_recv_test.ok` 按 glibc 文案
→ 测试程序输出对齐 libc 实际文案（同 libosmocore 0023/0025 模式）。

**平台能力开关**（configure 参数，非补丁）：
- `--disable-ortp`：上游默认 ON（ENABLE_ORTP=yes），OHOS 惯例不引入
  ortp（glib/gstreamer 重链）；libosmotrau 的 osmo_ortp.c 随之不编译，
  rtp_test 按上游 AT_SKIP_IF 自然跳过
- `--disable-dahdi`：上游默认 ON 且探测 `dahdi/user.h` 失败直接
  AC_MSG_ERROR 硬失败；本平台无 DAHDI（e1_input.c 调用点已有
  HAVE_DAHDI_USER_H 守卫）
- e1d：上游默认 OFF，无需显式参数

**TLS**：与 libosmocore/1.11.0 同策略——`-fno-emulated-tls`（构建期 +
package_info 注入消费者 cflags），跨 DSO 统一 TLS 模型（osmo_ctx 等）。

## 上游测试（make check，build() 内实际执行）

测试入口：`tests/testsuite.at`（autoconf testsuite，11 用例；
--disable-ortp 时 rtp_test 被上游自身 AT_SKIP_IF 跳过）

结果（conan create 构建日志实测）：

| # | 用例 | 结果 |
|---|------|------|
| 1 | ipa_recv | ok |
| 2 | subchan_demux | ok |
| 3 | rtp_test | skipped（testsuite.at:28，--disable-ortp 按上游设计跳过） |
| 4 | raa_prime_encode | ok |
| 5 | raa_prime_decode | ok |
| 6 | trau_sync | ok |
| 7 | trau_pcu_ericsson | ok |
| 8 | trau2rtp_fr_std | ok |
| 9 | trau2rtp_fr_twts001 | ok |
| 10 | trau2rtp_efr_std | ok |
| 11 | trau2rtp_efr_twts001 | ok |

汇总：`10 tests were successful. 1 test was skipped.`（0 失败），
`make check` 退出码 0。

## 消费者测试（test_package）

test_abis.c（C，clang -std=gnu11 -fno-emulated-tls）真实调用公开 API：
- `subch_demux_init` / `subch_demux_in`：按上游 subchan_demux_test.c
  同款喂数口径（每字节 2 bit，前位在 LSB）喂入 trau_idle_frame() 编码
  位流，验证 sync 头（16×0 + 1×1）触发 resync 后完整 320-bit 帧经
  out_cb 交付
- `trau_idle_frame` / `decode_trau_frame` / `encode_trau_frame`：
  空闲帧位流 → 解码 → 重编码，验证位流逐位一致（round-trip 稳定）

运行输出：
```
ok: subch_demux delivered frame on channel 0 (320 bits)
ok: decode_trau_frame
ok: encode_trau_frame
ok: trau encode/decode round-trip stable
consumer test: PASS
```
退出码 0（本机 aarch64 实际运行，非 compile-only）。

## 验证结果

- conan create：退出码 0
  （libosmo-abis/2.0.0:6fcc7d72c9d106c54d9a0b232c6fd3b3ae6d6211）
- 打包产物：libosmoabis.so{,.15,.15.0.0}、libosmotrau.so{,.11,.11.0.0}、
  15 个头文件、libosmoabis.pc / libosmotrau.pc、COPYING
- conan-verify：G1 完整性 / G0 风险 / G2 干净构建 / G3 R26 隔离 全 PASS
- test_package：PASS（编译+链接+运行）

## 交付物

- archives/l/libosmo-abis/2.0.0/conanfile.py（组件：osmoabis/osmotrau，
  pkg_config 名 libosmoabis/libosmotrau，requires libosmocore 组件
  osmocore/osmogsm/osmovty[+osmocodec] 与 libosmo-netif）
- archives/l/libosmo-abis/2.0.0/conandata.yml（官方 URL + sha256，5 补丁）
- archives/l/libosmo-abis/2.0.0/patches/0001–0005
- archives/l/libosmo-abis/2.0.0/test_package/（conanfile.py/test_abis.c/MANIFEST.yml）
- 本 notes.md + reports/（conan-verify-report.md 由 conan-verify 生成）

## 已知限制

- mISDN 驱动（misdn.c）仅编译期自包含通过，OHOS 无内核 mISDN 支持，
  该驱动运行时不可用（上游同为 Linux 内核 mISDN 依赖）
- DAHDI / ortp / e1d 平台能力关闭（见"平台能力开关"）
- rtp_test 随 --disable-ortp 跳过（上游设计内）
---

**编译结束**: 2026-10-10 17:53
**最终状态**: published
