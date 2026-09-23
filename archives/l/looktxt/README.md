# looktxt

`looktxt` 是一个把**任意自由格式文本中的数值区域**批量导出为科研数据格式的命令行工具：它扫描文本、识别其中的数字字段，按内容给每个数据集（标量/向量/矩阵）自动命名，然后生成 Matlab、IDL、Scilab、Octave、XML、YAML、HTML、Raw 共 8 种格式（`--help` 实测宣传同一清单；MATfile/MEX/NeXus 后端在本构建中为空占位，可选 NeXus/HDF5 不可用）输出。它的价值在于让研究者不必为每台仪器、每种日志格式手写一个 load routine。

上游 [gitlab.com/soleil-data-treatment/soleil-software-projects/looktxt](https://gitlab.com/soleil-data-treatment/soleil-software-projects/looktxt)（作者 Emmanuel Farhi（SOLEIL / ILL），GPL-2.0-or-later；Debian 亦以 `looktxt (1.4.1-3)` 打包同一份源码）。

## 功能概述

- 数值域自动发现：无需固定列位置，按分隔符集合从任意文本中抽取数字，支持注释/多行/混排文本
- 数据集命名与分段：按文件内容命名（可用 `-s` 指定 section 名、`--names_length` 控长），标量/向量/矩阵统一处理
- 输出格式：Matlab（默认）、IDL、Scilab、Octave、XML、YAML、HTML、Raw 共 8 种（`--help` 实测宣传清单）；`-o` 指定输出名，未指定时由输入文件名点号转下划线得到（`t1.txt` → `t1_txt.m`）
- 二进制数据块：`-b -f Matlab` 额外产出 `.bin`（double 序列）并在 `.m` 中内嵌 `bin_ref` 读取函数
- 干跑模式：`--test` 只做扫描与分类并打印 VERBOSE 结果，不写任何文件（上游回归即用它）
- 可选 NeXus/HDF5 后端：需要 libNeXus（本包未启用，见下）

## 依赖关系

- 编译依赖：无（上游自述 "pure C code, with no dependency"，单翻译单元 `looktxt.c`，纯 POSIX Makefile）
- 运行依赖：无（仅链接系统 libc）
- Conan 依赖：无（配方未声明 `requirements()`，W0 检查通过）
- 可选依赖：libNeXus（NeXus/HDF5 导出）。`nexus` 未发布到 ohpcd 制品仓，且上游 Makefile 会探测宿主 `/usr/include/napi.h`，配方因此以 `NEXUS_NAPI=` 显式关闭该后端以保证可复现

## OHOS 适配要点

- **1 个源码补丁（可移植性）**：`file_scan()`（looktxt.c L2336–L2700）在 L2382 用 `char c` 承接 L2419 的 `lk_tolower(getc(...))`，并在 L2422/L2692 与 `EOF` 比较。OHOS 目标（`aarch64-unknown-linux-ohos`）的 plain char 默认无符号（实测 `CHAR_MIN=0`），EOF(-1) 变成 255 后永不等于 -1，扫描主循环在文件结尾失去出口——未打补丁的二进制在上游自带的 `examples/Al.lau` 上无限挂起（`timeout 25` → rc=124，100% CPU）。补丁把接收变量改为 `int`（与 Debian 源码包 `fix_infinite_loop.patch` 语义等价：同一处 `char c` → `int c`；未取该补丁原文，不作逐字断言），**单行、无平台宏**（R8/PF5 合规）；同机的 `-fsigned-char` 对照组同样能跑完，但那是全局语义开关、只掩盖症状，故采用根因级修正。补丁后上游 `make test` 6/6 输出 `Test OK`
- **构建可复现**：以 `NEXUS_NAPI=` 屏蔽 Makefile 对宿主 `napi.h` 的 `$(shell)` 探测（make 命令行变量优先于 `ifeq` 内的赋值），产物只依赖 libc；编译器取自 Conan conf（R33），`-j1`（单翻译单元工程，且让上游测试日志可复现），上游 `make test` 缺失 `Test OK` 即中止构建（R9：不跳过、不伪造通过）
- 上游 `make install` 依赖 `install(1)`（OHOS/toybox 无），`package()` 改为直接 copy `bin/looktxt` + `licenses/LICENSE` + `share/doc/looktxt/README.md`
- 上游 `make test`（1 次 `--version` + 5 个 examples 文件的 `--test` 干跑）完整保留并在 `build()` 中强校验 `Test OK` 标记，未修改任何用例；**6/6 通过**。逐条结果见 [1.4.1/notes.md](1.4.1/notes.md)（`reports/test-report.md` 属本地质量报告，按 PR 禁止文件清单不随 PR 分发）
- 注意 looktxt 的**退出码 = 已处理文件数**（无输入/不可读输入 → 0，两个输入 → 2），脚本化调用应校验产物而非退出码；消费者测试的 15 条断言均按实测语义编写

## 参考资料

- 上游项目与 tag 归档：<https://gitlab.com/soleil-data-treatment/soleil-software-projects/looktxt>
- Debian 亦以 `looktxt (1.4.1-3)` 打包同一份 1.4.1 源码：其源码包描述文件 https://deb.debian.org/debian/pool/main/l/looktxt/looktxt_1.4.1-3.dsc 的 Checksums-Sha256 段记录 `looktxt_1.4.1.orig.tar.gz` = `a586e12a8706cd3e49e8ce836593720f3824e84cb8fd8d3f22f40987b778aac8`（344832 字节），与本包 `sources.sha256` 同一 ⇒ 两条独立来源指向同一份字节内容；Debian 侧还带一个语义等价的 `fix_infinite_loop.patch`（本包采用上游级单行类型修正，等价）
- 上游 README：用法、推荐参数（`--fast --headers --fortran`）与 NeXus 编译说明
- iFit 项目（本工具的原始使用背景）：<https://ifit.mccode.org>

## 版本

- `1.4.1` — 适配 HarmonyOS PC（aarch64-unknown-linux-ohos / armv8）；1 个 EOF 死循环补丁，上游 6/6 通过、test_package 15/15 通过；见 [1.4.1/notes.md](1.4.1/notes.md)

## 产物

| 路径 | 说明 |
|------|------|
| `bin/looktxt` | 文本数值域 → 科研数据格式转换器（arm64 ELF） |
| `licenses/LICENSE` | GPL-2.0 全文 |
| `share/doc/looktxt/README.md` | 上游使用说明原件 |

## 已知限制

- NeXus/HDF5 导出不可用（依赖未发布，构建期已关闭该后端）；其余 8 种格式（Matlab/Scilab/IDL/XML/YAML/HTML/Octave/Raw）实测均可用（逐格式跑过，见 1.4.1/notes.md 的『格式矩阵实测』）
- 上游不加 `--fast` 的慢路径存在既有数值缺陷（`1.0 2.0 3.0` 矩阵首行被写成 `1 1 2`），该缺陷在未打补丁的源码上同样复现，属上游算法既有问题，本次适配未越界修改；建议使用 `--fast`
