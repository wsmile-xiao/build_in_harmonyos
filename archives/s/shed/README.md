# shed

## 简介

shed（Simple Hex EDitor）是 Alex Sisson 编写的终端十六进制编辑器：全屏 ncurses 界面，
操作风格接近 pico。它不把文件读进内存，编辑直接写回磁盘文件（没有保存键），也可以只读查看管道输入。

## 功能概述

- 每个字节一行：偏移量，加上 asc / hex / dec / oct / bin 五列同时显示
- 编辑：在当前列的进制下改写字节；1/2/4 字节游标与大小端切换；二进制列可逐位翻转
- 搜索：按当前列的进制搜索字节序列（ascii 列可忽略大小写），支持向前/向后与重复搜索
- 跳转：`j` 跳到偏移量、`top`、`end`，支持 K/M/G 单位；`t` 切换十进制/十六进制偏移
- `d` 把整个文件按 shed 的显示格式（表头 + 每字节一行）导出为文本表；`p` 预览；`a` 切换 ascii 列显示方式
- 命令行：`-r/--readonly`、`-s/--start=OFFSET`、`-H/--hex`、`-L/--length`、`-h/--help`、`-v/--version`；
  文件名省略或为 `-` 时读取管道/重定向输入（`-n/--nofollow` 需 configure 时 `--enable-nofollow`，本包默认不含）

## OHOS 适配

### 1.16（feat/shed-1.16）

- 构建系统：autotools，发布包自带 autoconf 2.71 生成的 `configure`，配方直接使用，不重新生成
- `configure.ac` 没有 `AC_CANONICAL_HOST`：构建机与目标同为 OHOS profile 时 Conan 不传 `--host`，
  x86 runner 上 configure 会因无法执行 OHOS 动态 conftest 而失败；配方只传 `--host=aarch64-linux-ohos`，
  让 configure 自行探测（设备上原生，x86 上按交叉处理），不会调用 `config.sub`
- 管道输入（`producer | shed`）：shed 用 `tmpfile()` 缓冲。据 NDK `libc.a` 中 `tmpfile.o` 的模板字符串
  （`/data/local/tmp/tmpfile_XXXXXX`）与知识条目 E272 的设备实测（EACCES），OHOS musl 的 `tmpfile()` 写死该目录、
  不读 `TMPDIR`，普通进程无权写入，上游会报 `tmpfile() failed.`；补丁 0001 在 `$TMPDIR` 下 `mkstemp()` + `unlink()`
  建立匿名缓冲文件，未设置 `$TMPDIR` 时回落 `tmpfile()`
- ncurses/6.6 只提供静态宽字符库（`libncursesw.a`）；terminfo 数据库随 ncurses 包提供，
  配方以 `run=True` 依赖它，运行环境（`conanrun`）导出 `TERMINFO`
- ncurses 以 root（uid 0）运行时忽略 `TERMINFO`（x86 runner 上以 root 做 qemu 实跑已复现；据 ncurses 源码与库内符号推断，
  是 ohpcd 构建时 configure 把系统判为非多用户系统所致），需以普通用户运行，见知识草稿 `E429-draft-5ED1`
- OHOS SDK 链接器写入的 `.codesign` 段不被加载器认可，`package()` 对 `bin/shed` 重新自签
- 上游没有测试套件（无 `tests/`，`make check` 无注册用例）；`test_package` 补全 7 个消费者用例（37 条断言），
  经管道与伪终端驱动包内 `bin/shed`，其中 2 个为鸿蒙特有用例（管道输入缓冲在 `$TMPDIR`）
- 命令行工具，已按 R38 声明 `commands.json`

## 依赖关系

- 编译依赖：ncurses/6.6、C 编译器、make
- 运行依赖：ncurses 包内的 terminfo 数据库（`share/terminfo`，由 Conan 运行环境导出 `TERMINFO`）；动态链接 musl `libc.so`

## 参考资料

- 项目主页：<https://sourceforge.net/projects/shed/>
- 源码包：<https://downloads.sourceforge.net/project/shed/shed/shed%201.16/shed-1.16.tar.gz>
