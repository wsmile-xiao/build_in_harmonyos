# snpomatic

SNP-o-matic —— Magnus Manske 写的严格型短序列比对 / SNP 检出套件（C++，裸 Makefile 构建）。
上游仓库：<https://github.com/magnusmanske/snpomatic>（许可证 GPL-3.0-or-later，
包内附 `gpl-3.0.txt` 与 `doc/Manual.doc`）。

## 本仓交付的版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 1.0 | built | tag `v1.0`，官方归档取源，零补丁 |

## 提供的可执行文件

`1.0` 交付上游五个目标中在本 tag 真能编译的四个：

| 程序 | 作用 |
|------|------|
| `findknownsnps` | 主程序：把 FASTA/FASTQ 读段比对到参考，找已知/新 SNP（Debian 也只装这一个） |
| `reassemble` | 利用比对结果做重叠群重装配 |
| `variety` | 基于读段的序列型基因分型（variety calling） |
| `mapcontigs` | 重叠群到参考的比对 |

`ungap` **未交付**：该目标的源码在 tag `v1.0`（以及上游 master）不自洽，
`src/ungap.cpp:261` 以 4 个实参调用 5 参的 `align_solexa_paired`
（声明 `src/snpomatic.h:179`，无默认实参），属上游缺陷而非平台问题；
本仓不改上游源码、不打补丁，证据与处置见 `1.0/notes.md`。

## 依赖

零第三方编译依赖：上游 `Makefile` 只有 `LIBS=-lm`，`#include` 全集为 STL + POSIX。

## 使用提示

上游所有程序都没有 `--version`，且**对所有错误路径都 `exit 0`**（只打印用法），
脚本化调用时请押输出内容而不是退出码。
