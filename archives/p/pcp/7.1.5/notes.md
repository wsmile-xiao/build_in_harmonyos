# PCP 7.1.5 — OHOS 适配笔记（路径B 知识库扩展）

## 软件概况
- **名称**: Performance Co-Pilot (PCP)
- **版本**: 7.1.5（上游 tag，无 v 前缀）
- **构建系统**: autotools（单顶层 configure，预生成 configure/Makefile）
- **源码 URL**: https://github.com/performancecopilot/pcp/archive/refs/tags/7.1.5.tar.gz
- **sha256**: 54218701c53cbfddd043e50fd2244ab0c04d4cc58742cffdb460b32ea0adaa8c
- **语言**: C 主体（1695 .c / 81%），含 C++（pmcpp/web，258）与 Python 绑定（src/python，可选）

## 最小组件集（--without-* 裁剪）
核心保留 pmcd/pmlogger/pmstat/pmval + pmapi + libpcp；关闭：
perl、python3、qt/qt3d、x、systemd、selinux、secure-sockets、infiniband、
static-probes、perfevent、pmdagfs2/statsd/abpf/abpftrace/json/mongodb/mysql/
nutcracker/snmp、dstat-symlink、gperftools。

## 依赖
| 依赖 | 版本 | 类型 | 制品仓状态 |
|------|------|------|-----------|
| zlib | 1.3.2 | requires | 已发布 |
| libxml2 | 2.15.3.1 | requires | 已发布 |
| lmdb | 0.9.35 | requires | 已发布 |
| libuv | 1.52.1.1 | requires | 已发布 |
| flex | 2.6.4.2 | tool_requires | 已发布 |
| bison | 3.8.2 | tool_requires | 已发布 |

## OHOS 平台适配点（第一阶段：7 类，24 文件）

### 1. config.sub 不识别 linux-ohos triplet
PCP release 预生成 config.sub（2023-06-23）无 ohos 分支。
**修复**: OS case 列表加 `ohos*`（line ~1761）+ kernel-os 校验加 `linux-ohos*`（line ~1782）。
**注意**: OHOS clang 同时定义 `__linux__` 和 `__OHOS__`。

### 2. /tmp 只读（E002）
mk.pmdbg/mk.exports/check-statics/Make.stdpmid/xtractnames 硬编码 `mktemp -d /tmp/...`。
**修复**: 全部改 `mktemp -d "${TMPDIR:-/tmp}/..."` + 构建 env 设 TMPDIR/PCP_TMPFILE_DIR 指向 build_folder 可写目录。

### 3. FILE 不透明类型（glibc 结构拷贝失败）
libpcp/src/util.c + libpcp3/src/util.c 的 `logreopen()` 用 `*dupoldstream = *oldstream`（FILE 结构拷贝，glibc 专属——glibc FILE 是完整类型，OHOS/Bionic/musl 的 FILE 是不透明类型）。
**修复**: 可移植替代——用恢复后的流（oldstream，fdopen 所得，同 fd 同状态）直接作输出，跳过结构拷贝。

### 4. rindex 缺失（BSD 函数）
OHOS libc 无 rindex（有 POSIX 等价 strrchr）。8 文件 15 处调用。
**修复**: rindex( → strrchr(。

### 5. qsort_r 缺失（GNU 扩展）
OHOS libc 无 qsort_r，但 sort_r.h 的 `__linux__` 检查把 OHOS 误路由到系统 GNU qsort_r 分支。
**修复**: sort_r.h 的"libc 无 qsort_r"分支（NetBSD/OpenBSD）加 `!defined __GLIBC__`，路由到可移植 sort_r_simple()。
**R8 合规说明**: 采用 POSIX 兼容写法（qsort_r 是 glibc 专属扩展，非 glibc libc 无此函数），无需 `__OHOS__` 平台宏；顺带修复上游在 musl Linux 的同类潜在问题。探针编译验证：OHOS（-D_GNU_SOURCE 与无）均路由 portable 分支。

### 6. 静态链接不可行（CROSS_COMPILING）
pmcpp.static 等 `.static` 可执行目标需全静态链接（OHOS 静态 libpthread 集成困难）。
**修复**: 构建传 `CROSS_COMPILING=yes`，PCP 自身逻辑跳过 `.static` 目标（ifneq CROSS_COMPILING yes 守卫）。

### 7. /etc 不可写（PCP_CONF/PCP_DIR）
pmieconf/pmlogconf 等构建期工具 source `$PCP_DIR/etc/pcp.conf`，PCP_DIR 未设回退 `/etc/pcp.conf`（OHOS /etc→/system/etc 只读）。
**修复**: 构建传 `PCP_CONF=<source>/src/include/pcp.conf`（构建树已生成），pcp.env 优先用 PCP_CONF。

## 第二阶段适配点（构建全链 + install，9 处）

### 8. /proc/stat idle 时间单位需 HZ（musl sys/param.h 无 HZ）
`src/pmdas/linux_proc/proc_pid.c` 用 `HZ` 把 /proc/stat 的 idle clock tick 换算成秒；glibc sys/param.h 提供 HZ，OHOS musl 的 sys/param.h 没有。
**修复**: include 后 `#ifndef HZ / #define HZ 100 / #endif`（kernel 默认 HZ=100，/proc/stat idle 单位是 clock tick）。

### 9. re_comp/re_exec 缺失（BSD regex 扩展）
`src/pmdas/linux_proc/config.c`（eval_match_comp）与 `lex.l`（PATTERN 规则）用 glibc 在 `_REGEX_RE_COMP` 下声明的 re_comp/re_exec，musl 无。
**修复**: 全部改 POSIX regcomp/regexec/regfree，保留 1/0/-1 返回语义；删两处 `#define _REGEX_RE_COMP`。

### 10. versionsort 缺失（glibc scandir 比较器）
`src/pmdas/linux/proc_stat.c:114` `scandir("/proc", ..., versionsort, ...)`——versionsort 是 glibc 专属，musl 未声明。
**修复**: 改 `NULL`（node 条目逐个解析，顺序无意义）。

### 11. bind2/mk.rewrite 硬编码 pmcpp.static
`src/pmdas/bind2/mk.rewrite:46` 直接调用 `../../pmcpp/pmcpp.static`（CROSS_COMPILING=yes 下不构建 .static）。
**修复**: 改动态 pmcpp + `LD_LIBRARY_PATH=../../libpcp/src`（全树唯一硬编码 .static 调用点）。

### 12. qa/src/multithread10.c 的 rindex
阶段一 rindex 修复覆盖 src/ 树 8 文件；qa/ 树是新增（`rindex` → `strrchr` + 补 `#include <string.h>`）。
**说明**: 属上游测试代码的可移植性修复，不改测试语义（R51 申报项）。

### 13. libpcp3/src/sort_r.h 副本漏改（qsort_r）
阶段一 0006 补丁只改了 `src/external/sort_r.h`；PCP 源树有**两个** sort_r.h 副本，`src/libpcp3/src/sort_r.h` 漏改 → labels.c 经宏展开产生 `undefined reference to qsort_r`。
**修复**: v3 副本同样加 `|| !defined __GLIBC__` 路由到 sort_r_simple。**教训**: 同名头文件多副本必须全改。

### 14. qa/src/GNUlocaldefs 直链 .so 规则缺 LDFLAGS
api_abi_compat(519)/dumpstack(863) 两条链接规则直链 libpcp .so 但无 `$(LDFLAGS)` → 缺 `--allow-shlib-undefined` → lld 拒 libpcp.so.3/4 的 `U pthread_cancel`（sysroot libc 无该符号，设备 libc 有——sysroot≠设备 libc）。
**修复**: 两规则补 `$(LDFLAGS)`。

### 15. install-sh 无条件调 id（OHOS 无 id/chown 命令）
autotools install-sh 无条件 `REAL_UID=`$ID -u`` 判非 root；OHOS 无 id/chown（/system/bin、/usr/bin、/bin、hnp/bin 均无）→ REAL_UID 空 → `test $REAL_UID -ne 0` 语法错 → CHOWN 未被置 no-op → chown not found(127) → `make install` 第一条规则 Error 127。
**修复**: install-sh 加 `[ -n "$REAL_UID" ] || REAL_UID=1`（假定非 root → chown 跳过 → 文件保持自然所有权，正是 hmdfs 所需）。

### 16. make install 前置 default_pcp 重查 build 目标
`install :: default_pcp install_pcp`——install 前置重查所有子目录 default 目标；package() 是独立 self.run，命令行变量不持久 → 不带 `CROSS_COMPILING=yes` 时 builddefs 重算 CROSS_COMPILING=no → STATICTARGETS 恢复 → 重建 pmcpp.static → 静态链接失败（undefined pthread_cancel）。
**修复**: conanfile 抽 `_make_override_vars()` 共享方法，build() 与 package() 的 make 调用用同一份覆盖（防漂移）。

## 构建环境（conanfile generate/build）
- `TMPDIR` / `PCP_TMPFILE_DIR` → build_folder/tmp（可写）
- `CROSS_COMPILING=yes`（跳过 .static 目标）
- `PCP_CONF=<source>/src/include/pcp.conf`
- `LDFLAGS += -lpthread -Wl,--allow-shlib-undefined`（OHOS lld 默认 --no-allow-shlib-undefined；pthread 符号在独立 libpthread.a，共享 libc 无）
- `--with-64bit --with-threads` + 全套 --without-*（最小组件集）

## 上游测试（R51 三步法）

### ① 清点
PCP 上游测试套件 = `qa/`（autotools，非 ctest/pytest）：
- **3774 个编号测试目录**（qa/000 ~ qa/3773 量级），其中 **1762 个带参考输出 .out**（上游 tarball 自带，非运行产物——mtime 2026-05-26 = 上游发布日）
- **qa/src/ 下 273 个 C 测试程序** + 若干 shell 脚本测试（如 addlabels、agenttimeout）
- 多数测试需**运行中 pmcd(8) + PMDA 实时采集链路**（exec pmcd/pmstore 采实时指标）；少数免 context（纯 libpcp 函数级，如 multithread10、dumpstack）

### ② 运行（OHOS 实机，2026-10-09）
- **构建**: qa 全部测试程序在 OHOS 上编译通过（make 构建链全绿，含 8 处 qa 侧修复）
- **免 context 抽样实测**（LD_LIBRARY_PATH 指向 in-tree 库）:
  | 测试 | 结果 | 说明 |
  |------|------|------|
  | multithread10 | ✅ PASS (exit 0) | 多线程 API 测试 |
  | dumpstack | ✅ PASS (exit 0) | 崩溃转储测试 |
  | api_abi_compat | ⚠️ 需 pmcd | `pmNewContext: Connection refused`（无 pmcd 守护，CI 环境限制，非适配缺陷） |
- **需 pmcd context 的大头（3700+ 项）**: CI 无 pmcd 服务、无预置 archive 供离线分析、hmdfs /proc 布局与 Linux 有差异——不可运行（具体技术原因，非笼统"没环境"）

### ③ 回填
- **口径**: B 档——qa 套件多数项因需 live pmcd+实时采集在 CI 不可运行（如实申报）；免 context 抽样 2/2 PASS；L1 消费者测试（test_package）离线通过
- **上游测试修改申报**（2 处，均可移植性修复、不改测试语义）:
  - `qa/src/multithread10.c`: rindex→strrchr + `#include <string.h>`（musl 无 rindex）
  - `qa/src/GNUlocaldefs`: api_abi_compat/dumpstack 链接规则补 `$(LDFLAGS)`（--allow-shlib-undefined）

## 知识沉淀（路径B 核心）
**"OHOS 下 Linux 系统监控/性能库适配"可复用模式**：
1. /proc 数据源差异（**本任务核心沉淀**，草稿 E1005）：OHOS PC 的 procfs 是选择性暴露的，实测（普通用户）：

   | 文件 | 可读性 |
   |------|--------|
   | /proc/stat、/proc/meminfo、/proc/net/dev、/proc/loadavg | ✅ 可读 |
   | /proc/pressure/memory、/proc/self/status | ✅ 可读 |
   | /proc/diskstats | ❌ root-only（EACCES；→ /sys/block/diskstats 符号链接，见 DRAFT-11233） |
   | /proc/pressure/cpu、/proc/pressure/io、/proc/cmdline | ❌ 受限/缺失 |

   关键推论：① PSI 三件套**不是全有/全无**（memory 可读、cpu/io 不可读），代码须逐文件探测；② /proc/diskstats 在 CI/普通用户环境永不可读（无 sudo）；③ PMDA 对缺失文件须标记指标 unavailable 而非 die()（PCP 天然具备此设计，无需为 /proc 打补丁）。
2. glibc 专属假设的 OHOS 替代（草稿 E1006）：FILE 不透明（结构拷贝→流复用）、rindex（→strrchr）、qsort_r（→可移植实现，**注意源树双副本**）、re_comp/re_exec（→regcomp/regexec）、versionsort（→NULL）、HZ（→#ifndef fallback 100）
3. 构建期 /etc 依赖：PCP_CONF 指向构建树配置
4. 严格链接器：OHOS lld --no-allow-shlib-undefined 默认 + 独立 libpthread；**sysroot libc ≠ 设备 libc**（pthread_cancel/qsort_r 设备有、sysroot 无——链接错误优先可移植实现，勿 --allow-shlib-undefined 掩盖）
5. autotools install-sh 无条件调 id（草稿 E1007）：OHOS 无 id/chown 命令 → REAL_UID 空 → test 语法错 → chown 127 → make install Error 127；修复 = `[ -n "$REAL_UID" ] || REAL_UID=1`
6. make install 前置重查 build 目标（草稿 E1008）：`install :: default_pcp` 重查所有子目录 → build 期变量（CROSS_COMPILING 等）必须重传到 package() 的 make install；conanfile 抽共享方法防漂移

**知识草稿清单**（knowledge/drafts/，待主编 promote）：
- E1005-draft-D674: /proc 数据源选择性暴露（核心）
- E1006-draft-D674: glibc/BSD 专属符号 musl 缺口
- E1007-draft-D674: install-sh id/chown 缺口
- E1008-draft-D674: make install 前置重查
---

**编译结束**: 2026-10-09 04:21
**最终状态**: built
