# mtm — OpenHarmony 编译档案

## 软件简介
mtm（Micro Terminal Multiplexer）是一个轻量终端多路复用器：单个 C 源文件（mtm.c）加一个 VT 解析器（vtparser.c），基于 ncursesw，通过 forkpty 托管 shell，提供分屏（水平/垂直/标签页）、聚焦切换、重命名、缩放与隐藏等操作（命令键 Ctrl-g，可经 -c 自定义）。

## OHOS 适配要点
- 自定义 Makefile（28 行，无 configure，E097）：CC/LIBPATH 为 `?=`，可命令行覆盖，无需补丁
- 上游默认目标内联 `strip mtm`（OHOS 签名工具链拒绝剥离后二进制，E077）——配方改为 make 编译目标文件 + 自行链接（与 Makefile 同规则，仅去掉 strip）
- 上游 `cp -i config.def.h config.h` 规则在重建时会交互阻塞（E214 族）——不调用该规则，tarball 自带 config.h，无需补丁
- `-lutil` 去除：OHOS musl 将 libutil 并入 libc，sysroot 仅含空壳 libutil.a（无成员），forkpty 直接由 libc 提供
- `-D_DEFAULT_SOURCE` 补充 ncursesw 在 musl 上的特性宏可见性（E033 族）
- 许可证：GPL-3.0-or-later（源码包无 LICENSE 文件，声明位于 mtm.c 头部与 README.rst "Copyright and License" 节）

## 依赖关系
- 运行时：ncurses/6.6（宽字符构建；runenv 提供 TERMINFO 数据库，含 `screen` 条目）
- 编译器从 Conan conf `tools.build:compiler_executables` 获取（OHOS clang）

## 上游测试
- 上游正式测试为 0：tarball 仅含 mtm.c/vtparser.c/pair.c/mtm.1/mtm.ti/config.def.h/README.rst，Makefile 无 test/check 目标，README.rst 第 44 行注明 vttest 截图 "but have not been tested"
- 详见 test_package/MANIFEST.yml 的完整审计；test_package 以 pty 功能测试替代（4 项断言）

## 参考资料
- [mtm GitHub](https://github.com/deadpixi/mtm)
- [mtm man page (deadpixi.com)](https://deadpixi.com/mtm.html)
