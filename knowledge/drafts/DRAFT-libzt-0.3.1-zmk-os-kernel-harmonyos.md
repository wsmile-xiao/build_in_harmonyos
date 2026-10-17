# zmk（z.mk 定制 make 构建系统）OS.mk 不识别 HarmonyOS 内核

- **草稿 ID**: DRAFT-libzt-0.3.1-zmk-os-kernel-harmonyos
- **来源**: libzt 0.3.1 适配（`make configure` 报 `unsupported operating system kernel HarmonyOS`；zmk/OS.mk 加 HarmonyOS 后本地探索编译通过）
- **分类**: build / make / zmk / ohos / platform / toolchain
- **状态**: 本地草稿（路径 B 知识库扩展申请中）
- **严重级**: 2（make 加载期中止，报错点早于源码编译）

## 问题 / 错误签名

使用 zyga/zmk（z.mk）定制 make 构建系统的上游库，在 HarmonyOS 上执行
`make configure` 或 `make` 时，加载 zmk/OS.mk 即中止：

```
zmk/Toolchain.mk:96: *** unsupported operating system kernel HarmonyOS.  Stop.
```

（实际报错点：`zmk/OS.mk:43` 的
`OS.ImageFormat ?= $(error unsupported operating system kernel $(OS.Kernel))`）

## 根因

zmk 的 `zmk/OS.mk` 用 `OS.Kernel := $(shell uname -s)` 探测内核，仅把
`Linux FreeBSD NetBSD OpenBSD GNU GNU/kFreeBSD SunOS Haiku` 列入 ELF、
`Darwin`=Mach-O、`Windows_NT`=PE；HarmonyOS（`uname -s` 返回 HarmonyOS）
不在任何列表中，`OS.ImageFormat` 无法赋值 → make 立即报错。

libzt 0.3.1 的发布 tarball 本身不含 z.mk/zmk/（上游 CI 单独 checkout
zyga/zmk 后 `make install` 全局安装），首次适配需自行获取 zmk 快照，
本机 `uname -s`=HarmonyOS 因此直接触发该错误。

## 最小修复（本地探索构建验证）

```bash
# zmk/OS.mk 的 ELF 内核列表加入 HarmonyOS（与 Linux 同语义：OHOS 用户态
# 即 Linux ABI + musl，ELF 可执行）
sed -i 's/Linux FreeBSD NetBSD OpenBSD GNU GNU\/kFreeBSD SunOS Haiku))/Linux FreeBSD NetBSD OpenBSD GNU GNU\/kFreeBSD SunOS Haiku HarmonyOS))/' zmk/OS.mk
```

libzt 0.3.1 实测：修复后 `make configure` → `./configure` → `make -j2`
（libzt.a / libzt.so.1 / libzt-test 全出）→ `make check`（libzt-test 自测
通过，58 个测试函数）全通。

## 影响面与推广

- 识别：错误文本 `unsupported operating system kernel <X>` 出现在 make
  加载期、且上游用 z.mk（zmk）构建，基本即此条。
- 任何使用 zmk 构建系统的库在 HarmonyOS 上都会命中；修复为对构建系统
  打补丁或配方绕开（见下）。
- 配方案 fallback：完全绕开 zmk 直接编译，复刻上游目标（libzt 0.3.1
  先例：`libzt.a`=zt.c、`libzt.so.1`=zt.c+libzt.map、`libzt-test`=zt-test.c；
  注意 zt-test.c 内部 `#include "zt.c"`，只编译 zt-test.c 即可，勿重复
  编译 zt.c，否则 ld.lld duplicate symbol）——同时规避发布 tarball 缺
  z.mk 的构建依赖。
- 查重差异：E160 是 autotools config.guess 不识别 HarmonyOS（构建系统
  不同）；E532 / DRAFT-libxeddsa 是 CMake 平台分派（`if(UNIX)` 落空 /
  `CMAKE_SYSTEM_NAME=HarmonyOS`，构建系统不同）；本条是 make/z.mk 定制
  构建系统的内核探测缺口，扫描正式 E 条目与 drafts 均无等价命中。
- 机制口径：构建系统用 uname -s / 平台名分派时，HarmonyOS 用户态即
  Linux ABI + musl，应并入 Linux/ELF 语义；报错点越早（make 加载期）
  越要先查内核/平台探测代码，而非源码编译错误。

## 限制 / 反例

- 仅适用于 zmk（z.mk）系构建系统；autotools/CMake/meson 的 HarmonyOS
  平台缺口由 E160/E532/DRAFT-libxeddsa 分别覆盖，不重复。
- 对 zmk/OS.mk 的补丁属于构建系统级修改，不进入三方库配方 diff；
  配方案采用直接编译时该补丁完全不需要。
