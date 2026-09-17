# libmodplug 0.8.9.0 适配笔记

## 编译环境
- 构建系统: autotools (upstream `configure` + libtool, autoconf 2.69)
- 编译日期: 2026-09-11
- 编译器: OHOS clang 15.0.4 (target aarch64-linux-ohos), OpenHarmony PC (HarmonyOS aarch64)
- 分支: feat/libmodplug-0.8.9.0
- 状态: built（门禁全绿，详见"最终状态"）

## 上游核实（0.8.9.0, SourceForge 官方 tarball）

### 源码与许可
- 官方主页: https://modplug-xmms.sourceforge.net/ （SourceForge 项目
  https://sourceforge.net/projects/modplug-xmms/ — libmodplug 从
  modplug-xmms 项目发布，canonical 下载路径在 modplug-xmms 下；
  `downloads.sourceforge.net/project/libmodplug/...` 返回 404）
- 官方 tarball:
  https://downloads.sourceforge.net/project/modplug-xmms/libmodplug/0.8.9.0/libmodplug-0.8.9.0.tar.gz
- SHA256: `457ca5a6c179656d66c01505c0d95fafaead4329b9dbaa0f997d00a3508ad9de`
  （本地 `sha256sum` 复核一致；解包后顶层目录 `libmodplug-0.8.9.0/`）
- License: public domain — tarball 顶层 `COPYING`（57 字节）明文
  "ModPlug-XMMS and libmodplug are now in the public domain."；
  src/modplug.h 头部与 README 亦声明公有领域（conanfile package()
  复制 COPYING 到 licenses/）
- C++ 实现 + C 公共 API（src/modplug.h 纯 C 接口，`extern "C"`）

### 构建与接口
- Autotools: `configure` (autoconf 2.69) + `Makefile.am` + libtool
- `src/Makefile.am` L46-49: `libmodplugincludedir = $(includedir)/libmodplug`
  安装 modplug.h + stdafx.h/sndfile.h/it_defs.h 到 `include/libmodplug/`
  （消费者 include 写法 `#include <libmodplug/modplug.h>`）
- 库名: `libmodplug.so`；`MODPLUG_LIBRARY_VERSION=1:0:0` →
  SONAME `libmodplug.so.1`、real name `libmodplug.so.1.0.0`
- 依赖: 无第三方库依赖（自包含混音引擎）；C++ 运行库
  `libc++_shared.so` + musl `libc.so`
- 交付选项: `--enable-shared --disable-static`

## 上游测试：0 项（三重证据）
1. **目录**: tarball 内无 `tests/`、`test/` 目录；`tar tzf` 全量 72 个条目核实
2. **构建目标**: 根 Makefile.am 与 src/Makefile.am 无 `check`/`TESTS` 目标
   （`grep -E 'check|TESTS'` 仅 dist_doc_DATA 文档行命中）
3. **测试框架**: configure (autoconf 2.69) 无 check 目标生成
   （`grep -cE '^check|^TESTS' configure` = 0）；无 CTest/GTest/Check
   等任何测试框架引用；README 无测试章节

按 TEST_QUALITY_SPEC 无上游测试规范处理：以 test_package 消费者测试
（18 断言）与 test_ohos 鸿蒙专项测试（7 机检 + 18 消费者断言）替代，
全部从最终 Conan 包构建/运行。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 阶段 OHOS 元组探测失败 rc=1 | config.guess 2015 版无 HarmonyOS 分支，`uname -s` = "HarmonyOS" | 0001 补丁主 case 加 `*:HarmonyOS:*:*` + `__OHOS__` → LIBC=ohos |
| 2 | config.sub 拒绝 linux-ohos | maybe_os 列表无 linux-ohos | 0002 补丁 maybe_os 加 `linux-ohos*`（保留 `os=-$maybe_os`，勿硬编码） |
| 3 | make 阶段 HMDFS 权限错误 | 源码树 umask 077，configure 产物组不可读 | conanfile `build()` 前 sed 修复（lame 先例） |
| 4 | C++ 编译 exceptions 警告/膨胀 | 上游代码不使用异常但未显式关闭 | CXXFLAGS 加 `-fno-exceptions` |
| 5 | fixture 全静音 + GetLength=0 | MODMAGIC 布局（见下） | 按 libmodplug 实际解析布局重造 fixture |

## MODMAGIC 布局怪癖（fixture 构造关键知识）
libmodplug 0.8.9.0 `src/load_mod.cpp`（L149 `#pragma pack(1)`）定义：
```c
typedef struct {
    BYTE nOrders;      // offset 0   (in struct)
    BYTE nRestartPos;  // offset 1
    BYTE Orders[128];  // offset 2
    CHAR Magic[4];     // offset 130  ← 在 orders 之后！
} MODMAGIC;
```
探测代码在 `lpStream + 20 + 30*31`（=950）处读 `pMagic->Magic`，
即文件偏移 950+130 = **1080**。因此 libmodplug 0.8.9.0 期望的 31-sample
MOD 文件布局是：
```
title(20) | 31*samplehdr(30) | nOrders(1) | nRestart(1) | orders(128) | "M.K."(4) | patterns | sample data
```
即 **"M.K." magic 位于 order 列表之后**（Ultimate SoundTracker/
NoiseTracker 时代布局，与 ProTracker 惯例相反——PT 是 magic 紧跟
31 个采样头之后、orders 之前）。常见文档描述的布局会被 1080 处的
零填充击败 → 探测失败 → 15-sample 分支 → `m_nSamples=15`、
`Order[]` 错位（Order[0]=32）、`GetLength` 返回 0、解码全静音。
本仓库 fixture `ohpc_test.mod`（2620 字节）即按此布局手工构造：
- title "OHPCTEST"（null 填充）
- sample 1: "OHPC-SMP1", 256 words, volume 64, no loop
- 1 个 order（pattern 0），64 行 × 4 通道，row 0 ch0 note period 428
  （C-3, note 61）instr 1
- sample data: 8 周期方波（0x40/0xC0 交替）
- 预期: name="OHPCTEST"、GetLength=8000 ms、44100 Hz/16bit/stereo
  下 0.5 s 缓冲解码含 5544 个非零样本

## 语义核实（实测，OpenHarmony PC / clang-15 / libc++）
- `ModPlug_GetSettings` 默认: mChannels=2, mBits=16, mFrequency=44100,
  mResamplingMode=MODPLUG_RESAMPLE_LINEAR(1), mLoopCount=0
- `ModPlug_SetSettings` 在 `ModPlug_Load` **之前**调用才对解码生效
  （载入后修改需重新 Load）；GetSettings 回读值即时反映
- `ModPlug_GetLength` 单位毫秒；对上述 fixture 恒为 8000（1 pattern
  64 行 × speed 6 tick × tempo 125 下 tick 累计向上取整）
- `ModPlug_Read` 是流式 API：连续调用推进播放位置，缓冲满即返回
  请求长度（88200 B = 0.5 s stereo 16-bit）
- 损坏输入: 截断头（100 B）、随机垃圾（3000 B）、空缓冲全部返回
  NULL 且不崩溃（ReadMod 的 dwErrCheck/dwWowTest 防御）

## 查重与已知风险（不建草稿，证据不成立）
- 有符号 char 差异: MOD 采样默认按 RS_PCM8S（signed 8-bit）解码，
  本机 aarch64 char 无符号但代码显式 `signed char`/`LPCSTR` 处理，
  load_mod.cpp 读 sample 头用 `bswapBE16`+BYTE，无隐式 char 符号扩展
  依赖 → 无真实缺口
- 未对齐读取: 结构体 `#pragma pack(1)` + LPCBYTE 流式访问，
  aarch64 未对齐访问在 OHOS clang 默认允许（非 arm32），且实测
  解码正常 → 无缺口
- 字节序: 上游已全大端字节交换（bswapBE16/32），aarch64 LE 正常
- 音频定点/浮点: 0.8.9.0 混音引擎纯定点整数（无浮点路径），
  跨配置（-O2/-O3）输出逐位一致（同机构建对比），无浮点分歧证据
  → 按规则不创建知识草稿

## 交付物
- lib/libmodplug.so.1(.0.0)（版本化 SONAME libmodplug.so.1, OHOS 签名
  [.codesign 段], ELF64 AArch64, NEEDED=[libc++_shared.so, libc.so],
  无 RPATH/RUNPATH, 无宿主绝对路径泄漏）
- include/libmodplug/{modplug.h, stdafx.h, sndfile.h, it_defs.h}
  （C 公共 API，libmodplugincludedir = $(includedir)/libmodplug）
- lib/pkgconfig/libmodplug.pc（configure 生成，随 make install 安装
  ——首次 DESTDIR 冒烟看漏是因为查错了 stage 目录，conan 包实测含
  lib/pkgconfig/libmodplug.pc）
- CMakeDeps 消费: find_package(libmodplug) + libmodplug::libmodplug

## 门禁与本地环境差异记录（2026-09-11）
- scoped CI `CI_PACKAGES=archives/l/libmodplug/0.8.9.0
  ci/conan/build_and_test.sh`: L0/L1/L1e/L5 PASS、L2 skip（库无
  bin/）、L4 warn（config.guess 补丁含 `echo|sed` 触发危险函数
  误报——该行是上游 config.guess 自身固有写法）
- L1c 判定说明: CI 日志中 "make check" 痕迹来自 conanfile build()
  内对 `$(MAKE) -C src` 的调用 grep 命中，**上游本身无测试**
  （三重证据见"上游测试"节），L1 的实质通过依据是 test_package
  18 断言真实执行（L1a/L1b）
- 本地 pre-commit hook（ci/conan/hooks/pre-commit）L0c 对
  `test_ohos/` 报 "test_package/ 目录缺失"：hook second-loop 未
  跳过 test_ohos 目录的固有缺陷。已入库先例 msdfgen/1.13（同款
  test_ohos/conanfile.py + test_ohos.sh 结构）今天以相同文件集
  提交同样被拦（实测复现）；正式 CI 门禁不经过该路径
- 本机跑 conan/CI 需用本地工具链 profile（ohos-aarch64-localfix:
  CONFIG_SHELL/bash/clang 指向本机路径）——仓库 ci/conan/profiles/
  ohos-aarch64 的 /data/service/hnp/bin/ 前缀仅存在于 CI 执行机

## 0001/0002 补丁可应用性复核（2026-09-15，官方干净 tarball）
- 官方 tarball sha256 `457ca5a6...ad9de` 与 conandata.yml 一致；
  其 config.guess 与 config.sub 的 `timestamp='2015-01-01'`
  （Copyright 1992-2015）——"2015-era" 描述属实
- `git apply --check`、`patch --dry-run -p1`、`patch_ng.apply()`
  三种方式对干净源码均应用成功（0001 + 0002）
- 应用后功能验证：`sh config.guess` → `aarch64-unknown-linux-ohos`，
  `sh config.sub aarch64-unknown-linux-ohos` 原样通过
- 结论：补丁本身正确，无需重新生成；conandata.yml/manifest.yaml/
  notes.md 中 "2015-era/2015 版" 描述与官方 tarball 事实一致，保留

## 最终状态
- **最终状态**: 成功（built）
- **产物**: lib/libmodplug.so.1.0.0 + SONAME 链 libmodplug.so(.1)，
  include/libmodplug/*.h，lib/pkgconfig/libmodplug.pc
- **验证**: conan-verify G0-G5 + L2/L4/L5 全 PASS（本机
  ohos-aarch64-localfix profile）；test_package 18/18；
  test_ohos 7/7（AArch64/musl/SONAME/NEEDED/.codesign/无宿主路径/真实解码）
- **质量门禁**: 全部通过；详见 reports/test-report.md
- COMPLETED
