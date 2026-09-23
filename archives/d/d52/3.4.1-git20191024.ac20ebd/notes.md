# d52 3.4.1-git20191024.ac20ebd 适配笔记

## 编译环境

- 构建系统: makefile（纯 make，无 configure 脚本）
- 编译日期: 2026-09-10
- 编译器: clang 15.0.4（OHOS aarch64，`/data/service/hnp/bin/clang`）
- Conan: 2.29.1，profile `ci/conan/profiles/ohos-aarch64`（os=OHOS 6.0 / armv8 / clang 15 / Release）
- 状态: built

## 编译步骤

1. `get()` 从 conandata.yml 的官方 GitHub 提交归档下载源码（提交
   `ac20ebd03fc2d102b46d6fa4166ebaa7552546dd`，2019-10-24，与任务卡版本
   `3.4.1-git20191024.ac20ebd` 对应；上游无 tag，`git ls-remote` 与 GitHub tags
   接口均为空，故按提交归档取源）。
2. `make -j1 CC=<profile 的 clang>`（R9 单线程；`CC` 由
   `tools.build:compiler_executables` 字典提供，不用 shell 变量）——顶层 Makefile
   依次编译 d52（`D52OBJS` = 7 个成员）、d48（`D48OBJS` = 4 个成员）、dz80（`DZ80OBJS` = 8 个成员）
   并链接三个可执行文件。采信轮日志中共 19 行 `clang -Wall` 调用：
   **16 行编译**（`clang -Wall -O2 -c <x>.c -o obj/<x>.o`）+ **3 行链接**
   （`clang -Wall -O2 ./obj/*.o -o d52|d48|dz80`）。注意 7+4+8=19 是三个 `*OBJS` 变量的
   成员数之和，而 `common.o` 被三者共用、`analyze.o` 被 d52 与 dz80 共用，去重后实际
   编译的目标文件为 16 个（与日志 16 行编译行一致）。
   （耗时不在本包证据口径内，见「验证结果」节。）
3. `package()` 把 `d52`、`d48`、`dz80` 复制到 `bin/`，`README`、
   `d52manual.html`、`dz80-d48addendum.html`、`COPYING` 复制到 `share/doc/d52/`。
4. 上游 Makefile 的 `install` 目标硬编码 `cp -f <bin> /usr/local/bin`，不使用。

实跑命令的唯一权威副本在 `manifest.yaml` 的 `validation.*.command`（本节不复制命令）。

## 测试情况

### 上游测试：0 用例

本版本上游没有测试套件（不是跳过，也不是部分执行）：Makefile 的显式 target 共 14 条
（all/install/d52/d48/dz80/clean/win/wind52/wind48/windz80/winclean 与
d52.exe/d48.exe/dz80.exe），没有 check/test，且 `test|check` 字样在 Makefile 中整体不出现；
源码树没有 tests/ 目录或测试脚本；Debian 对同一版本的打包也没有 Testsuit（无 autopkgtest）。
完整清单与证据命令见 `manifest.yaml` 的 `test_results.upstream.evidence`。

### 适配侧测试：15 项断言全部通过（含 8 项上游 golden 回放）

上游在 `cyclefiles/` 里自带基准程序与参考输出（BENCH0.HEX 加每个 MCU 派生型号的
cycle 文件对应的期望反汇编 `bench0.<derivative>.d52`，以及 Z80 例子 z.bin/z.ctl/z.z80，
见上游 cyclefiles/cycle_counting.doc）。`test_package/test.sh` 把这些参考数据复制到
测试工作目录，用安装后的 `bin/d52`、`bin/dz80` 回放，并与上游期望输出逐字节比对；
唯一允许的差异是开头 4 行版本/日期头（3.4.1 把日期格式改成了 y/m/d，期望文件由
3.4.0 生成，内容从第 5 行起完全一致）。

两处**不改变工具所读字节**的存放适配（详见 `test_package/data/PROVENANCE.md`）：

1. 两个文件名按工具实际 `fopen()` 的名字小写化（`BENCH0.HEX`→`bench0.hex`、
   `Bench0.ctl`→`bench0.ctl`）。设备 HMDFS 大小写不敏感，大小写不一致在设备上也能跑通，
   但 CI worker 是大小写敏感文件系统，必须与工具打开的名字完全一致。
2. Z80 二进制输入以可打印文本存放（`cyclefiles/z.bin` → `z.bin.esc`，39 字节写作
   一行 POSIX 八进制转义），由测试用 shell 内建 `printf '%b' "$(cat z.bin.esc)"` 还原
   （用 `%b` 而不是把文件内容当格式串，避免内容被解释成 printf 转换说明符）。
   原因：PR 新增的裸二进制文件无法被 CI 检出步骤应用——平台生成的 `pr.diff` 不含
   binary patch 数据（首轮 CI 构建 44060 实测
   `error: missing binary patch data ... patch does not apply`），会在构建开始前就失败。
   还原出的字节正确性由 golden 回放本身证明（任何一个字节不同都会改变反汇编结果，
   从而在逐字节比对中失败），还原后另断言文件为 39 字节。

| 断言组 | 数量 | 结果 |
|--------|------|------|
| 三工具自识别（d52/d48/dz80 版本横幅） | 3 | 3/3 |
| d52 golden 回放（7 个 cycle 文件，每个 42 行输出逐字节一致） | 7 | 7/7 |
| dz80 golden 回放（`-d`，58 行输出逐字节一致） | 1 | 1/1 |
| 行为断言（缺失输入报错 / d48 反汇编 / `-u` 大写 / `-t` 分析模式） | 4 | 4/4 |
| 合计 | 15 | 15/15 |

参考数据来源与每个 fixture 的 sha256 记录在 `test_package/data/PROVENANCE.md`，
存放形态的两处适配（文件名小写化、Z80 二进制输入改为转义文本）见本节上方说明，
工具实际读到的字节与上游一致。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `make CC=clang -j1` 首编即失败：`error: unable to open output file 'obj/d52.o': 'No such file or directory'` | Makefile 把对象写进 `OBJDIR = ./obj`，但没有创建该目录的规则（上游只保证 `make` 在已有 obj/ 的树里可用） | 配方 `build()` 里 `os.makedirs(source_folder/obj)` 后再 make；不需要补丁（Debian 打包同样用 `override_dh_auto_build: mkdir -p obj` 处理） |
| 2 | 设备 `make` 默认 `CC=gcc`，OHOS 主机没有 `gcc` | Makefile 硬编码 `CC = gcc`，且裸 shell 无 `CC` 变量 | 从 `tools.build:compiler_executables`（字典，`check_type=dict`）取 `c` 并命令行传入 `CC=`；未改动 Makefile |
| 3 | `d52 --version` / `--help` 返回非 0（CI L2 冒烟探测的非阻塞告警） | 上游只支持自由格式的短选项（`-h` 是"按 Intel HEX 读入"，不是 help），没有 `--version/--help` 长选项 | 不改上游行为；改用"无参数运行打印版本横幅并按 rc=0 退出"作为自识别断言（见 test_package） |
| 4 | golden 回放若缺 `bench0.ctl` 则输出与期望不同 | 期望输出是在 `Bench0.ctl`（`Z 0-ffff^`，强制取高 cycle 值）参与下生成的 | fixture 中一并提供 `bench0.ctl`；比对前断言生成文件非空且行数一致，避免空输入假绿 |

## 源码修改

无补丁（`patches: {}`，`patches_applied: []`）。上游 Makefile 与全部源码原样使用，
仅在配方侧创建 `obj/` 目录并显式传入编译器。

## 依赖版本

无外部依赖：源码只 include `<ctype.h>` `<stdio.h>` `<stdlib.h>` `<string.h>` `<time.h>`
（libc）。`requirements()` 为空，W0 无需制品仓依赖验证；Conan 侧也不产生 library
产物，只有 `bin/` 三个可执行文件与 `share/doc/d52/` 文档。

## 验证结果

- 原生构建：设备 `mkdir -p obj && make CC=clang -j1` 通过，产出 d52/d48/dz80
  （clang 15.0.4，仅上游代码自带告警）。本包不申报 `make` 耗时：设备是共享负载环境，
  同一命令的实测耗时在不同会话间可相差数倍，任何单次数值都不具可复现性，故不作为证据；
  构建过程的证据以采信轮 `conan create` 日志为准
  （`RUN: make -j1 CC=…` 加 16 行编译 + 3 行链接）。
- 上游测试：无（0 用例，证据见上）。
- 适配侧测试（`test_package`）：15/15 通过，含 8 项上游 golden 回放逐字节比对。
- `conan create`（clean 轮）与 `conan-verify` 的结论与日志路径见 `manifest.yaml`
  的 `validation.conan_create` / `validation.conan_verify` 及本包 `reports/`。
- 交互命令（设备实测）：

```bash
$ d52            # rc=0，打印 “D52 8052 Disassembler V3.4.1”
$ cd cyclefiles && d52 -zADuC84x.cyc bench0   # 生成 bench0.d52，与上游 bench0.aduc84x.d52 第 5 行起逐字节一致
$ dz80 -d z      # 生成 z.z80，与上游 z.z80 第 5 行起逐字节一致
$ d52 no-such-input ; echo $?   # rc=2，打印 “* Can't open either 'no-such-input.hex' nor 'no-such-input.bin' *”
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/d52 | 92608 B | 8052 反汇编器（PIE，BIND_NOW，GNU_RELRO，GNU_STACK RW） |
| bin/d48 | 63936 B | 8048/8041 反汇编器 |
| bin/dz80 | 92608 B | Z80/8080/8085 反汇编器 |
| share/doc/d52/{README,d52manual.html,dz80-d48addendum.html,COPYING} | 113451 B（111 KB） | 上游文档与 GPL-3.0 许可证原文（7190 + 65826 + 5367 + 35068 B） |

三个可执行文件均为 aarch64 OHOS musl 动态可执行（`/lib/ld-musl-aarch64.so.1`），
类型 DYN（PIE）、`FLAGS: BIND_NOW`、`FLAGS_1: NOW PIE`、`GNU_RELRO` 存在、
`GNU_STACK RW`（NX）。

## 注意事项

- 三个可执行文件的输出文件写在**当前工作目录**（`<basename>.d52` / `.d48` / `.z80`），
  输入按 `<basename>.hex`（Intel HEX）或 `<basename>.bin` 查找；上游 `-h/-b/-c` 选项
  强制输入类型。test_package 因此把所有运行都放在工作目录内，不污染包目录。
- `-t`（trace/analyze）会**覆盖**同名 `.ctl` 文件，属上游文档声明的行为，测试放在
  独立子目录执行。
- 上游最后一次提交为 2019-10-24（README 声明项目已停止维护），源码为 2007 年风格的
  C；本次适配未修改任何源码。
