# poster - PostScript 海报缩放/分块打印工具

## 简介

poster 是 Jos van Eijndhoven（埃因霍温理工大学）1995 年编写的 PostScript
缩放工具：将一页 PostScript 输入放大成大幅面海报，并自动分块平铺到多张
打印纸上。每张分块页带有裁剪标记（cropmarks）和少量重叠区域，便于拼接
组装。输出介质尺寸可独立于放大倍数选择。

典型用法（手册页示例）：`cat input.ps | poster -p2x2 -mA4 > output.ps`，
即把一页 PS 放大 2 倍平铺到 4 张 A4 纸上。

## 功能特点

- `-p<box>`：输出海报尺寸（如 `2x2A4` = 放大到 2x2 张 A4；`A0`、`10x25cm` 等）
- `-m<box>`：打印介质尺寸（A4/A3/A2/A1/A0/letter/legal/tabloid 等）
- `-s<number>`：线性缩放因子（与 -p 互斥）
- `-c<margin>`：裁剪边距（绝对尺寸或百分比，默认 5%）
- `-w<margin>`：附加白边
- `-i<box>`：手动指定输入图像尺寸（缺省从输入文件 %%BoundingBox 读取）
- `-P<pages>`：只打印指定分块页（如 `1,2-5`）
- `-o<file>`：输出重定向到文件（缺省 stdout）
- `-v`：详细模式；`-f`：手动送纸
- stdin→stdout 管道式工作流，支持 EPS/PS 输入

## 官方信息

- **源码（Debian pool 权威镜像）**: https://ftp.debian.org/debian/pool/main/p/poster/poster_20050907.orig.tar.gz
- **上游作者**: Jos van Eijndhoven (Eindhoven University of Technology)
- **许可证**: GPL-2.0
- **版本说明**: 20050907 为上游最后版本（1995 年首发，2005-09-08 最后更新，Debian 以日期为版本号）

## 编译版本

当前已编译版本：20050907

### 已知平台适配要点

1. **Makefile gcc 硬编码**
   - 上游 Makefile 唯一构建规则为 `gcc $(CFLAGS) -o poster poster.c -lm`，
     编译器是字面量而非 `$(CC)`，`make CC=<cc>` 覆盖无效（实测 OHOS 上
     Error 127：环境无 gcc）
   - 配方 build() 用 sed 把规则里的 `gcc` 改写为 `$(CC)`，再以
     `make -e`（Toolchain 环境的 CC/CFLAGS 覆盖 Makefile 内置值）驱动
     构建（R33 合规，编译器来自 Conan Toolchain 而非裸 shell 变量）

2. **install 目标不可用**
   - 上游 `make install` 硬编码 `strip poster` + 绝对路径
     `/usr/local/bin`、`/usr/local/man/man1`
   - 配方 package() 手动布局：`bin/poster`、`share/man/man1/poster.1`、
     `share/doc/poster/`（README/COPYING/manual.ps）

3. **运行时 TEMP 环境变量（E002 关联）**
   - poster 管道模式下先用 `tmpinfile()` 把 stdin 落成临时文件，路径取
     `TEMP` 环境变量（不是 TMPDIR！），未设置时用 `/tmp`（OHOS 只读）
   - 使用管道模式时需 `export TEMP=<可写目录>`

4. **代码年代**
   - 2005 年最后更新的 K&R 风格 C，clang 15 `-Wall` 下零告警零错误，
     无需任何补丁；tarball 中的 getopt.c 不参与构建（Makefile 只编
     poster.c），无 getopt 符号冲突

## 使用示例

```bash
# 把一页 A4 PS 放大 2 倍平铺到 4 张 A4（需 export TEMP）
export TEMP=$TMPDIR
cat input.ps | poster -p2x2A4 > output.ps

# 放大到一整张 A0 纸
cat input.ps | poster -mA0 -s4 > output.ps

# 只打印第 1、2 块
cat input.ps | poster -p2x2A4 -P1,2 > output.ps

# 从文件读取并输出到文件
poster -v -mA2 -c1cm input.ps -o output.ps
```

## 编译状态

- **版本**: 20050907
- **状态**: built
- **编译日期**: 2026-09-03
- **构建系统**: makefile（plain，非 autotools/cmake）
- **依赖**: 无 conan 依赖（纯 C 标准库 + 系统 libm）
- **产物**: 单一可执行文件 `bin/poster`（package_type=application）
