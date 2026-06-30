# unifdef

unifdef 是一个用于选择性处理 C 预处理器条件编译指令的工具。它可以移除或保留 `#ifdef`、`#ifndef`、`#elif`、`#else` 和 `#endif` 等指令控制的代码块，同时保持代码结构完整。

- **官网**: http://dotat.at/prog/unifdef
- **许可证**: BSD-2-Clause AND BSD-3-Clause
- **语言**: C
- **构建系统**: 自定义 Makefile（非标准 autotools，无 configure 脚本）
- **作者**: Tony Finch (dot@dotat.at)

## 功能概述

- 选择性移除条件编译代码块（`#ifdef`/`#ifndef`/`#else`/`#elif`/`#endif`）
- 支持宏定义（`-D`）和反定义（`-U`）参数
- 支持合并模式（`-m`）保留输出文件权限
- 支持保留模式（`-k`）保留被移除的代码块（注释化）
- 支持行号输出（`-n`）
- 提供 `unifdefall` 脚本，可完全展开所有条件编译

## OHOS 适配

- unifdef 使用自定义 Makefile，不依赖 autotools 的 configure 脚本
- 编译命令: `make CC=clang CFLAGS="-fPIC -O2"`
- 安装命令: `make install DESTDIR=<dir> prefix=<prefix>`
- 需要创建 `cc → clang` 软链接，因为 `unifdefall.sh` 脚本内部调用 `cc`
- 测试套件中 `outeperm` 和 `overperms` 测试因 HMDFS 文件系统权限行为差异失败（非功能缺陷）
- 终端工具，产物为 `unifdef` 和 `unifdefall` 可执行文件

## 依赖关系

- 编译依赖: 无
- 运行依赖: libc（系统库）
- `unifdefall` 脚本依赖 `cc` 编译器（需软链接到 clang）

## 参考资料

- 官网: http://dotat.at/prog/unifdef
- 源码下载: https://dotat.at/prog/unifdef/unifdef-2.12.tar.gz
