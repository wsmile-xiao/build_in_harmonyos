# E556 — inetd 风格 spawner 的 socket→stdin/stdout 契约验证与三段式进程清理

## 问题概述

inetd 风格程序（micro_inetd 类 spawner）在 OHOS PC 目标环境没有 systemd/inetd 挂载点，也没有特权端口权限。`--help`/`--version` 冒烟只证明二进制能执行，不能证明「连接 socket 被 dup2 到子进程 stdin/stdout/stderr 后 execv 服务程序」这一核心契约。测试自己 fork spawner 后，若只 kill 不 waitpid，会留下孤儿/僵尸或占端口的残留进程。端口选择上，`<1024` 绑不了，硬编码高位端口在并行 CI 下会冲突。

解决思路是**真实 socket 契约测试 + 三段式进程清理**：test_package 自带两个极小服务 fixture（svc_cat 字节中继、svc_exit42 固定退出码），C 驱动 fork+execl **已安装**的 spawner（package_folder/bin），6 个用例覆盖契约的每个维度；端口用 bind(0)+getsockname 探测空闲临时端口；进程清理走 SIGTERM→waitpid(WNOHANG) 轮询→SIGKILL 兜底三段式，并以负向验证（移走 bin/ 后测试必须全 FAIL）证明测的是安装产物。

## 典型错误

```
# 冒烟测试的假象：--help 能跑 ≠ 契约成立
$ micro_inetd --help
usage: micro_inetd <port> <prog> [args...]     # 冒烟通过，但核心契约未验证

# 只 kill 不 waitpid 的残留
$ ps aux | grep micro_inetd
root  12345  ...  [micro_inetd <defunct>]      # 僵尸进程残留

# 硬编码端口在并行 CI 下冲突
bind: Address already in use
```

触发条件：
- 构建系统: 任意（本例纯 Makefile）
- 阶段: testing（conan test_package）、runtime（进程生命周期）

## 根因

1. spawner 本体不实现应用协议——它的全部职责就是 `listen → accept → fork → dup2(0/1/2, socket) → execv(prog)`。
2. 上游 `execv` 失败路径 `perror()` 写到**已 dup2 为连接 socket 的 stderr** 上，错误文本沿连接回传客户端（真实 inetd 语义）；初版测试断「立即 EOF」实测 FAIL，是断言设计想当然，不是程序 bug。
3. 无系统服务管理器的环境里，进程生命周期必须由测试驱动完全接管：启动（fork+exec）→ 健康确认（探测连接成功）→ 停止（SIGTERM→waitpid→SIGKILL 兜底）。
4. 端口选择：`<1024` 绑不了（无 root），硬编码高位端口在并行 CI 下会冲突；唯一可靠方案是内核分配的临时端口。

## 适用范围

- inetd 风格 spawner（accept+fork+dup2+exec 模式）在无 systemd/inetd、无特权端口环境下的 test_package 设计。
- 要求被测程序支持 `<port> <prog> [args]` 形式的命令行（micro_inetd 即此形态）。
- 无第三方依赖的单文件网络工具（仅 libc）。

## 不适用范围

- 程序自身实现应用协议（直接对协议断言即可）。
- 需要 Unix domain socket 的程序（见 E461 文件系统矩阵条目）。
- 程序自身有守护进程化行为（daemonize）的程序。

## 检测流程

1. **确认 spawner 形态**：读上游源码，确认 listen→accept→fork→dup2→execv 模式与命令行形态 `<port> <prog> [args]`。
2. **确认环境限制**：目标环境无 systemd/inetd，无特权端口（<1024），无 root。
3. **确认依赖面**：readelf 确认仅 libc 依赖，无系统同名库风险。

## 修复流程（通用算法）

1. **测试形态**：test_package 自带两个极小服务 fixture：`svc_cat`（stdin→stdout 字节中继）、`svc_exit42`（固定退出 42）。C 驱动 fork+execl **已安装**的 spawner（`package_folder/bin`，不测构建树副本）。每个用例独立端口 + 独立 spawner 生命周期，失败路径同样走清理。
2. **端口策略（无特权、无冲突）**：`bind(port=0) → getsockname() 取回临时端口 → close`。探测后释放到 spawner bind 前有竞争窗口，但 spawner bind 失败会立刻退出，被 `bring_up` 轮询中的 `waitpid(WNOHANG)` 发现 → 测试快速失败而非悬挂。探测连接成功同时充当「listener 就绪」信号（~50ms 间隔，上限 ~2s）。
3. **契约断言集（6 用例）**：

   | 用例 | 验证点 |
   |---|---|
   | T1 | 请求/响应字节级中继（stdin+stdout 均接 socket，多长度报文） |
   | T2 | 服务退出码→连接 EOF；spawner 存活续接 3 轮 |
   | T3 | 4 路并发连接交错读写，会话独立 |
   | T4 | 5 轮重复新鲜连接（nowait 语义） |
   | T5 | 无效命令→execv 错误文本经 socket 回传 + EOF + spawner 存活 |
   | T6 | 无参数→stderr usage + exit 1 |

4. **三段式进程清理**：`SIGTERM → ≤40×50ms waitpid(WNOHANG) 轮询 → SIGKILL + 阻塞 waitpid 兜底`。禁用无条件 `pkill`/`killall`（误伤环境同名进程）；PID 由 fork 直接持有，不存在复用歧义。测试后 `ps` 扫描断言无 spawner/fixture 残留、无监听端口残留。
5. **负向验证（证明测的是安装产物）**：临时移走包内 `bin/` → `conan test` 必须 6 用例全 FAIL → 恢复后包完好。

## 验证流程

- **契约执行证据**：T1–T6 全部 PASS（6/6），EXIT 0。
- **负向验证**：移走 bin/ 后全 FAIL，恢复后完好。
- **残留检查**：`ps` 无 micro_inetd/svc_cat/svc_exit42；无测试监听端口。
- **产物形态**：ELF64 AArch64 PIE，musl interpreter `/lib/ld-musl-aarch64.so.1`，仅 libc.so 依赖。
- **上游三源核验**：sha256 一致：acme.com（HTTP 200, Last-Modified 2014-8-14）+ FreeBSD distfiles + Homebrew。
- **上游源码依据**：micro_inetd.c L111-114（execv 失败 perror 到 dup2 后的 stderr）。

## 禁止方案

- ❌ **只做 --help/--version 冒烟**：只证明二进制可执行，不证明核心契约。
- ❌ **无条件 pkill/killall**：误伤 CI 环境同名进程，测试间互相干扰。
- ❌ **绑定特权端口**：无 root 环境 EPERM 悬挂。
- ❌ **硬编码高位端口**：并行 CI 下冲突。
- ❌ **测构建树副本**：package() 阶段缺陷逃逸。
- ❌ **只 kill 不 waitpid**：留孤儿/僵尸与端口占用。

## micro_inetd 真实案例

micro_inetd 2014-8-14（ACME Labs，BSD-2-Clause）适配：

- **测试驱动**：`archives/m/micro_inetd/2014-8-14/test_package/test_micro_inetd.c`（453+ 行，6 用例 + bring_up/stop_spawner 生命周期管理）。
- **服务 fixture**：同目录 svc_cat.c / svc_exit42.c。
- **上游源码依据**：micro_inetd.c L111-114（execv 失败 perror 到 dup2 后的 stderr）。
- **结果**：T1–T6 全部 PASS（6/6），EXIT 0；负向验证通过（移走 bin/ 后全 FAIL）；残留检查通过（ps 无残留进程/端口）。
- **上游核验**：acme.com 原站 HTTP 200（Last-Modified 2014-08-14）+ FreeBSD distfiles + Homebrew 三源 sha256 一致 15f5558753bb50ed18e4a1445b3e8a185f3b1840ec8e017a5e6fc7690616ec52。

## 与相似条目的区别

- **E361（MPI detached-descendant canary）**：讲“超时验收后仍需后代哨兵”，对象是托管 MPI launcher 的超时契约，非 inetd spawner 的 socket 契约。
- **E461（AF_UNIX bind 文件系统矩阵）**：讲 AF_UNIX bind 的路径/权限矩阵，本方案用 TCP 临时端口恰好绕开该问题域。
- **E503（CLI 无 --version/--help）**：讲探测式冒烟的门禁失败，本方案正是其深化反面——不能止步于探测，要真跑 socket 契约。
- **E464/E403（残留清理）**：讲构建树/CMake 残留文件，非运行时进程清理。
- 其余 socket 类条目（E024/E048/E086/E233/E496）为 SELinux bind/UDPLITE/musl 结构体字段缺失、RDHUP/SO_PRIORITY 等内核与 libc 兼容性问题，无一条覆盖“spawner 契约验证+进程清理”问题域。

## 跨库复用方式

把“micro_inetd”替换为任意 inetd 风格 spawner：

1. 确认上游源码为 listen→accept→fork→dup2→execv 模式与 `<port> <prog> [args]` 命令行形态。
2. 在 test_package 写两个极小 fixture（字节中继 + 固定退出码服务）。
3. C 驱动 fork+execl 已安装 spawner，bind(0) 探测端口，按 T1–T6 断言集设计用例。
4. 三段式清理 + ps 残留扫描 + 负向验证。

## 关联条目
- 相似: E361（MPI 后代哨兵）、E461（AF_UNIX bind 矩阵）、E503（CLI 无 --help 冒烟）
