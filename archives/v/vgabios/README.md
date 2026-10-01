# vgabios (LGPL'd VGABIOS)

Bochs / QEMU / plex86 使用的 LGPL **显卡固件**（VGA / PCI Option ROM）：一份用
C + 8086 汇编写成的实模式视频 BIOS，实现 INT 10h VGA 服务、Bochs VBE (DISPI)
扩展、Cirrus SVGA 扩展与 3dfx Voodoo Banshee PCI 扩展。

本包交付的是**与宿主架构无关的 8086 Option ROM 镜像**，以及随构建产出的
`biossums` 镜像校验和工具。

## 产物

| 路径 | 内容 |
|------|------|
| `share/vgabios/VGABIOS-lgpl-latest.bin` | 标准 VGA + Bochs VBE ROM（38400 B，PCI） |
| `share/vgabios/VGABIOS-lgpl-latest.debug.bin` | 同上 + DEBUG 编译（39424 B） |
| `share/vgabios/VGABIOS-lgpl-latest.cirrus.bin` | Cirrus SVGA 扩展 ROM（33280 B） |
| `share/vgabios/VGABIOS-lgpl-latest.cirrus.debug.bin` | Cirrus + DEBUG（33280 B） |
| `share/vgabios/VGABIOS-lgpl-latest.banshee.bin` | Voodoo Banshee PCI 扩展 ROM（32768 B） |
| `bin/biossums` | VGA BIOS 镜像校验和工具（OHOS aarch64 原生） |

## 安装

```bash
conan install --requires=vgabios/0.8a -r=ohpcd
# ROM 镜像：<package>/share/vgabios/VGABIOS-lgpl-latest*.bin
# 工具：    <package>/bin/biossums
```

Bochs 配置中把 `vgaromimage` 指向所需的 ROM 镜像即可：

```
vgaromimage: file=<package>/share/vgabios/VGABIOS-lgpl-latest.bin
```

## 构建方式

上游 Makefile 用**两套工具链**：

1. 宿主 C 编译器（clang）——编译 `biossums` / `vbetables-gen`，并对 `vgabios.c`
   做 `-E -P` 预处理；
2. dev86 的 **8086 工具链**——`bcc`（C→8086 汇编）与 `as86`（汇编→二进制），
   把预处理后的 C 翻译成实模式机器码。

```
clang -E -P vgabios.c -DVBE -DPCIBIOS … > _vgabios_.c
bcc   -o vgabios.s -C-c -D__i86__ -S -0 _vgabios_.c
as86  _vgabios_.s -b vgabios.bin -u -w- -g -0 -j -O -l vgabios.txt
biossums VGABIOS-lgpl-latest.bin        # 追加校验页并写 ROM 校验和
```

## 依赖关系

| 类型 | 依赖 |
|------|------|
| 工具依赖（tool_requires） | `dev86/0.16.21`（OHOS aarch64 原生的 bcc/as86 及 `lib/bcc` 组件） |
| 运行依赖 | 无（产物是与宿主无关的 8086 ROM 镜像） |

## OHOS 适配要点

- **无源码补丁**：上游 Makefile 以 `CC/GCC/BCC/AS86` 变量驱动且为简单赋值，
  命令行覆盖即可接入 Conan 工具链（R1：参数最少化）。
- `tool_requires("dev86/0.16.21")`：把 OHOS aarch64 原生的 8086 工具链接入构建环境；
  `bcc` 经 `BCC_PREFIX` 定位包内 `lib/bcc/` 的 `bcc-cpp`/`bcc-cc1`/`include`。
- **HMDFS /tmp 只读**：`bcc` 会在临时目录落中间文件，配方把 `TMPDIR` 指向构建目录
  （dev86 已打补丁令 `bcc` 遵循 `TMPDIR`，见 `archives/d/dev86/0.16.21`）。
- **预编译产物防护**：上游归档内含发布时预编译的 ROM，构建前先移除，确保最终打包
  的一定是本次真构建产物；构建若产出不全则打包阶段显式报错。
- 产物是 8086 实模式固件，**不含任何平台分支**；`bin/biossums` 为 OHOS 原生可执行文件。

## 测试

- **上游 0.8a 无自动化测试**：顶层 Makefile 无任何 `check`/`test`/`ctest` 目标；
  `tests/` 下只有两个 DOS 时代交互式程序（`testbios.c` = Turbo C 2.0、
  `lfbprof` = Watcom C++ + DOS4GW），无法在 OHOS 上运行（用 8086 工具链编译
  `tests/testbios.c` 在 `#include <dos.h>` 处即失败）。详见 `0.8a/reports/test-report.md`。
- **消费者侧测试**：`0.8a/test_package/test_vgabios.sh`，9 项用例，其中 1 项为
  鸿蒙平台专有（`TC-09-ohos-host-abi`：`bin/biossums` 为 OHOS 目标 AArch64 ELF
  且可在本机执行）。逐字节校验 5 个 ROM 的签名/校验和/长度字段/PCIR 结构/变体标记，
  并实际运行 `biossums` 修复被破坏的 ROM。

## 参考资料

- 上游源码：https://github.com/bochs-emu/VGABIOS （tag `v0_8a`，2021-06-03）
- 项目主页：https://www.nongnu.org/vgabios/
- PCI Firmware Specification（PCIR 结构）：https://pcisig.com/specifications
- 许可证：LGPL-2.0-or-later
