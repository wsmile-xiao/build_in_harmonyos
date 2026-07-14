# connect 1.106 适配笔记

## 编译环境
- 构建系统: makefile（裸 Makefile，无 configure，无 install 目标）
- 编译日期: 2026-07-11
- 编译器: clang（由 Conan profile `ohos-aarch64` 的 `tools.build:compiler_executables` 注入）
- 状态: built（配方与测试用例完成，编译与测试由 CI 在真实鸿蒙 worker 上执行；尚未 upload）

## 上游情况

源码包只有 4 个有效文件：`connect.c`（约 3000 行）、`Makefile`、`README.md`、`doc/`。
整个程序是单文件 C，依赖仅 libc。上游 **没有任何测试**：Makefile 只有
`all` / `clean` / `veryclean` / `rebuild` 目标，没有 `check`/`test`，也没有测试源码或测试脚本。

## 编译步骤

上游 Makefile 按 `uname -s` 分支：Darwin 追加 `-lresolv`，SunOS 追加 `-lresolv -lsocket -lnsl`，
Windows 追加 `-lws2_32 -liphlpapi`，其余（含鸿蒙，`uname -s` 返回 Linux）走通用 UNIX 分支
（`CC=gcc`、`CFLAGS=-DSOCKLEN_T=unsigned`、`LDLIBS` 为空）。因此**无需补丁即可编译**，
只需在 make 命令行覆盖三个变量：

```bash
make CC="<conan profile 中的 clang>" \
     CFLAGS="-O2 -fPIE -D_GNU_SOURCE -DSOCKLEN_T=socklen_t" \
     LDFLAGS="-pie -Wl,-z,relro,-z,now" \
     LDLIBS="" -j1
```

Makefile 无 `install` 目标，`package()` 手动把 `connect` 拷到 `bin/`，README.md 拷到 `licenses/`
（上游没有单独的 LICENSE 文件，GPL-2.0-or-later 声明位于 connect.c 头部）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Makefile 硬编码 `CC=gcc`，鸿蒙 worker 上无 gcc | 上游 2012 年的 Makefile 未考虑 clang 工具链 | 在 `build()` 中从 `self.conf.get("tools.build:compiler_executables")` 取 c 编译器并在 make 命令行覆盖 `CC`（R33，禁止裸用 `${CC}`） |
| 2 | 面向 Solaris/macOS 的 `-lresolv -lsocket -lnsl` 在鸿蒙上会链接失败 | musl 已把 resolver、socket 并入 libc，无独立 .so | make 命令行显式置 `LDLIBS=""`（知识库 musl-glibc-developer-impact.md §1.4.2） |
| 3 | 上游 `CFLAGS=-DSOCKLEN_T=unsigned` 语义不正确 | 该宏是历史遗留，1.106 的 connect.c 里已无任何引用点 | 改为 `-DSOCKLEN_T=socklen_t` 保持类型正确（实际不影响编译产物） |
| 4 | CI L2 冒烟门禁用 `--version`/`--help` 探测 | connect 只支持短选项 `-V`，长选项会报 unknown option 并退出 1 | L2 为非阻塞（warn）。版本验证改由 test_package 执行 `connect -V` 并断言输出含 `Version 1.106` |
| 5 | CI 构建 #1162 编译失败：`connect.c:1814: error: use of undeclared identifier '_res'` | `switch_ns()` 用 glibc 的 `_res` 全局解析器状态实现 `-R <nameserver-ip>`；OHOS 的 musl 提供了 `res_init()` 但没有 `_res` 结构 | 见下节：`patches/0001-connect.c.patch`，在 musl 上直接向指定 nameserver 发 UDP DNS 查询 |
| 6 | CI 构建 #1169 运行时失败：`FATAL: getpwuid() failed for uid: 20020101`，connect 启动即退出 | 鸿蒙的 uid 不在 `/etc/passwd` 中，musl 的 `getpwuid()` 返回 NULL；上游在两处把这当致命错误：`read_parameter_file()`（每次调用都执行，用于找 `~/.connectrc`）与 `getusername()`（代理用户名）。**这不是测试问题——在鸿蒙上 connect 对任何参数都会启动即 abort，工具完全不可用** | `patches/0002-connect.c.patch`：`getpwuid()` 失败时不再 abort，回退到 `$USER`/`$LOGNAME`，再不行用 uid 数字串；`~/.connectrc` 改从 `$HOME` 找，没有家目录就跳过（该配置文件本就是可选的） |

## 源码修改

两个补丁，均为 `portability` 类型，都只在 musl/OHOS 分支生效，glibc 分支保持上游原样。

### 0001-connect.c.patch — 为 musl/OHOS 移植 `-R <nameserver-ip>`

上游 `switch_ns()` 把用户指定的 nameserver 写进 glibc 的 `_res` 全局解析器状态，后续 `gethostbyname()`
便会向该 nameserver 发查询：

```c
res_init();
memcpy(&_res.nsaddr_list[0], ns, sizeof(*ns));
_res.nscount = 1;
```

musl（含鸿蒙 libc）声明了 `res_init()`，但**没有 `_res` 这个结构**，其解析器只读 `/etc/resolv.conf`，
所以这段代码在鸿蒙上直接编译失败（CI #1162）。

**修法**：不采用 `#ifdef` 把 `-R` 空掉的绕过式 stub（那会让功能静默失效，违反 R8 / 审查规则 #5），
而是在 musl 分支上真正实现该功能——`switch_ns()` 记下指定的 nameserver，
`local_resolve()` 在解析主机名时直接向它发 UDP DNS A 记录查询并解析应答（新增
`dns_encode_name()` / `dns_skip_name()` / `ns_resolve()`，支持 CNAME 跳过与压缩指针）：

```c
#if defined(__OHOS__) || (defined(__linux__) && !defined(__GLIBC__))
#define WITHOUT_RES_STATE 1
#endif
```

平台判定同时覆盖 `__OHOS__` 与「Linux 且非 glibc」（即 musl），glibc 分支保持上游原样，
两个分支都验证过可编译（见下）。上游的调用点与调用顺序完全未改动，语义与 glibc 上一致。

### 0002-connect.c.patch — `getpwuid()` 失败不再 abort

鸿蒙的账号不在 `/etc/passwd` 里，`getpwuid(getuid())` 返回 NULL。上游有两处把这当致命错误直接退出：

- `read_parameter_file()`：为找 `~/.connectrc` 而取家目录，**每次调用都会执行**（在 `set_relay()` 内）；
- `getusername()`：取 SOCKS/HTTP 代理用户名。

结果是 connect 在鸿蒙上**对任何参数都启动即 abort**（CI #1169：`FATAL: getpwuid() failed for uid: 20020101`），
工具完全不可用。这不是测试环境问题，是真实的适配缺陷。

修法（不 abort，走有实质逻辑的兜底，而非 stub 掉功能）：
- `getusername()`：`getpwuid()` 失败 → `$USER` → `$LOGNAME` → 最后用 uid 的数字串。
  该名字只用作代理用户名，任何非空字符串都能满足 SOCKS4/5 与 HTTP 代理的协议要求；
- `read_parameter_file()`：家目录改从 `$HOME` 取；若确实没有家目录，就跳过 `~/.connectrc`
  （这个 per-user 配置文件本就是可选的，`/etc/connectrc` 仍照常读取）。

兜底路径只在上游原本会 abort 的场景下才会走到，glibc 上正常有 passwd 条目时行为与上游完全一致。

## 依赖版本

无第三方依赖（仅 libc）。

## 验证结果

上游无测试套件，测试全部由 test_package 承担。`test_package/test_connect.c` 不是 `--version` 空壳
冒烟测试：它在进程内起 TCP 监听端口，`fork`/`execv` 拉起被测的 `connect` 二进制并接管其 stdin/stdout，
再按协议扮演对端，实测三条中继链路（R34）：

| # | 用例 | 断言 |
|---|------|------|
| 1 | `connect -V` | 输出包含 `Version 1.106` |
| 2 | `connect -n 127.0.0.1 <port>` | 直连模式下 stdio ↔ socket 双向中继：写入 PING，对端收到 PING 并回 PONG，stdout 读回 PONG |
| 3 | `connect -H 127.0.0.1:<port> example.invalid 12345` | 进程内 HTTP 代理断言收到 `CONNECT example.invalid:12345 HTTP/1.0`；回 `200 Connection established` 后校验数据中继 |
| 4 | `connect -5 -R remote -S 127.0.0.1:<port> example.invalid 12345` | 进程内 SOCKS5 服务端断言方法协商（VER=5）与 CONNECT 请求（CMD=1、ATYP=3 域名远端解析、host/port 正确）；回成功应答后校验数据中继 |

共 6 条断言（`check()` 调用数）。

### 补丁的验证（0001-connect.c.patch）

`-R <nameserver-ip>` 走的是 UDP 53 端口，CI worker 上无特权无法 bind 53，
因此这条路径**无法**放进 test_package（不能在鸿蒙 CI 上跑）。为避免向 CI 交付未经验证的 DNS
报文解析代码，本地做了针对性验证（macOS/clang，用 `-DWITHOUT_RES_STATE=1` 强制打开 musl 分支）：
把打完补丁的 `connect.c` 以 `-Dmain=...` 改名后与一个测试 main 链接（即**直接测被测源码本身**，
不是复制一份），起一个进程内 DNS 服务端（应答里使用压缩指针，覆盖 `dns_skip_name()` 的 0xC0 分支），
调用 `switch_ns()` + `local_resolve()`：

```
DEBUG: Using nameserver at 127.0.0.1
DEBUG: resolving host by name: dns-test.invalid
DEBUG: resolved: dns-test.invalid (93.184.216.34) by the specified nameserver
PASS: local_resolve("dns-test.invalid") -> 93.184.216.34 via the nameserver given to switch_ns()
```

补丁两个分支均验证可编译且无新增告警：
- glibc 分支（默认）：`cc -Wall -Wextra` 通过，行为与上游一致；
- musl 分支（`-DWITHOUT_RES_STATE=1`）：`cc -Wall -Wextra` 通过；唯一的 `unused parameter 'sig'`
  告警在**未打补丁的上游源码里同样存在**，非本补丁引入。

用 musl 分支编译出的二进制重跑上述 4 条用例 6 条断言，全部通过（无回归）。

### 0002 补丁的验证（getpwuid 兜底）

CI worker 的 uid（20020101）无 passwd 条目，本机无法直接复现。用桩函数强制 `getpwuid()` 返回 NULL
（`-Dgetpwuid=fake_getpwuid`，即 CI 上的真实条件），并清空 `USER`/`LOGNAME`/`HOME` 环境变量以逼出最深一层
（uid 数字串）兜底，做修复前后对比：

```
# 打 0002 之前 —— 与 CI #1169 完全相同的失败签名
PASS: connect -V reports "Version 1.106"
FATAL: getpwuid() failed for uid: 501
FAIL: direct relay (connect never connected)   [connect exited with status 1]

# 打 0002 之后 —— 即使 USER/LOGNAME/HOME 全都不存在
All tests passed   (6/6)
```

### test_package 用例实测

本地（macOS/clang，用于验证测试逻辑本身）实测：

```
$ cc -O2 -Wall -Wextra -o test_connect test_connect.c   # 零 warning
$ ./test_connect ./connect
PASS: connect -V reports "Version 1.106"
PASS: connect -n relays stdio <-> TCP (direct mode)
PASS: connect -H sends a well-formed HTTP CONNECT request
PASS: connect -H relays payload after the tunnel is established
PASS: connect -5 sends a SOCKS5 CONNECT request with remote name resolution
PASS: connect -5 relays payload after the SOCKS5 handshake
All tests passed   # exit 0

$ ./test_connect /path/that/does/not/exist   # 模拟 CI L1e 破坏性反向验证
exit 1                                       # 产物缺失时测试确实失败，非假测试
```

鸿蒙 aarch64 上的实际编译与测试由 CI（Buildbot 真实鸿蒙 worker）执行 `conan create` 完成，
本地不具备鸿蒙构建环境。

## 注意事项

- 本包只产出可执行文件，无库产物：`cpp_info.libs = []`、`cpp_info.bindirs = ["bin"]`，
  并按 R38 在软件级目录提供 `commands.json`。
- 测试用例使用 `example.invalid`（RFC 2606 保留域名）作为目的主机，且始终由进程内的代理服务端
  应答，全程不产生任何外部网络访问与 DNS 查询，可在离线 CI worker 上稳定运行。
- 测试进程设置了 60 秒 `alarm()` 超时保护，避免握手异常时挂死 CI worker。
- CI #1169 暴露出测试本身的一个诊断缺陷：被测二进制启动即退出时，测试会阻塞在 `accept()` 上直到 alarm
  触发，把真实死因（`FATAL: getpwuid()`）掩盖成一句"timed out"。已改为用 `poll()` 给 `accept()` 加 15 秒
  上限（`accept()` 并非在所有平台都遵守 `SO_RCVTIMEO`），并在失败时 `waitpid` 回报子进程退出码，
  现在同样的故障会直接打印 `[connect exited with status 1]`。
