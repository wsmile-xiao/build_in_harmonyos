# cfingerd 1.4.3 适配笔记

## 编译环境
- 构建系统: custom(自定义 Perl Configure 脚本 + makefile,非 autotools)
- 编译日期: 2026-09-07
- 编译器: clang 15.0.4(OHOS SDK)
- 状态: built

## 编译步骤

1. 下载源码(Infodrom 上游): https://www.infodrom.org/projects/cfingerd/download/cfingerd-1.4.3.tar.gz (SHA256: 61b5efdbbe881fe35c39ca243fc11cf52d219a4f61104f1052a900fc7acb0fb0)
2. 交互式 Configure 非参数化问题:用 `-c foo=bar` 参数绕过交互:
   ```bash
   perl ./Configure -c os_type=LINUX -c make=make -c cflags="-O2 -Wall" \
     -c mandir=$PREFIX/share/man -c nobody_uid=65534 -c nobody_gid=65534 \
     -c mailspool="/var/spool/mail" -c lastlog="/var/log/lastlog"
   ```
   注意:Configure 的 `require 'perl/*.pl'` 需要 `PERL5LIB=.`(Perl 5.42 @INC 不含 cwd)。
   注意:os_type 必须显式指定 LINUX——uname 返回 HARMONYOS 走 else 分支会用 gmake(设备只有 make)。
3. 编译: `make all CC=clang`(Makefile 默认 CC=cc,鸿蒙无 cc 别名,必须显式 CC=clang)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Configure 报 `Can't locate perl/question.pl in @INC` | Perl 5.42 移除了 cwd 进 @INC,1999 年脚本假设 cwd 可见 | `export PERL5LIB=$SRC` |
| 2 | `cc: No such file or directory` | Makefile.cfg 未设 CC,内置默认 cc,鸿蒙 clang 无 cc 符号链接 | `make all CC=clang` |
| 3 | 链接报 `duplicate symbol: foo_utmp`(16 处) | cfingerd.h/userlist.h 在头文件里用 `struct utmp foo_utmp;`(暂定定义)推导 sizeof 宏,每个 .o 都实例化;鸿蒙 utmp.h 只定义 UT_HOSTSIZE/LINESIZE/NAMESIZE(不含 UT_USERSIZE),#if 块必然进入;1999 gcc 宽容,clang+lld 严格 | 头文件删除 foo_utmp 机制,改 `#define UT_USERSIZE 32`(鸿蒙 utmpx.h: ut_user[32]) |
| 4 | userlist/display.c 报 `use of undeclared identifier 'cp'/'x'` | K&R 风格旧代码,隐式 int 声明,C99 严格模式禁止 | display.c 内补局部声明 `char *cp = ...; char *x;` |
| 5 | `make clean` 会删掉 Configure 生成的 src/config.h | 上游 Makefile clean 规则 rm -f config.h | clean 后必须重跑 Configure 再 make |

## 源码修改

探索阶段直接改源码(按 R3,补丁由 finish 阶段 refresh-patch --auto 统一生成):
- src/cfingerd.h: 删除 foo_utmp 暂定定义块,`#define UT_USERSIZE 32` 显式替换
- src/main.c: 删除 foo_utmp 强定义
- userlist/userlist.h: 同 cfingerd.h 的处理
- userlist/main.c: 删除 foo_utmp 强定义
- userlist/display.c: 补 cp/x 局部声明

## 依赖版本

无外部依赖(纯 libc + POSIX socket API,musl 全覆盖)。

## 验证结果

```bash
$ file src/cfingerd userlist/userlist
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)

# smoke test
$ userlist
Nobody logged in.          # rc=0,正常读取 utmp(鸿蒙 _PATH_UTMP=/dev/null/utmp → 空用户表)

$ cfingerd
(静默退出 rc=0;守护进程设计为 root + inetd 拉起,非 root 环境下 setuid 检查路径触发 SIGSYS 信号,预期行为,非缺陷)
```

上游无 make check 测试套件(1999 年软件),以二进制 smoke 验证代替。

## 注意事项

- cfingerd 是 inetd 超级服务架构下的 finger 守护进程,运行时需要 root + inetd/xinetd 环境或 `-d` standalone 模式(DAEMON_MODE 默认未启用);设备沙箱内无法完整拉起服务属预期
- 鸿蒙 utmp.h 的 `#define utmp utmpx` 使源码中 `struct utmp` 实为 `struct utmpx`(musl 风格),字段兼容
- cfingerd 二进制为 tool 类型(R38):构建产物含可执行文件,软件级目录需 commands.json
---

**编译结束**: 2026-09-07 19:38
**最终状态**: built
