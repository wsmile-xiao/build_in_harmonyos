# DRAFT: 被测程序内部 exec 外部命令的测试替身模式——环境变量命令前缀注入（RENICED_PS_CMD 模式）

- Status: UNMATCHED
- 来源: reniced 1.23 shadow CI r4–r8（2026-10-01）
- 关联: DRAFT-hmdfs-script-exec-interpreter（外部调用脚本须显式解释器）、E325（test_package 先解析 shell）——本条解决的是**互补问题**：不是"我们怎么调用脚本"，而是"被测程序自己 exec 外部命令时怎么替换"

## 问题场景

被测 CLI（如 reniced）在内部通过 shell 执行外部命令：

```perl
open PS, '-|', $cmdline        # $cmdline = "ps H -o lwp,comm --user $uid"
```

真机无法用常规手段 mock `ps`：

- 新建脚本文件（mock ps 放 PATH 目录）chmod 755 后仍被 SELinux 拒绝 exec（HMDFS 与非 HMDFS 分区均如此，同 DRAFT-hmdfs-script-exec-interpreter 的根因）；
- 也无权限写入 /data/service/hnp/bin 等已有可执行目录。

## 解法模式（一行注入 + 前缀拼接 + mock shift）

1. **打包脚本注入一行命令覆盖点**（默认不设置环境变量时行为与上游逐字一致，属可公开说明的最小适配）：

```perl
# 上游原句
open PS, '-|', $cmdline or die "can't open `$cmdline': $!\n";
# 注入后
my $ps_cmd = defined $ENV{RENICED_PS_CMD} ? "$ENV{RENICED_PS_CMD} $cmdline" : $cmdline;
open PS, '-|', $ps_cmd or die "can't open `$cmdline': $!\n";
```

要点：**前缀拼接** `$ENV{XXX} . " " . $cmdline`，而不是整体替换——原命令行
参数串（`ps H -o lwp,comm --user <uid>`）必须保留，否则 mock 收到空参数
（reniced r6 实测踩坑）。debug/die 消息仍引用原 `$cmdline`，verbose 输出与
上游期望保持逐字一致。

2. **mock 用显式解释器调用并 shift 掉原命令首词**：

```perl
shift @ARGV if @ARGV && $ARGV[0] eq 'ps';   # 丢弃前缀拼接带上的 "ps"
my $argstring = join ':', '', @ARGV;        # 按上游 mock 的方式校验剩余参数
```

3. **测试运行时**：`RENICED_PS_CMD='"<perl绝对路径>" "<mock.pl>"'`，
   经 os.environ / subprocess env 传入（进程链继承即可，无需改 run 调用）。

## 适用面

任何"被测程序在运行时 exec 外部命令（ps/git/curl/sh 等）+ 真机禁 exec 新建
文件"的包：把外部命令调用点改为环境变量可覆盖的命令前缀，即可在测试里注入
显式解释器运行的 mock，同时不改变默认行为。test_package 用同一注入点即可验
证**打包原文件**（比"改副本再测"更强的消费者验证）。

## 验证

reniced/1.23：r7（整体替换丢参数）失败 → r8 前缀拼接后上游 3 个 no-op 测试
输出与 .expected 逐行一致、test_package 打包原文件 no-op 输出与上游
normal-run.expected 逐行一致，L1e 破坏性反向验证通过，exit 0。
