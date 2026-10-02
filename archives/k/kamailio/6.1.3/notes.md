# kamailio 6.1.3 适配笔记

## 1. 软件形态

- SIP 服务器。core 交付物 = `src/kamailio` 单二进制（11.5MB，ELF 64-bit PIE，Type DYN + PIE + BIND_NOW 全 RELRO，`NEEDED` 仅 `libc.so`——musl 下 pthread/m/dl 已并入 libc）。
- **无独立 libkamailio.so/.a**：core 目标代码直接链入主二进制；二进制按 shared object 构建以便运行时 dlopen 模块。
- **srved 不存在**：6.1.3 全树 grep 零命中（上游早已移除），smoke 不涉及。
- 构建系统：经典 Makefile（`make cfg` → `make`）。工具链 clang 15.0.4（OHOS SDK native）。
- 无外部 conan 依赖：pcre2 仅被 modules（regex/dialplan/cnxcc/lcr）引用，core 不引用；core 外部面 = musl libc 内置。

## 2. W0b 核验：Makefile.defs 6.1.3 vs 6.0.6（路径B 核心素材）

6.1.3 平台分支（L1853-1908 linux / solaris / freebsd / darwin / gnu_kfreebsd）**仍无 harmonyos 分支**，与 6.0.6 一致（E429 结论跨版本成立）。`OS=harmonyos` 落入无分支，linux 分支的宏与锁机制必须经 `extra_defs` 手动注入。

| linux 分支宏 | 6.0.6 模块口径 | 6.1.3 core 处理 | 依据 |
|---|---|---|---|
| `_GNU_SOURCE` `HAVE_GETHOSTBYNAME2` `HAVE_SCHED_YIELD` `HAVE_MSG_NOSIGNAL` `HAVE_MSGHDR_MSG_CONTROL` `HAVE_ALLOCA_H` `HAVE_TIMEGM` `HAVE_SCHED_SETSCHEDULER` `HAVE_IP_MREQN`（9 宏） | E429 已注入 | 同 6.0.6，直接复用 | core 头 resolve.h/sched_yield.h 等 #error 前置检查 |
| `HAVE_UNION_SEMUN` | 不注入 | **不注入** | musl sem.h 不导出 union semun；注入反致冲突（E429 已验证） |
| `USE_PTHREAD_MUTEX`（锁机制） | 不需要（modules 不触达锁检查） | **必须注入（core delta 1）** | lock_ops.h L298 `#error "no locking method selected"`；linux 分支默认给 USE_PTHREAD_MUTEX |
| `HAVE_EPOLL`（条件 ≥2.5.44） | 不需要（modules 无 tcpio） | **注入（已实证）** | 不注入则 `-v` 仅 "poll method support: poll."；注入后 "poll, epoll_lt, epoll_et."，与 linux 构建对齐；musl epoll 路径编译通过 |
| `HAVE_SIGIO_RT` + `SIGINFO64_WORKAROUND`（条件 ≥2.2.0） | 不需要 | 不注入（最小参数原则） | sigio 路径 musl 支持度未验证，poll/epoll 事件循环已完备，不引入未验证面 |
| `USE_FUTEX`（条件 ≥2.5.70） | 不需要 | 不注入（最小参数原则） | glibc 特化快锁优化，FAST_LOCK-ADAPTIVE_WAIT + USE_PTHREAD_MUTEX 已覆盖 |
| `HAVE_SELECT`（条件，NO_SELECT 空） | 不需要 | 不注入 | 回退路径默认启用，compilable |

### core delta 2：`_res` 全局（musl 缺失）

- `-DHAVE_RESOLV_RES` 在 Makefile.defs L729 **无条件**进 C_DEFS（非平台分支）。
- OHOS sysroot resolv.h（musl）：有 `struct __res_state` 类型，**不导出 `_res` 全局** → core/resolve.c 6 处报错（L190/192/194/195/197 调整 retrans/retry/nscount/options；L926 `match_search_list(&_res,…)`）。
- **修复 = 纯构建配置，零源码改动、零补丁（R8）**：`env DEFS=-UHAVE_RESOLV_RES make …`。
  - 机制：Makefile.rules L46 编译行 `… $(C_DEFS) $(DEFS) -c`，`$(DEFS)` 在 C_DEFS 之后，后置 `-U` 胜出（已实验验证 -D 后 -U 生效）。
  - **为何不用命令行 `DEFS=…`**：make 命令行变量锁定 in-file 赋值，会吞掉目标特定定义 `main.o: DEFS+=-DMODS_DIR=…`（src/Makefile L276）→ main.c 报 MODS_DIR 未声明（实测复现）。环境变量 DEFS 可被 in-file `+=` 追加，main.o 同时获得 -U 与 MODS_DIR（实测通过）。
  - **为何不用 extra_defs**：extra_defs 在 L711 前置进 C_DEFS，早于 L729 的 `-DHAVE_RESOLV_RES`，-U 被 -D 覆盖。
  - 语义：守卫变假后走上游自带 `#else` 回退（L198-201 "no resolv options support" 警告分支）；L924 块跳过后 `fullname_rd = rd` 恒执行（DNS 缓存启发式回退，glibc 行为不变）。
- 6.0.6 模块族无此问题：`make modules` 不编译 core/resolve.c（模块不链接 libkamailio，NEEDED 仅 libc.so）——**core 构建首次触达**。

## 3. R51 上游测试清点

- 官方 `_src` tarball 顶层无 `tests/` 目录、`src/Makefile` 无 `check` 目标（与 6.0.6 先例一致）。
- 上游 CI 走 `pkg/kamailio` Smoketest（需运行中 SIP 场景，CI clean 环境不可行）。
- 申报口径（与 6.0.6 模块族一致）：上游无自动化套件（附本清点证据）+ test_package 结构/功能断言 + `kamailio -v` 冒烟。

## 4. 构建事实与实测

- 完整 clean 构建（`make cfg` + `make -j4`）：约 7 分钟（21:04→21:11，本机）；conan create 默认 3600s 预算内，无需 timeout 覆盖。
- smoke：`kamailio -v` → `version: kamailio 6.1.3 (aarch64/harmonyos) dc4570`，flags 含 `USE_PTHREAD_MUTEX`、`TLS_PTHREAD_MUTEX_SHARED`、`poll method support: poll, epoll_lt, epoll_et.`。
- 非阻塞警告：fastlock.h "arm* smp mode not supported (no membars), try -DNOSMP"（#warning；与 6.0.6 族一致未加 NOSMP，kamailio 为 fork 多进程模型非线程模型）。
- 未注入 `HAVE_UNION_SEMUN`/`USE_FUTEX`/`SIGIO_RT`：最小参数原则，回退路径完备（见 §2 表）。

## 5. 可复现构建命令

```sh
# 前置：CC=clang CXX=clang++（Conan toolchain 注入；make 经 ${CC} 环境变量读取，Makefile.defs L255）
DEFS_INJ='-D_GNU_SOURCE -DHAVE_GETHOSTBYNAME2 -DHAVE_SCHED_YIELD -DHAVE_MSG_NOSIGNAL -DHAVE_MSGHDR_MSG_CONTROL -DHAVE_ALLOCA_H -DHAVE_TIMEGM -DHAVE_SCHED_SETSCHEDULER -DHAVE_IP_MREQN -DUSE_PTHREAD_MUTEX -DHAVE_EPOLL'
make cfg extra_defs="$DEFS_INJ"
env DEFS=-UHAVE_RESOLV_RES make -j4 extra_defs="$DEFS_INJ"
# 产物：src/kamailio（无其他交付物；无 modules 时 modules_search_path 为空）
```
---

**编译结束**: 2026-09-29 22:37
**最终状态**: built
