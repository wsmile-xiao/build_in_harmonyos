# isc-kea 3.0.3 适配笔记

## 编译环境
- 构建系统: meson（Kea 3.0 起由 Autotools 迁移；顶层 `meson.build`，`meson_version: '>=1.1.0'`）
- 编译日期: 2026-10-08（首次适配）
- 编译器: clang/clang++ 15.0.4（OHOS SDK 26，aarch64-linux-ohos，libc++，C++17）
- 工作副本: `~/huawei/worktrees/2404_87638649/isc-kea-3.0.3`（分支 `feat/isc-kea-3.0.3`）
- 状态: built

## 本件定位（与同族包的分工）

ISC Kea 3.0.3 是单 Meson 工程，本仓已按目标拆分适配：

| 包 | 范围 |
|---|---|
| **isc-kea（本件）** | 五个服务器/工具守护进程（kea-dhcp4/kea-dhcp6/kea-dhcp-ddns/kea-ctrl-agent/kea-lfc）+ keactrl + 23 个核心 libkea-* 库 + include/kea 公共头 |
| kea-hooks | hooks（callout）框架库 libkea-hooks |
| kea-hook-{radius,lease-cmds,lease-query,limits,perfmon,ping-check,stat-cmds,pgsql,ha,...} | src/hooks/* 用户 hook 插件 |
| kea-perfdhcp | perfdhcp DHCP 性能测试客户端 |
| kea-shell | kea-shell 管理脚本（python） |

配置口径：mysql/postgresql/netconf/krb5 均 disabled（制品仓无对应依赖包；netconf 禁用连带
src/lib/yang 不构建——kea-yang 仅经 netconf 选项可达）。hook 插件不随本件构建（其目标属
src/hooks，在各自包内构建）。

## 编译步骤

```bash
# 1) 语言预检（R47）：cpp / meson 工程
ohc-run.py lang-preflight isc-kea 3.0.3 --src <上游源码树>

# 2) Conan 生成 Meson 工具链（PkgConfigDeps + MesonToolchain）
conan install . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 -of=<of>

# 3) 配方固化构建（ninja 按 output path 编译五守护进程 + 29 个上游测试可执行 + fixture）
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64

# 4) 门禁
ohc-run.py conan-verify isc-kea 3.0.3
ohc-run.py finish isc-kea 3.0.3 built
```

## 上游测试（实测执行）

上游 Meson 注册 46 个 test() 套件（`meson test --list` 实测）。本件范围：

- **24 个 lib 套件 + 5 个 bin 服务器套件 = 29 套件**：kea-{asiodns,asiolink,cc,config-backend,
  config,cryptolink,d2srv,database,dhcp-ddns,dhcp,dhcpsrv,dns,eval,exceptions,hooks,http,
  log-init,log-interprocess,log,process-cfgrpt,process,stats,tcp,util,agent,d2,dhcp4,dhcp6,lfc}-tests
- 排除：15 个 src/hooks 套件（属 kea-hook-* 包）、perfdhcp-tests（属 kea-perfdhcp）、
  kea-{mysql,pgsql}-tests（后端禁用）、kea-netconf/kea-sysrepo-setup-tests（netconf 禁用）、
  shell 集成套件（*_process_tests.sh/memfile/keactrl_tests.sh 等——驱动守护进程开真实
  socket，包 CI 环境不可提供，环境限制）

fixture 依赖（上游 depends: 声明实测）：dhcp4/dhcp6 各 co1-co4、dhcpsrv co1-co3、
hooks nvl/ivl/fxl/bcl/lcl/lecl/ucl/fcl/pcl/acl、agent callout/basicauth、d2 callout/configured
——ninja 以 output path 一并编译后 `meson test --no-rebuild` 运行。

**测试统计（--gtest_list_tests 实测口径）**：

| 项 | 数 |
|---|---|
| 上游注册用例（29 套件） | 7321 |
| 上游自带 DISABLED_（gtest 不注册执行） | 27 |
| 应执行 | 7294 |
| OHOS 环境限制排除（GTEST_FILTER） | 168 |
| 实际执行并全部通过 | **7126（0 失败）** |

**OHOS 环境限制用例根因（六类，全部实测验证）**：

| # | 根因 | 排除范围 | 数量 |
|---|------|----------|------|
| 1 | 路径式 AF_UNIX socket 在 OHOS 上对非特权进程全面禁止（tmpfs=EPERM、hmfs=EACCES，实测 bind() 全拒；抽象命名空间可用但 Kea 硬编码路径式）；夹具 Sandbox `mkdtemp(P_tmpdir=/tmp)` 在只读 /tmp 返回 NULL → `std::string(NULL)` → musl 加载器 strlen(0) SIGSEGV（SIGSEGV 探针实测：addr=0、PC=strlen+0x10） | ClientConnectionTest / UnixCommandMgrTest / UnixDomainSocketTest / CtrlChannel{Dhcpv4,Dhcpv6,D2}Test / CtrlAgentCommandMgrTest | 153 |
| 2 | 只读 /tmp：MemfileLeaseMgr dataDir* 在 /tmp 开租约 CSV 失败（报错定位 `unable to open '/tmp/leasefile6_1.csv'`） | MemfileLeaseMgrTest.dataDir{EnvVar,Explicit}Override | 2 |
| 3 | conan 深构建目录超 sockaddr_un::sun_path 107 字符上限（报错定位 `Filename too long [system:36]`），经控制 socket 写配置的用例同因（响应非 map：`get(string) called on a non-map Element`） | Dhcp{4,6}ParserTest.comments、Dhcp{4,6}GetConfigTest.run/{69,65}、Http(s)CtrlChannel{Dhcpv4,Dhcpv6,D2}Test.configWriteFullPath | 10 |
| 4 | OHOS death-test 语义：子进程死亡消息不回传父进程控制台（报错定位 `Result: failed to die`） | FormatterTest.mismatchedPlaceholders | 1 |
| 5 | OHOS chmod(S_IRUSR) 不阻止属主写（open(O_WRONLY) 仍成功，`it throws nothing`） | PIDFileTest.pidWriteFail | 1 |
| 6 | 虚拟接口清单差异：ip6_vti0/ip6tnl0 无匹配地址（报错定位 `Non-matching addresses on the detected interface ip6_vti0`） | IfaceMgrTest.detectIfaces | 1 |
| | **排除合计**（153+2+10+1+1+1） | | **168** |

> 168 = 应执行 7294 - 实际通过 7126（实测对账闭合）。根因 1 计 153：七个 fixture 共 154 个
> 注册用例，其中 CtrlAgentCommandMgrTest.DISABLED_connectionTimeout 为上游自带 DISABLED_
> （不在 gtest 执行集，不重复计入）。

排除方式：`GTEST_FILTER` 环境变量（meson test 透传父环境给每个测试进程——testlog.txt
"Inherited environment" 段实测确认），配方 build() 内以 `Environment().define()` 注入，
仅 `settings.os == "OHOS"` 时生效，非 OHOS 平台全量执行。

## 遇到的问题与解决方案

与 kea-hooks / kea-perfdhcp / kea-hook-* 同源（同一 tarball、同一 Meson 工程），四个已知
平台差异全部复用同族已合入方案：

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `meson.build:17:0: ERROR: Unknown linker(s): [['llvm-ar']]`（configure 阶段，首个错误） | meson 对 clang 默认用裸名 `llvm-ar` 探测静态链接器，本环境/CI worker 上裸名 exec 失败 | `generate()` 从 `conf tools.build:compiler_executables` 的 c 编译器路径推导同目录 `llvm-ar`/`llvm-ranlib` 写入 `tc.binaries` |
| 2 | `meson.build: ERROR: Problem encountered: Unsupported system "harmonyos".` | Kea 用 `build_machine.system()` 做平台白名单分支，不含 OHOS | 补丁 `0001-meson.build.patch`：顶层归一化 `harmonyos -> linux`，全树走 Linux 分支 |
| 3 | `meson.build: ERROR: Boost TLS support broken.`（`sp_thread_sleep.hpp: pthread_setcancelstate undeclared`） | OHOS musl pthread.h 不声明 `pthread_setcancelstate()`，boost 无条件调用 | `generate()` 注入 `-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE` |
| 4 | 配置期探针 `Checking ... runs: NO (127)`（log4cplus/openssl/boost） | meson 特性探针是"编译并运行"，host 共享依赖不在配置期 LD_LIBRARY_PATH | `generate()` 用 `Environment` 把各依赖 libdirs 追加进 `LD_LIBRARY_PATH` 并 save_script |
| 5 | 编译期 `iface_mgr_linux.cc: redefinition of 'sockaddr_storage'` | OHOS sysroot 的 bionic 派生 `linux/socket.h` 与 musl `sys/socket.h` 都定义该结构体 | 补丁 `0002-src-lib-dhcp-iface_mgr_linux.cc.patch`：包含 netlink 头前后 define/undef 守卫（`__linux__ && !__GLIBC__`） |

## 守护进程形态说明（daemon runtime）

kea-dhcp4/kea-dhcp6/kea-dhcp-ddns/kea-ctrl-agent/kea-lfc 是服务器守护进程：真实流量验证
需要绑定网络接口、开 socket、加载 hook 库等，包 CI 环境不可提供（环境限制）。验证口径：
- 上游 gtest 套件覆盖服务器本体逻辑（kea-dhcp4-tests 等直接测 Dhcpv4Srv 类行为）
- test_package 消费者侧：五守护进程 `--version` 实跑（证明可执行文件 + libkea-* 闭包在目标
  环境加载执行）+ API 链接断言 + OHOS 平台 ABI/dlopen 检查
