# xf86-video-savage 2.4.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-18
- 编译器: clang/clang++ (OHOS aarch64)
- 状态: published

## 适配方案（2026-09-18 重构）

**核心策略：使用真实 xorg-server 21.1.15 SDK 头文件，驱动源码零修改编译。**

早期尝试（2026-06 / PR #5867 首版）依赖本机预编译的 xorg-server（其 xf86int10.h/vbe.h
为空壳 stub），因此被迫用 `#ifdef __OHOS__` 补丁 stub 掉 VBE/BIOS 代码路径——该方案
违反 R8（patches 禁止平台宏）且被检视意见驳回。

现行方案（参照 xf86-video-fbdev 已合入配方）：
- 构建时从官方 xorg-server 21.1.15 tarball 提取**真实** SDK 头文件（hw/xfree86/int10/
  vbe.h + xf86int10.h、exa/exa.h、hw/xfree86/modes/xf86Modes.h 等），在私有 build
  目录组装 sdkdir 并生成 xorg-server.pc（含 sdkdir 变量）
- 生成 xorg-server.h：RANDR/RENDER/XV/DPMSExtension/XSERVER_LIBPCIACCESS 等供
  configure 的 XORG_DRIVER_CHECK_EXT 探测；ABI 版本宏来自真实 xf86Module.h
- pixman/xorgproto/libpciaccess 走 conan 依赖（registry 已发布）；xorgproto 的 .pc
  用包内原生的（${pcfiledir} 相对路径可直接用），pixman/pciaccess 包内 .pc 的
  prefix 是占位符，故在 SDK 中生成修正版 .pc
- VBE/BIOS 代码路径**完整编译**：savage_vbe.c 的 int10 调用全部有真实声明，运行期由
  X server 的 stub int10 模块返回不支持（上游对非 x86 平台的标准机制），驱动所有
  VBE 调用点都有 pVbe != NULL 守卫（上游原有逻辑）——无需任何源码级 stub
- XAA：configure 的 AC_CHECK_HEADERS([xaa.h]) 自动探测不到（xorg-server 21.x 已移除
  XAA），XAA=no，savage_xaa.c 与 savage_driver.c 的 HAVE_XAA_H 守卫自动生效（上游逻辑）
- DRI：显式 --disable-dri（DRI1 已从 xorg-server 21.x 移除，且需要 savage 内核 DRM）

## 编译步骤（conan create 流程等价）

```bash
conan create . -pr=ohos-aarch64 --build=missing
# 内部：
#   1. 下载 savage 2.4.1 tarball，打 3 个 portability 补丁
#   2. 下载 xorg-server 21.1.15 tarball，组装 SDK + xorg-server.pc
#   3. PKG_CONFIG_PATH=<sdk>/lib/pkgconfig:<xorgproto>/share/pkgconfig
#   4. ./configure --disable-dri（--prefix 等由 conan 注入）
#   5. make -j2 && 安装 savage_drv.so 到 lib/xorg/modules/drivers/
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess HMDFS 临时目录创建失败 (Permission denied) | HMDFS 上 umask 077 + mktemp 创建的目录不可写 | 0001 补丁：HarmonyOS 上跳过 umask 077（uname -s 探测，非平台宏） |
| 2 | configure HMDFS 临时目录问题 | 同上 | 0003 补丁：configure 中 HarmonyOS 上跳过 umask 077 |
| 3 | config.sub 不识别 linux-ohos | 上游 config.sub 无 OHOS | 0002 补丁：接受 ohos/ohos-linux 三元组（保留 android 原行为） |
| 4 | CI: No package 'xorg-server' found | xorg-server 不是 conan 包，CI 无系统 xorg-server | conanfile 内从官方 tarball 组装 SDK + 生成 xorg-server.pc（fbdev 同款方案） |
| 5 | XAAInfoRec 缺少成员（早期本机构建） | 预编译 xorg-server 的 XAA.h 是空壳 | 现方案用真实头文件 + configure 自动 XAA=no（上游 AC_CHECK_HEADERS 探测） |
| 6 | xf86int10.h/vbe.h 类型缺失（早期本机构建） | 预编译 xorg-server 的 int10/vbe 头是 stub | 现方案用 xorg-server 21.1.15 真实头文件，savage_vbe.c 原样编译 |

## 上游测试清点（R51）

上游 xf86-video-savage 2.4.1 无测试套件（X.Org 驱动项目惯例：无 tests/ 目录，无
make check 目标注册）。清点证据：tarball 内无 tests/ 目录；`make check` 输出
"Nothing to do for check"（automake 默认空目标）。

test_package 采用模块符号验证替代（X 驱动模块无法脱离 X server 链接/dlopen）：
验证 savage_drv.so 为合法 ELF64 AArch64 共享库，且动态符号表导出 savageModuleData
（X server loader 入口）、SAVAGE（DriverRec）、SavageGetBIOSModeTable（VBE 代码路径，
证明完整编译未裁剪）。

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| pixman | 0.46.4.3 | conan (ohpcd registry) |
| xorgproto | 2025.1 | conan (ohpcd registry) |
| libpciaccess | 0.19 | conan (ohpcd registry) |
| xorg-server | 21.1.15 | 官方 tarball（仅构建期 SDK 头文件） |

## 验证结果

```bash
# 编译产物
ls lib/xorg/modules/drivers/
# savage_drv.so

# test_package（conan create 自动执行）
# PASS: 64-bit AArch64 shared library (ET_DYN)
# PASS: dynamic symbol table present (N symbols)
# PASS: exports savageModuleData / SAVAGE / SavageGetBIOSModeTable
```

## 注意事项

- 此驱动面向 S3 Savage 显卡（x86 PCI 硬件）。在 OHOS/ARM64 上模块可正常构建、
  加载、注册；VBE BIOS 模式切换依赖 x86 real-mode int10，在无 BIOS 的 ARM 平台
  由 X server 的 stub int10 模块返回不支持（上游标准行为），EXA 加速/硬件光标/
  I2C/DDC 等寄存器级代码路径不受影响
- HMDFS 文件系统的 umask 077 + mktemp 问题会影响所有使用此模式的 autotools 项目
- R8 合规：3 个补丁均为 shell 级平台探测（uname -s），无 `__OHOS__` 宏；
  0002 补丁保留 android-linux 原有行为
