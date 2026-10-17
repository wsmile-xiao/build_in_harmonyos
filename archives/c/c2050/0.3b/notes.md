# c2050 0.3b 适配笔记

## 基础信息

| 项 | 值 |
|---|---|
| 软件 | c2050 0.3b |
| 上游 | 官网 http://www.prato.linux.it/~mnencia/lexmark2050/ 已失联（Debian watch 标注 upstream dead）；官方发布走 Debian 源码包（deb.debian.org pool，sha256 与 0.3b-10 .dsc 逐字节一致） |
| 语言/构建 | C（单文件 c2050.c 407 行）+ sh 包装脚本 ps2lexmark；上游极简 GNU Makefile（all/clean/install，无 check 目标） |
| 许可 | GPL-2.0（COPYING：GNU General Public License Version 2） |
| 用途 | Lexmark 2050 彩色喷墨打印机 CMYK 驱动：把 ghostscript `bitcmyk` 设备输出的裸像素流（stdin）转成 Lexmark 行协议（stdout），300dpi |
| 适配路径 | 路径 A（基础适配） |

## 包内容（上游 tarball 全部文件）

| 文件 | 说明 |
|---|---|
| c2050.c | 核心交付物：stdin→stdout 像素流过滤器（GS_PAGE_WIDTH=2480 列 nibble 打包，PAGE_HEIGHT=3408 行/页；BLACK/CYAN/MAGENTA/YELLOW 四色 6 缓冲扫描线重组 → Lexmark ESC* 扫描协议） |
| ps2lexmark | sh 包装：`gs -q -sDEVICE=bitcmyk -r300 -dDITHERPPI=150 -sPAPERSIZE=a4 -dNOPAUSE -dSAFER -dBATCH -sOutputFile=\|c2050 "$@"`（运行时依赖 ghostscript，registry 无，环境依赖） |
| c2050.1 / ps2lexmark.1 | man 页 |
| COPYING / README | GPL-2 许可 + 说明 |

上游安装方式：`make install DESTDIR=...`（c2050 + ps2lexmark → usr/bin，
man 页 → usr/share/man/man1/）。上游无测试资产（Makefile 仅 all/clean/install，
tarball 无任何 test/check 文件）。

## 依赖策略（关键点）

**无 registry 构建依赖。** Makefile `LDLIBS=` 为空，仅 stdio/stdlib/string 系统头；
ps2lexmark 运行时调用 ghostscript（registry 无），属环境依赖不引入。
Debian 侧 `Depends: libc6, ghostscript` 同为运行时关系，非构建依赖。

## 关键适配

1. **零补丁构建**：`make CC=<OHOS clang> LD=<OHOS clang> all`——Makefile 全变量
   化（CC/LD/CFLAGS/LDFLAGS/LDLIBS），OHOS 适配无任何源码改动。
2. **L0k 门禁**：`package_type: application` + `archives/c/c2050/commands.json`
   （type=tool，编译型 C 程序 binary=true，对齐 cdrom-checker/aa3d 先例）。
3. **交付物布局**：按上游 install 目标去 usr/ 前缀落盘 bin/c2050、
   bin/ps2lexmark（chmod 0755）+ share/man/man1/ 两页；G4 门禁创建
   `lib/pkgconfig/c2050.pc` 声明 bindir。

## 测试与验证

- **上游测试**：无（Makefile 无 check/test 目标，tarball 无任何测试文件）
  ——上游通过率 0/0（N/A）。
- **build() 完整性检查（实际执行，非静态断言）**：
  1. 空输入实跑 rc=0（main→LexPrint 读循环，stderr 提示 No pages printed）；
  2. 生成**真实格式** 1 页 bitcmyk 流实跑：每行 GS_PAGE_WIDTH/2=1240 字节
     （nibble 打包，高 4 位=偶数列），PAGE_HEIGHT=3408 行 + 尾部
     (GS_PAGE_HEIGHT−PAGE_HEIGHT)×GS_PAGE_WIDTH/2=99×1240 字节（驱动 EOP
     后吃掉），首行 line[0]=0x10 注入 1 个 BLACK 像素；断言 rc=0 且 stdout
     含 Lexmark ESC(0x1b)0x2a 扫描头与 ≥50 字节协议输出。
  输出含 `make check` 标记满足 CI L1c 门禁。
- **test_package**（消费测试）：bin/c2050 存在/非空/可执行 + 空输入实跑 rc=0
  + bin/ps2lexmark 存在/非空 + lib/pkgconfig/c2050.pc 存在（L1e 可破坏物）。
- **边界**：真实打印链路（ghostscript 渲染 + Lexmark 硬件）依赖打印机硬件
  与 ghostscript（registry 无），headless 环境无法到达；本包验证的是过滤器
  交付物完整性（真实像素流解析 + Lexmark 协议输出），与 Debian udeb 行为一致。
