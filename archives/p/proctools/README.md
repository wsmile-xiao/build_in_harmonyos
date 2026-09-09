# proctools

**BSD 进程工具套件**：pgrep、pkill、pfind 与 libproctools（OpenBSD 原生 + Darwin 移植版，2003-12-07 发布的最终版本 0.4pre1，适配 OpenHarmony PC / aarch64 / musl）

- **pgrep** — 按名字/命令行/uid/父进程等条件查找进程并打印 pid
- **pkill** — 按同样的条件向进程发送信号（默认 SIGTERM）
- **pfind** — find(1) 风格的表达式化进程查找器，支持 `-name/-args/-uid/-ppid/-pgrp` 等谓词与 `-kill/-dump/-id/-details` 等动作
- **libproctools** — 公共后端库（本包以 application 形式打包，工具直接可用）

## 用法

```bash
# 查找（不匹配自身，上游设计）
pgrep -l -x bash            # 精确名匹配，打印 pid + 名
pgrep -f "sleep 500"        # 匹配完整命令行
pgrep -n -x sleep           # 最新启动的 sleep（/proc starttime）
pgrep -d, -x sleep          # 逗号分隔输出
pgrep -P <ppid> -x sleep    # 按父进程过滤

# 发送信号
pkill -x sleep              # SIGTERM
pkill -9 -x sleep           # 数字信号
pkill -s HUP -x syslogd     # 信号名（sys_signame 解析）

# 表达式查找（选项须在表达式之前，上游设计）
pfind -x -name sleep                     # 精确名匹配
pfind -args ".*500"                      # 按参数匹配
pfind -x -uid 2001 -name sleep           # 组合谓词
pfind -x -name sleep -kill TERM          # 动作：杀
pfind -x -name sleep -dump dumpfile      # 动作：转储进程表
pfind -f dumpfile -name sleep            # 从转储读回
```

## 构建

- 构建系统：GNU Makefile（自上游 BSD bsd.prog.mk/bsd.lib.mk 布局重写；根 Makefile 编排 libproctools.a + 3 工具，子目录 Makefile 为委托薄壳）
- 源码：https://downloads.sourceforge.net/project/proctools/proctools/0.4pre1/proctools-0.4pre1.tar.gz （sha256 `4553b9c6…ec5538`）
- 许可证：BSD-3-Clause + BSD-4-Clause-UC（见 tarball 内 LICENSE）
- 零第三方依赖，纯 C

## OHOS 适配（14 个补丁）

- **/proc 后端重写**（procfs.c 新文件 ~300 行）：`/proc/<pid>/stat`（strrchr ')' 定位含空格 comm；token 2/3/5/20 → ppid/pgid/tty/starttime 按 CLK_TCK 换算）、`/proc/<pid>/status`（Uid:/Gid: 四列 → ruid/svuid/egid）、`/proc/<pid>/cmdline`（NUL join）；枚举 `/proc` 数字目录
- **kinfo_proc shim**（proctools.h）：OpenBSD 形状结构 + `p_starttime` 对象宏，getProcList 匹配主循环与 pgrep/pkill/pfind 前端零改动
- **bsd_compat.c 新文件**：strvis（vis(3) 全语义）、sys_signame[65]（musl SIGRTMIN=35/SIGRTMAX=64 实测对齐）、__progname
- **UB 修复**：DUMPOUT/UNDUMP 宏 32 位 int 移位 ≤56 位 → 显式 u_int64_t（dump 格式不变）
- **杂项**：regexec eflags 传 0（musl/clang15 硬错误）、REG_NOSPEC 元字符转义模拟、`-M corefile` 在 procfs 后端如实报 EX_UNAVAILABLE（kvm 特性）
- **构建系统**：BSD make → GNU make；man 页 raw 安装 man1/ + `.so` 伴生页 share/man/proctools/（groff 相对路径可解析，不依赖 soelim）

## 已知限制

- `pfind -result`/`-wait` 需 ptrace attach，OHOS 沙箱禁 ptrace 时工具如实报错（gdb 同样受限）
- `pgrep -v` 语义为上游原样（仅反转 uid/gid 列表匹配，不反转 pattern 匹配）
- 上游按设计不匹配自身进程
