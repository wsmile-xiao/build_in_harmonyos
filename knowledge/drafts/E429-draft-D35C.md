# E429 — kamailio（经典 Makefile）OHOS 交叉编译：OS=harmonyos 未被 Makefile.defs 识别 + 依赖探测回退 LOCALBASE + core 锁机制与 musl _res 缺失

> severity: 🟡 medium | category: build-system, platform, compat | 状态: 草稿（D35C）

## 错误特征

日志症状（两类，常同时出现）：

```
make: *** No rule to make target '.cfg-defs'.  Stop.
```
```
/.../src/core/resolve.h:123:4: error: #error "HAVE_GETHOSTBYNAME2 not defined"
/.../src/core/sched_yield.h:31:4: error: #error "HAVE_SCHED_YIELD not defined"
```

或模块 Makefile 探测阶段报 `no way to determine ...`（依赖库探测未命中）。

core 主二进制构建（6.1.3 实测）另见两类：

```
/.../src/core/lock_ops.h:298:4: error: #error "no locking method selected"
```
```
/.../src/core/resolve.c:190:5: error: use of undeclared identifier '_res'
```

## 触发条件

- 构建系统: 经典 Makefile（kamailio 的 `src/Makefile` + `Makefile.defs` 体系，非 autotools/cmake）
- 阶段: configuration → compilation（`make cfg` 与 `make modules`）
- 平台: OHOS aarch64（OS 探测结果为 `harmonyos`；上游 Makefile.defs 只有
  linux / solaris / freebsd / darwin 分支）

## 根因分析

1. **平台分支缺失**：`Makefile.defs` 按 `uname`/目标三元组分派平台宏，`OS=harmonyos`
   不落入任何分支 → `HAVE_GETHOSTBYNAME2` / `HAVE_SCHED_YIELD` / `HAVE_MSG_NOSIGNAL` /
   `HAVE_MSGHDR_MSG_CONTROL` / `HAVE_ALLOCA_H` / `HAVE_TIMEGM` /
   `HAVE_SCHED_SETSCHEDULER` / `HAVE_IP_MREQN` 等探测宏全缺，core 头（`resolve.h`、
   `sched_yield.h`）直接 `#error` 终止。
2. **未先 cfg**：`make modules` 前必须先 `make cfg`（生成 `src/config.mak`/`cfg-defs`），
   否则 make 报 `No rule to make target '.cfg-defs'`。
3. **依赖探测回退链**：模块 Makefile（如 `src/modules/uuid/Makefile`）用
   `BUILDER`/`SSL_BUILDER` 等变量解析依赖库；`CROSS_COMPILE` 为空时先走构建机
   pkg-config，未命中才回退 `LOCALBASE`/`SYSBASE`。交叉编译时构建机系统库
   （libuuid/libssl）可能被误命中，导致产物随构建机漂移。
4. **core 锁机制（6.1.3 实测，模块不触达）**：`found_lock_method` 只由各平台分支
   置位；`OS=harmonyos` 落无名分支后未置位，`src/core/lock_ops.h` 末尾
   `#error "no locking method selected"`。须 `extra_defs` 注入 `-DUSE_PTHREAD_MUTEX`
   （linux 分支默认值，musl 完整支持 pthread mutex）。
5. **musl 不导出 _res 全局（6.1.3 实测，模块不编译 resolve.c）**：`-DHAVE_RESOLV_RES`
   在 `Makefile.defs` 无条件定义（L729，非平台分支），但 OHOS sysroot（musl）
   `resolv.h` 仅有 `struct __res_state` 类型、不导出 `_res` 全局实例 →
   `core/resolve.c` 6 处（L190-197、L926）编译失败。撤销该宏后走上游自带
   `#else` 回退分支（"no resolv options support" 警告），零源码改动。

## 解决方案

### 推荐方案（priority 1，不改源码）

先 `make cfg`，再经 make 命令行 `extra_defs` 注入 linux 分支等价平台宏集，并用空赋值
`BUILDER=`（或 `SSL_BUILDER=` 等）钉死 `LOCALBASE` 回退分支——make 命令行变量优先于
Makefile 内部赋值，故构建机 pkg-config 无法劫持：

```bash
make cfg include_modules=${MOD} LOCALBASE=${DEP_PKG} BUILDER= \
    extra_defs='-D_GNU_SOURCE -DHAVE_GETHOSTBYNAME2 -DHAVE_SCHED_YIELD \
    -DHAVE_MSG_NOSIGNAL -DHAVE_MSGHDR_MSG_CONTROL -DHAVE_ALLOCA_H \
    -DHAVE_TIMEGM -DHAVE_SCHED_SETSCHEDULER -DHAVE_IP_MREQN'
make modules modules=modules/${MOD} -j1 LOCALBASE=${DEP_PKG} BUILDER= \
    extra_defs='<同上>'
```

每个宏须先对照目标平台 sysroot 头文件实证（musl 语义下 `HAVE_UNION_SEMUN` 不注入：
`sys/sem.h` 不导出 `union semun`，core `lock_ops.h` 在宏未定义时自带条件定义）。

**core 主二进制构建变体（6.1.3 实测，见 archives/k/kamailio/6.1.3/notes.md）**：

```bash
DEFS='-D_GNU_SOURCE -DHAVE_GETHOSTBYNAME2 -DHAVE_SCHED_YIELD -DHAVE_MSG_NOSIGNAL \
      -DHAVE_MSGHDR_MSG_CONTROL -DHAVE_ALLOCA_H -DHAVE_TIMEGM \
      -DHAVE_SCHED_SETSCHEDULER -DHAVE_IP_MREQN -DUSE_PTHREAD_MUTEX -DHAVE_EPOLL'
make cfg extra_defs="$DEFS"
env DEFS=-UHAVE_RESOLV_RES make -j4 extra_defs="$DEFS"
```

要点：
- `_res` 撤销必须走**环境变量** `DEFS`（编译行 `$(DEFS)` 位于 `$(C_DEFS)` 之后，
  后置 `-U` 胜出）。make **命令行** `DEFS=` 会锁定变量、吞掉 `main.o` 的目标特定
  `DEFS+=-DMODS_DIR`（main.c 报 `MODS_DIR` 未声明，实测复现）；`extra_defs` 位于
  `-DHAVE_RESOLV_RES` 之前，`-U` 被 `-D` 覆盖——两者均不可行。
- `-DHAVE_EPOLL` 注入后事件循环对齐 linux 构建（`kamailio -v` 显示
  "poll, epoll_lt, epoll_et."，musl 可编译已实证）；不注入则回退 poll（可运行但
  与 linux 行为不一致）。`HAVE_SIGIO_RT`/`USE_FUTEX` 按最小参数原则不注入。
- core 无外部 conan 依赖：pcre2 仅被 modules（regex/dialplan/cnxcc/lcr）引用。
- 产物为 `src/kamailio` 单二进制（ET_DYN/PIE，NEEDED 仅 `libc.so`）；无独立
  libkamailio 库；`srved` 在 6.1.3 源码树已不存在（上游移除）。

### 回退方案（priority 2）

在 `Makefile.defs` 增补 harmonyos 分支（复用 linux 分支语义），以补丁形式提交并在 PR
说明理由（属平台适配补丁）。

### 禁止做法

- ❌ 不传 `LOCALBASE` / 不钉死 `BUILDER` 就跑 `make modules`：模块 Makefile 会用构建机
  pkg-config 探测系统库，CI 与本地结果不一致、静态/动态链接形态漂移，甚至链接到构建机
  系统库导致目标机加载失败。
- ❌ 直接改 `src/config.mak` 等生成文件（应通过 make 变量/宏注入，生成文件不属源码）。

## 验证

```bash
llvm-readelf -d src/modules/<mod>/<mod>.so | grep NEEDED   # 期望仅 libc.so（依赖静态链入）
llvm-nm -D src/modules/<mod>/<mod>.so | grep <sym>          # 依赖符号应为 T（已定义）而非 U
```

core 变体（6.1.3 实测通过）：

```bash
llvm-readelf -d src/kamailio | grep NEEDED   # 期望仅 libc.so
./src/kamailio -v                            # 版本 6.1.3 + flags 含 USE_PTHREAD_MUTEX
                                             # + "poll method support: poll, epoll_lt, epoll_et."
```

## 关联条目

- 相关: [E???]（待主编串接：同类“平台分支未覆盖导致平台宏缺失”条目）
- 相关: [E257 草稿]（musl 不导出 glibc `_res` 全局的 libc 面 delta，见
  `knowledge/drafts/DRAFT-E257-res-state-musl.kv`）
- 先例: kamailio-snmpstats / kamailio-unixodbc / kamailio-tls / kamailio-uuid 6.0.6
- 先例: kamailio core 6.1.3（core 主二进制，lock_ops 锁机制 + musl _res 两处 delta
  实测，2026-09-29）
