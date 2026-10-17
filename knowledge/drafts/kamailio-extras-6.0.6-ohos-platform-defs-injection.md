# kamailio 家族在 OHOS 上：平台探测宏缺失经 make 命令行注入 + 「只编 modules」规避 musl 缺失符号（0 补丁）

> Status: DRAFT（预留条目 E429，草稿期以文件名标识）
> Source: kamailio-extras 6.0.6（Alpine `kamailio` 子包，31 个 extras 模块）HarmonyOS PC 适配，2026-09-29
> Related: 同族 10 个已合入配方 `archives/k/kamailio-{tls,xml,snmpstats,unixodbc,slack,outbound,debugger,kemix,lrkproxy,uuid}/6.0.6`；E074/E525（OHOS 禁 FIFO → `-j1`）；P004、P013

## 背景

仓库内已有 11 个 `kamailio-*` 配方（全部同源 kamailio 6.0.6 源码包，按模块分组打包），
但知识图谱中**没有任何 kamailio 条目**（`grep -ril kamailio knowledge/graph` → 0 命中）。
本条把同族先例的平台结论 + 本次 kamailio-extras 31 模块全量核实结果固化为首个 kamailio 条目。

kamailio 使用的是**经典 Makefile 体系**（非 autotools/cmake/meson）：
`src/Makefile` + `src/Makefile.defs` + `src/Makefile.groups`，模块在
`src/modules/<name>/Makefile`，运行时由 kamailio 主程序 `loadmodule` 动态加载。

## 现象（错误面，按暴露顺序）

```text
1) make: *** No rule to make target 'cfg-defs'.  Stop.
   （未先跑 `make cfg`；同族先例实证）

2) src/core/sched_yield.h: #error "HAVE_SCHED_YIELD is not defined"
   src/core/resolve.h:     #error ... HAVE_GETHOSTBYNAME2 ...
   （OS=harmonyos 不在 Makefile.defs 的任何平台分支内 → HAVE_* 宏全缺）

3) 若连 core 一起编，追加两条 musl 语义差异：
   undefined reference to `_res`        （core/resolve.c，HAVE_RESOLV_RES 相关）
   union semun 相关冲突                  （core/lock_ops.h，HAVE_UNION_SEMUN）

4) 模块 Makefile 里探测外部库的（如 cnxcc 的 hiredis/libevent）：
   探测不到 conan 依赖包 → 走 LOCALBASE 回退 → 缺头文件/缺库
```

## 根因

`src/Makefile.defs` 按 `uname -s` 结果分支（linux/solaris/freebsd/darwin…），
**分支内才定义** `HAVE_GETHOSTBYNAME2` / `HAVE_SCHED_YIELD` / `HAVE_MSG_NOSIGNAL` /
`HAVE_MSGHDR_MSG_CONTROL` / `HAVE_ALLOCA_H` / `HAVE_TIMEGM` / `HAVE_SCHED_SETSCHEDULER` /
`HAVE_IP_MREQN` 等宏。OHOS 上跑 `uname -s` 得 `Linux`，但构建显式 `OS=harmonyos`
时该值不在任何分支内 → 宏一个都没有定义 → core 头 `#error` 直接中断编译。

模块 `.so` 由 kamailio 主程序运行时加载，**不需要参与 core 的链接**：
因此 core 的两条 musl 缺失符号路径（`_res`、`union semun`）在「只编 modules」时根本不触发。

## 方案（本配方实际采用，0 补丁）

```bash
# 1) 生成构建配置（必须；否则报 No rule to make target 'cfg-defs'）
make cfg include_modules="<31 个 extras 模块>" \
     extra_defs="-D_GNU_SOURCE -DHAVE_GETHOSTBYNAME2 -DHAVE_SCHED_YIELD \
                 -DHAVE_MSG_NOSIGNAL -DHAVE_MSGHDR_MSG_CONTROL -DHAVE_ALLOCA_H \
                 -DHAVE_TIMEGM -DHAVE_SCHED_SETSCHEDULER -DHAVE_IP_MREQN"

# 2) 只编模块列表（不编 core），-j1（OHOS SELinux 禁 FIFO，E525/E074）
make modules modules="modules/auth_diameter modules/auth_xkeys ... modules/xprint" -j1 \
     extra_defs="<同上宏集>" \
     HIREDISDEFS=-I<conan hiredis>/include HIREDISLIBS="-L<conan hiredis>/lib -lhiredis" \
     LEVENTDEFS=-I<conan libevent>/include   LEVENTLIBS="-L<conan libevent>/lib -levent"

# 3) 校验：31/31 模块 .so 产出，且 aarch64/ET_DYN、契约名与 kamailio 期望一致、无 RPATH
python3 test_package/check_extras_modules.py
```

`extra_defs` 与 `HIREDIS*/LEVENT*` 这类 make **命令行变量优先于文件内赋值**，
并自动向递归子 make 传递；因此无需改任何源文件 → 「0 补丁」。

## 验证

| 项 | 结果 |
|---|---|
| 模块产出 | 31/31（`auth_diameter` … `xprint`） |
| 产物身份 | 全部 `ELF64 LE / ET_DYN / EM_AARCH64` |
| 模块契约名 | 31/31 与 kamailio 期望一致（上游例外：`ss7ops.so` 声明名为 `ss7`） |
| 依赖面 | 30 个模块 `DT_NEEDED` 仅 `libc.so`；`cnxcc` 另有 `libevent.so`（conan 依赖）；31/31 无 `RPATH`/`RUNPATH` |
| 端到端 | `conan create`（ohos-aarch64 profile）包创建 + `test_package` 36/36 断言通过 |

## 反例（禁止）

- 直接 `sed -i` 改 `Makefile.defs`：改动不进补丁，本地能编、CI 干净源码编不出（R6/P003）。
- `make -j$(nproc)` / `-j>1`：OHOS SELinux 禁 FIFO，jobserver 依赖 FIFO（E074/E525）。
- 注入 `-DHAVE_UNION_SEMUN` / `-DHAVE_RESOLV_RES` 想「补齐」宏：musl 下无对应符号语义，
  反而与 core 的兜底逻辑冲突；正解是只编 modules。

## 适用面

- 直接：仓库内 11 个 `kamailio-*` 配方（同源 6.0.6），以及后续任何 kamailio 模块分组包。
- 泛化：平台探测宏只在 Makefile/shell 里按 **OS 名**分支的经典 Makefile 项目
  （autotools 走 `config.guess`，属于问题域不同，不适用本条）。
