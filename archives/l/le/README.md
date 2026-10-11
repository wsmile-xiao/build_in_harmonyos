# le

LE —— 带块操作与二进制处理能力的文本编辑器（上游 http://lav.yar.ru/programs.html ，
版本 `1.16.8`，Debian 源码包 `le`）。

## 功能概述

- 矩形/流式块操作、二进制安全编辑、十六进制模式、大文件与 mmap 设备编辑
- 可配置语法高亮、键位映射与配色（`--dump-keymap` / `--dump-colors` 可离线导出）
- 同时支持 Unix 与 DOS 换行（LF/CRLF）

## OHOS 适配

- release tarball 自带生成好的 `configure`/`Makefile.in`，不需要 autoreconf，
  因此不涉及 perl/gettext 引导链问题
- 依赖 `ncurses/6.5`（制品仓为**宽字符静态库** `libncursesw.a`）；LE 自带的
  `LE_PATH_CURSES_DIRECT` 宏只按硬编码 `/usr/include*` 搜索、完全不走 CPPFLAGS，
  因此配方传上游支持的 `--with-curses-include=<ncurses 包>/include` 指到 Conan 头文件。
  宽字符库无需任何补丁：LE 自身的 `use_libcursesw` 探测到 `libncursesw.a` 后会把
  `-lncurses` 追加成 `-lncursesw`（曾误加同名补丁导致 `-lncursesww`，已回退）
- HMDFS 下构建目录作为进程工作目录时 `getcwd()` 失败，build() 里预置 `PWD`

## 依赖关系

- 编译依赖：`ncurses/6.5`（宽字符静态库）
- 运行依赖：无（静态链接 ncurses）

## 参考资料

- 上游：http://lav.yar.ru/programs.html
- Debian 打包：https://salsa.debian.org/salvage-team/le
