# E429 — kamailio 模块（经典 Makefile）OHOS 交叉编译：OS=harmonyos 未被 Makefile.defs 识别 + 依赖探测回退 LOCALBASE

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

## 关联条目

- 相关: [E???]（待主编串接：同类“平台分支未覆盖导致平台宏缺失”条目）
- 先例: kamailio-snmpstats / kamailio-unixodbc / kamailio-tls / kamailio-uuid 6.0.6
