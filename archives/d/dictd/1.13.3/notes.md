# dictd 1.13.3 适配笔记

## 构建系统
- autotools 风格（非 automake 生成）：tarball 自带 configure / config.h.in / 自定义 Makefile.in，
  无需 autoreconf。构建期需要 flex + bison（scanners 自带 yywrap，不需要 -lfl）与 awk。
- configure 无条件 `AC_LIBOBJ` 一批宽字符回退实现（wcrtomb/wctomb/mbstowcs 等），
  属上游设计，并非 musl 缺失信号，勿"修复"。

## vendored libmaa（方案 a）
上游 configure 硬依赖 `libmaa`（`AC_CHECK_LIB(maa, maa_shutdown)`，`#include <maa.h>`），
而仓内无 libmaa Conan recipe。经批准在 dictd recipe 内 vendored 静态构建：

- 源：官方 SourceForge `libmaa-1.4.7.tar.gz`，SHA256 固定于 conandata.yml。
- libmaa 自身是 BSD make (mkc) 构建系统，不兼容 GNU make，vendored 构建直接编译
  `maa/*.c` 为 `libmaa.a`（全量 22 个源文件，含 bit.c/timer.c）：
  - mkc 特性宏以命令行提供：`-DSIZEOF_LONG=8`（aarch64 LP64）、
    `-DHAVE_HEADER_SYS_RESOURCE_H=1`（musl 提供 sys/resource.h；timer.c 需要
    struct rusage/getrusage，且 maa.c 的 maa_init/maa_shutdown 引用 timer.c 的
    tim_* 符号——**排除 timer.c 会导致链接失败**，archives/l/libmaa/1.4.7/notes.md
    中"排除 bit.c/timer.c"的旧结论实为缺宏误诊，本 recipe 已纠正）；
  - `-DMAA_MAJOR=4 -DMAA_MINOR=0 -DMAA_TEENY=0`；
  - `arggram.c` 由 `awk -f arggram2c < arggram.txt` 预生成（arg.c 需要）；
  - `maaP.h` 的 `HAVE_HEADER_ALLOCA_H` 留空即可（`#if` 未定义宏按 0 处理）；
    `log.c` 的 `HAVE_SYSLOG_NAMES` 未定义时自带回退。
- dictd 侧以 `CPPFLAGS=-I<vendor>/maa LDFLAGS=-L<maa-build>` configure（INSTALL 官方支持的姿势），
  链接只拉入 maa.o 及其闭包，符号面极小。

## 平台行为
- `daemon()`：musl 提供；dictd 默认 daemonize 只影响上游测试的 nodetach 一组
  （其余用例走 `dictd --stdin2stdout` 管道，不经 socket/daemon）。
  设备实测 nodetach 组可正常通过（daemon() 未被沙箱拦截）。
- 上游测试 nodetach 组绑定固定端口 localhost:26281，并行跑多库 CI 时存在撞端口可能。
- 测试 harness 依赖 m4/awk/diff/cmp/sort/cut/head/sed/grep，设备均有可用版本
  （GNU awk 5.4、GNU diffutils 3.10、m4 随 autoconf 提供）。
- HMDFS 新建目录上 getcwd() 失败：bash 以该类目录为 cwd 启动时在 shell-init 阶段
  即失败（"error retrieving current directory"）。对策：构建/测试均改在
  /data/storage/el2/base 下的 tmpfs 工作区进行，且所有 shell 命令以
  `cd '<workdir>' &&` 前缀重建有效工作目录（test_package 的 test() 同样处理）。
- AC_PROG_LEX(yywrap) 在找不到 -lfl 时把 LEX 降级为 `:`（静默不生成 scanner），
  而 dictd 的 scanners 自带 yywrap、无需 libfl；故在 make 前按上游原始命令行
  预生成 servscan/servparse/clientscan/clientparse 四个文件，绕开该行为。
- 上游不单独产出 `dictunzip`：dictzip.c 按 argv[0] 分派（`!strcmp(pt,"dictunzip")`
  即解压模式），上游 install 也不装 dictunzip 文件；发行版惯例是以指向 dictzip
  的链接提供，本 recipe 同样在 bin/ 下建 dictunzip→dictzip 链接。

## 上游测试
- 入口：`make test`（Makefile.in 无 check 目标）：`cd test && sh dictd_test && sh dictzip_test`。
- 覆盖：dictfmt/dictunformat/index 往返与选项矩阵、dictzip 压缩与随机解压、
  dictd 协议应答（cyrillic/utf8/limits/defstrat/mixedcase 等），期望输出逐条 diff。
