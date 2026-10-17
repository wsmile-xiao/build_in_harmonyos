# pen

pen 是一个独立部署的 **负载均衡器**（Author: Ulric Eriksson），对 **tcp 与 udp** 协议
（http、dns、smtp、任意长连接协议）做四层转发，让多台后端服务器对外表现得像一台。

## 功能概述

- **会话保持（session affinity）**：内部客户端表记录"客户端 → 上次访问的后端"，同一客户端
  的连接尽量回到同一台后端；表满时按 LRU 淘汰。相比纯轮询，避免破坏有状态的后端应用。
- **后端故障自动转移**：后端不可用时跳过它继续选下一台（可配 `blacklist` 冷却时间），
  配合 vrrp 可消除 pen 自身单点。
- **TCP 与 UDP 双模**：`-U` 打开 UDP 负载均衡（DNS、syslog 等）。
- **TLS 前端/后端**：`--with-ssl` 构建后可通过 `-e host[:port]` 把某个后端标记为 SSL
  端点，pen 负责 TLS 终止/发起（本包已启用，OpenSSL 静态链入）。
- **运行期控制面**：`-C port` 打开控制口，`penctl` 可在线查服务表、上下线后端、
  改权重等；`-w file` + `SIGUSR1` 导出 HTML 状态页。
- **日志聚合**：`penlog` → `penlogd` 把 pen 日志与各后端 web 日志合并，还原真实客户端 IP；
  `mergelogs` 用于事后离线合并。
- **访问控制**：`-a`/配置文件对控制口做 ACL。

包内的可执行文件：

| 命令 | 作用 |
|---|---|
| `pen` | 负载均衡器本体 |
| `penctl` | 控制口客户端（在线查询/管理后端） |
| `penlogd` | 日志聚合守护进程（接收 pen/后端日志 UDP 流） |
| `penlog` | 把后端 web 日志按 penlog 协议 UDP 发给 `penlogd` |
| `mergelogs` | 离线合并 pen 日志与 web 日志 |

## OHOS 适配

- **构建系统**：autotools。上游发布包自带预生成 `configure`/`Makefile.in`，
  因此不需要 autoreconf；但**不含 `config.guess`/`config.sub`**，构建时显式
  `--build=aarch64-linux-ohos` 跳过三元组猜测（与 `archives/n/ngircd/28` 同法）。
- **零源码补丁**：`patches/` 为空目录外的补丁数为 0 —— clang 15 + OHOS musl 下
  上游源码直接编译通过（仅有 9 条上游自身的编译告警：`pen.c` 1 条 unused variable，
  `ssl.c` 8 条 OpenSSL 3.0 deprecation / unused variable；详见
  `0.34.1/reports/w3-local-ci.log`）。
- **依赖**：仅 `openssl/3.5.8.1`（静态）。`--with-ssl` 命中后 `HAVE_LIBSSL` 生效，
  `ssl.c` 参与编译，最终 `pen` 静态链入 OpenSSL（`DT_NEEDED` 只有 `libc.so`）。
- **裁剪项**：`--without-geoip`（libgeoip 未适配/未发布）、`--without-dsr`
  （DSR 需要 netmap 的 `net/netmap_user.h`，OHOS 无对应实现）。二者都不影响代理模式。
- **与 Linux 的差异**：无。事件后端自动探测（OHOS 命中 `epoll_create1`/`poll`，
  `kqueue` 未命中属预期）。

## 依赖关系

| 类型 | 依赖 |
|---|---|
| 编译依赖 | `openssl/3.5.8.1`（ohpcd 制品仓，静态包） |
| 运行依赖 | 无（OpenSSL 已静态链入，`DT_NEEDED` 仅 `libc.so`） |

## 测试

- 上游**没有任何自动化测试**：无 `tests/` 目录、`Makefile.am`/`configure.ac` 未注册
  `TESTS`/`check_PROGRAMS`，`make check` 是 automake 的空目标（0 用例，见
  `0.34.1/reports/upstream-test-run.log`）。
- 因此新增 **4 条鸿蒙消费者用例**（非断言型，全部为真实数据面/控制面跑通）：
  UDP 数据面（penlog→pen→penlogd）、TCP 控制面（penctl）、TCP 数据面（双跳 pen 转发）、
  统计面（SIGUSR1 + `-w` HTML 状态页）。用例逻辑见
  `0.34.1/test_package/test.sh`，本机运行入口 `0.34.1/test_ohos/run_ohos_test.sh`。

## 参考资料

- 官网/源码：https://siag.nu/pen/
- 手册页：包内 `share/man/man1/{pen,penctl,penlog,penlogd,mergelogs}.1`
