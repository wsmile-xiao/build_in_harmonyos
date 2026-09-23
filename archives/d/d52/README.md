# d52

**单片机代码反汇编器套件**（8052 / 8048-8041 / Z80-8080-8085，来自 jblang/d52）

D52 是一套命令行反汇编工具，用于把已编译的单片机固件还原成可读的汇编源码：

| 工具 | 目标 | 说明 |
|------|------|------|
| `d52` | 8052 / 8051 | 8052 反汇编器，支持代码分析（`-t`）与周期计数（`-z`） |
| `d48` | 8048 / 8041 | 8048 系列反汇编器 |
| `dz80` | Z80 / 8080 / 8085 | Z80 反汇编器，`-80`/`-85` 可切换 8080/8085 助记符 |

## 功能概述

- 读入 Intel HEX（`.hex`/`.ihx`）或纯二进制（`.bin`）固件，输出汇编源码与
  `.ctl` 控制文件；未指定类型时先找 `.hex` 再找 `.bin`。
- 控制文件（`.ctl`）可定义代码/数据区、符号、标签、位地址等，支持 `-t`
  追踪分析自动生成代码/数据划分。
- `z` 指令/`-z<file>` 可加载设备周期表（`cyclefiles/*.cyc`），在每条指令后
  输出指令周期数并按区间汇总，用于固件时序分析。
- 输出格式可切换：ASCII 宏（`-a`）、C 风格十六进制（`-n`）、点号伪指令（`-p`）、
  `defb/defw`（`-s`）、大写（`-u`）、Keil A51（`-k`）、地址偏移（`-x`）。

## 用法

```bash
d52 firmware.hex          # 生成 firmware.d52（同时读写 firmware.ctl）
d52 -t firmware.hex       # 先追踪分析代码/数据，生成控制文件后再反汇编
d52 -zADuC84x.cyc firmware   # 按 ADuC84x 周期表输出指令周期与区间汇总
d48 firmware.hex          # 生成 firmware.d48
dz80 -d firmware.bin      # Z80 反汇编，注释含地址与机器码
dz80 -80 firmware.bin     # 用 8080 助记符
```

输出文件写在工作目录，命名为 `<输入基名>.d52` / `.d48` / `.z80`。

## OHOS 适配

- 构建系统为上游单文件 `Makefile`（无 configure），`make CC=clang` 即可；
  上游默认 `CC=gcc`，OHOS 主机没有 `gcc`，配方从 Conan profile 的
  `tools.build:compiler_executables` 取编译器命令行传入。
- Makefile 把对象写进硬编码的 `./obj` 却没有创建目录的规则，配方在 make 前
  创建该目录（无补丁，与 Debian 打包的 `mkdir -p obj` 同型）。
- 上游 `install` 目标硬编码 `/usr/local/bin`，配方改为复制到包内 `bin/`。
- 无外部依赖（仅 libc），无平台相关系统调用，**零补丁**即可构建；
  产物为 aarch64 OHOS musl 动态可执行（PIE + BIND_NOW + RELRO + NX）。
- 三个工具都没有 `--version`/`--help` 长选项（`-h` 是"按 Intel HEX 读入"），
  自识别方式是直接运行并读版本横幅。
- 上游无测试套件；上游 `cyclefiles/` 自带基准输入与参考输出，本包的
  `test_package` 回放这些 golden 数据做逐字节回归（详见版本级 `notes.md`）。
- 上游最后一次提交为 2019-10-24，项目已停止维护（README 自述），本包照原样构建。

## 依赖关系

- 编译依赖：无（只用 libc）
- 运行依赖：无
- 仓库路径：`archives/d/d52/3.4.1-git20191024.ac20ebd/`

## 参考资料

- 源码仓库：https://github.com/jblang/d52
- 上游文档：源码包内 `d52manual.html`、`dz80-d48addendum.html`、
  `cyclefiles/cycle_counting.doc`
- 许可证：GPL-3.0-or-later
