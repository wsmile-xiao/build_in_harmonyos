# E544（草稿 31E6）— 构建期生成器读「构建机」/usr/include：交叉编译与鸿蒙真机上静默生成空表

> 状态：草稿（适配 `archives/s/shush/1.2.3` 时产出，建议主编评估后 promote）
> 字段见同名 `.kv`；E 编号为草稿占位，正式编号由主编分配。

## 现象

构建与 `conan create` 全部成功，产物也能运行，但凡是按**名字**解析信号的功能都失效：

```text
shush encountered the following error(s) while running "slow" on host ...:

Invalid "timeout" signal: SIGTERM
```

配置 `timeout=2s,SIGTERM` 的作业不会在 2 秒后被终止，而是跑满全程（实测 60 s）。
构建日志里唯一的线索是一条看起来无害的规则：

```make
signals.h: signals.awk Makefile
	cat /usr/include/signal.h /usr/include/sys/signal.h \
		/usr/include/sys/iso/signal_iso.h \
		/usr/include/bits/signum.h 2> /dev/null | \
		awk -f signals.awk > signals.h
```

生成的 `signals.h` 只有哨兵项：

```c
struct signame signame[] = {
    { NULL,	 0 }
};
```

## 根因

生成器读的是**构建机**的系统头，而且 `2> /dev/null` 把缺失吞掉了：

| 构建环境 | cat 能读到的内容 | 结果 |
|---|---|---|
| 鸿蒙 PC 真机（CI worker） | 没有 `/usr/include` | 空表 |
| x86_64 交叉构建机（Debian 12） | `signal.h` 不含 `#define SIGxxx <n>`；`bits/signum.h` 在 multiarch 目录 `/usr/include/x86_64-linux-gnu/`，上述路径不存在 | 空表 |
| 老式单架构 Linux | 宿主 libc 的编号 | 有表，但属于**构建机**而非目标机 |

空表下 `getsignumbyname()` 对任何名字返回 -1：配置解析报 `Invalid "timeout" signal`，超时动作执行
`kill(-pgrp, -1)` 失败，作业不会被终止。编译、链接、打包、只跑 `-V` 的冒烟测试都发现不了。

## 修法（shush `patches/0005-src-Makefile.in.patch`）

向**目标编译器**要宏值，而不是去构建机上找头文件：

```make
signals.h: signals.awk Makefile
	@rm -f signals.h
	echo '#include <signal.h>' | $(CC) $(CPPFLAGS) -E -dM -x c - | \
		awk -f signals.awk > signals.h
	@grep '"TERM"' signals.h > /dev/null || \
		{ rm -f signals.h; echo "signals.h: no signal found" >&2; exit 1; }
	@chmod 644 signals.h
```

- `-dM` 的输出形如 `#define SIGHUP 1`，与原 awk 规则 `/^#define[ \t]+SIG[A-Z1-9]+[ \t]+[0-9]+/`
  完全兼容，`signals.awk` 不用改；OHOS musl sysroot 下得到 HUP…SYS 共 31 个信号。
- `$(CC)`/`$(CPPFLAGS)` 由 Conan 工具链注入（R33），交叉机、真机、普通 Linux 行为一致；
  不需要平台分支，也不需要 `__OHOS__`（R8）。
- 空表检查把问题从运行期提前到构建期。
- 附带现象：`-dM` 还会带出 `SIGSTKSZ 12288`（非信号，awk 规则会收进表），只是多一个
  永远不会被用到的名字，无害。

## 验证（反向对照，同一消费者用例）

`test_package/test_shush.c` 的 C6：配置 `timeout=2s,SIGTERM` + `if=$exit == -15`，作业 `sleep 60`。
在 x86_64 构建机上用同源 `.o` 静态重链副本经 `qemu-aarch64` 执行：

| 构建 | signals.h | C6 结果 |
|---|---|---|
| 本配方（补丁 0005） | 31 个信号 | PASS：约 2 s 后收到 SIGTERM，`$exit == -15` 的报告送达 |
| 上游规则（空表） | 仅哨兵 | FAIL：`Invalid "timeout" signal: SIGTERM`，作业跑满 60.1 s，无报告 |

交付的动态产物在 aarch64 CI worker 上由同一 C6 用例执行。

## 与相近条目的区别（查重）

- `engine` 以本条签名检索无命中（仅关键词误命中 E106「GNU cat stdout 权限」，与本条无关）。
- `DRAFT-inputlirc-34-hardcoded-usr-include-uapi-path-resolved-via-clang-M`：同样是「上游假设头在
  `/usr/include`」，但那里是 make 前置条件断链、构建**直接失败**；本条是 `cat … 2>/dev/null`
  吞掉缺失后**构建成功、运行期静默失效**，修法也不同（`-E -dM` 取宏值 + 空表检查，而非 `-M` 反解路径）。
- E543（正式条目）：老 autotools 项目交叉/原生构建的三类适配点（AC_TRY_RUN 无交叉分支、lex/yacc 生成器依赖、
  无 make check），不涉及「构建期生成器读宿主系统头」这一类；草稿 `E543-draft-419E`（jday，config.guess/config.sub
  三元组）同样不涉及。

## 同包的同族现象（未单列条目，供主编判断）

「构建机事实被静默烙进目标产物」在 shush 里还有一处：`configure.ac` 的
`AC_PATH_PROG([SENDMAIL], [sendmail], [NOSENDMAIL], [/usr/lib:/usr/sbin:$PATH])` 在交叉构建时探测的是
构建机——x86_64 runner 上烙进 `/usr/lib/sendmail`，鸿蒙真机上则是 `NOSENDMAIL`。配方用
`ac_cv_path_SENDMAIL=NOSENDMAIL ac_cv_path_CRONTAB=NOCRONTAB` 钉成目标机上的结果，消费者用例 C5 覆盖
（未钉死的构建：`config.h` 中 `SENDMAIL` 为 `/usr/lib/sendmail`，C5 FAIL——没有 `execv(NOSENDMAIL)` 诊断）。
