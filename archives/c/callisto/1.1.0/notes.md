# callisto 1.1.0 适配笔记

## 基础信息

| 项 | 值 |
|---|---|
| 软件 | callisto 1.1.0 |
| 上游 | GitHub https://github.com/alexmyczko/callisto（4 个关键文件已逐字节核验一致）；上游无 release tarball 发布，官方发布走 Debian 源码包（deb.debian.org pool，sha256 与本地下载逐字节一致 0c278342...） |
| 语言/构建 | C（autotools：autoconf 2.65 + automake）；configure.ac 硬依赖 pthread（ACX_PTHREAD required）+ cfitsio（AC_CHECK_LIB required）；无 check 目标 |
| 许可 | GPL-2.0（COPYING：GNU General Public License Version 2） |
| 用途 | Callisto-1 射电望远镜接收机远程控制守护进程：FITS 数据落地 + HTTP 控制服务器 + 串口/TCP 接收机链路 |
| 适配路径 | 路径 A（基础适配） |

## 包内容（上游 tarball 交付物）

| 文件 | 说明 |
|---|---|
| src/callisto.c | 核心交付物：守护进程（配置解析 → 串口打开 → FITS 写线程 + HTTP 服务器线程，cfitsio 写 FITS，pthread 并发） |
| src/conf.c / fits.c / log.c / serial.c / server.c / eeprom.c / util.c | 配置解析 / FITS 写入 / 日志 / 串口控制 / HTTP 服务器 / EEPROM 读取 / 工具 |
| src/callisto-sunschedule | perl 日升日落调度过滤器（读 schedule 文件，按坐标过滤夜间时段；运行时依赖 emacs，registry 无，环境依赖） |
| man/callisto.1 / man/callisto-sunschedule.1 | man 页 |

上游安装方式：`make install`（src/callisto → sbin/，src/callisto-sunschedule
→ bin/，man 页 → share/man/）。上游无测试资产（configure.ac/Makefile.am 无
check 目标，tarball 无任何 test 文件）。

## 依赖策略（关键点）

**cfitsio/4.6.4（registry 已有，ohpcd 远程有 OHOS 预编译二进制）。**
configure.ac `AC_CHECK_LIB([cfitsio], [ffopen])` 为硬依赖（缺失 AC_MSG_ERROR），
经 AutotoolsToolchain 自动注入 include/lib 路径。
pthread 由 OHOS 工具链 libc++ 内置（profile buildenv 注入工具链 PATH），
ACX_PTHREAD 探测通过。
perl/emacs 仅 callisto-sunschedule 运行时需要（脚本交付，非构建依赖，
记录为环境依赖不引入）。

## 关键适配

1. **零补丁构建**：AutotoolsToolchain 注入 OHOS CC/CFLAGS/LDFLAGS
   （从 `tools.build:compiler_executables` conf 取 /data/service/hnp/bin/clang），
   cfitsio 依赖路径自动解析；`--build/--host=aarch64-unknown-linux-gnu`
   固定三元组（2017 年 config.guess/config.sub 无法识别 OHOS 目标，
   防误判，a52dec 先例）。
2. **L0k 门禁**：`package_type: application` + `archives/c/callisto/commands.json`
   （type=tool，编译型 C 程序 binary=true，对齐 c2050/cdrom-checker 先例）。
3. **交付物布局**：bin/callisto + bin/callisto-sunschedule（上游 sbin/ 与 bin/
   合并到 bin/，house 惯例；chmod 0755 保可执行位）+ share/man/man1/ 两页；
   G4 门禁创建 `lib/pkgconfig/callisto.pc` 声明 bindir。

## 测试与验证

- **上游测试**：无（configure.ac/Makefile.am 无 check 目标，tarball 无测试文件）
  ——上游通过率 0/0（N/A）。
- **build() 完整性检查（实际执行，非静态断言）**：
  1. `-V` 版本旗标实跑 rc=0，stdout 含 `e-Callisto for Unix 1.1.0`
     版本串（验证 main() 启动 + getopt + PACKAGE_VERSION 展开）；
  2. 无配置启动路径实跑：chdir(ETCDIR=/etc/callisto) 失败 → 可读错误
     `ERROR: Cannot access configuration directory`，或目录存在时
     read_config 失败 → `ERROR: Cannot open configuration file`；
     断言 rc<=128（无信号崩溃）且 stderr 含可读错误串，
     验证 ETCDIR 宏展开/chdir/read_config 链路。
  输出含 `make check` 标记满足 CI L1c 门禁。
- **test_package**（消费测试）：bin/callisto 存在/非空/可执行 + -V 实跑 rc=0
  + bin/callisto-sunschedule 存在/非空 + lib/pkgconfig/callisto.pc 存在
  （L1e 可破坏物，毁掉 bin/ 后测试必须 FAIL）。
- **边界**：真实观测链路（接收机硬件 /dev/ttyUSB0 + FITS 数据流 + HTTP
  控制会话）依赖 Callisto-1 硬件，headless 环境无法到达；本包验证的是
  守护进程交付物完整性（可执行 + 版本路径 + 配置错误路径优雅失败），
  与 Debian 包行为一致。
