# kamailio-db 6.0.6 适配笔记（OHOS PC / aarch64-linux-ohos）

## 1. 目标库身份

| 项 | 值 |
|---|---|
| 发行版子包名 | `kamailio-db`（Alpine `kamailio` 的 `db` 子包，描述 *"Kamailio modules using a database backend"*） |
| 对应上游工程 | Kamailio SIP Server 6.0.6（https://github.com/kamailio/kamailio） |
| 对应上游模块组 | `_mod_list_db` **33 个模块**（产物 33 个 `*.so`） |
| 身份依据 | `pkg/kamailio/alpine/APKBUILD`：`_mod_list_db="…"`（:199）、`db() { _generic_pkg "modules using a database backend" "$_mod_list_db"; }`（:574）；`pkgs.alpinelinux.org` 记录 `kamailio-db 6.0.6-r1`、`Depends (2) = kamailio + so:libc.musl-x86_64.so.1` |
| 成员清单（33） | `acc alias_db auth_db avpops cfg_db db_cluster db_flatstore dialog dispatcher domain drouting group htable imc matrix mohqueue msilo mtree pdt permissions pipelimit prefix_route p_usrloc registrar sipcapture siptrace speeddial sqlops topos_htable uac uri_db userblocklist usrloc` |
| 与 `src/Makefile.groups` 的差异 | 后者 `mod_list_db` 另含 `db_text`/`secfilter`；Alpine 注释明确 *"Remove db_text from _mod_list_db because we create a separate dbtext package"*，本包**以 Alpine 子包口径为准**（子包名 kamailio-db 的权威成员表） |
| 语言 | C（33 模块全为 C 源文件，无 `.cc/.py/.go/.rs`；R47 lang-preflight：detected=cpp，主体 94% —— c↔cpp 兼容族） |
| 构建系统 | kamailio 自有 make 体系（`src/Makefile` + `Makefile.defs` + `Makefile.modules`）；每个模块另提供 `CMakeLists.txt` 作为替代入口 |
| 范围边界 | **不含**具体 DB 驱动：`db_mysql`/`db_postgres`/`db_unixodbc`/`db_sqlite`/`db_text`/`db_berkeley` 分属**独立子包**（Alpine `_db_driver`；Debian `kamailio-*-modules`；OBS `%package mysql|postgresql|sqlite|unixodbc|bdb`） |

## 2. 源码核验

| 项 | 值 |
|---|---|
| 源码 URL | `https://github.com/kamailio/kamailio/archive/refs/tags/6.0.6.tar.gz`（github.com 官方归档端点） |
| sha256 | `5b8cd435aa52137857bbfc27804479b687a495df5634e7d8513b3ff45e98e1b6`（实测下载后 `sha256sum` 一致） |
| 上游 tag | `refs/tags/6.0.6` |
| 为何用仓库 tag 归档而非官网 src 包 | kamailio 官网发布包 `kamailio-6.0.6_src.tar.gz`（sha256 `32e4290c…`，13,152,560 B）**不含 `test/` 目录**；本包 R51 上游测试入口位于 `test/unit/**`，故采用官方仓库 tag 归档（含完整 `test/` 树：`test/` 顶层 `README.md misc mkinclude mod_httpapitest travis unit`，`test/unit` 49 个 `.sh` / 共 241 个文件） |
| 归档条目数 | `tar tzf` 7449（src 包）→ tag 归档实测解压 6951 文件（`.work` 基线指纹） |
| 端点选择理由 | `codeload.github.com` 不在 CI mirror-fallback 域名白名单（`ci/conan/build_and_test.sh`）内；`github.com/.../archive/refs/tags/<tag>.tar.gz` 与 codeload 同路径归档为**同一字节**（sha256 已实测一致），且可命中官方镜像回退。conandata.yml 只保留官方源，不含任何镜像域名（R39） |

## 3. 依赖

**强制第三方依赖 = 0（无）**。依据（三重取证）：

| 取证面 | 结论 | 证据 |
|---|---|---|
| 构建文件 | 33 个模块 `Makefile` 的 `LIBS=` **全为空**，唯一例外 `dispatcher: LIBS=-lm`（系统库） | `logs/04_buildfile_evidence.log`（依赖分析）、本包 `reports/` 复核 |
| 头文件 | 33 模块全部 `#include <...>` **全为系统/POSIX 头**（无 `mysql.h`/`libpq-fe.h`/`sqlite3.h`/`sql.h`/`<db.h>`/`openssl/…`） | 同上 |
| 模块文档 | 33 个 `doc/<m>_admin.xml` 的 *"External Libraries or Applications"* 全部声明 **None**（`mohqueue` 提及运行期 rtpproxy 应用，非构建期链接库） | 同上 |
| 发行版包库 | Alpine `kamailio-db 6.0.6-r1` 的 `Depends (2)` 仅 `kamailio` + `so:libc.musl-x86_64.so.1` | 同上 |
| W0 可消费性 | 无待探测的第三方依赖包；`conan download kamailio-db/6.0.6 -r=ohpcd --only-recipe` → rc=1（ohpcd 未发布该 ref，**非本包依赖**）；对照组 `zzz-nonexistent-pkg/9.9.9` 同报文同 rc=1 印证语义 | `.dep-analysis/kamailio-db_6.0.6/logs/W0_*.log` |

| 依赖 | 类型 | 说明 |
|---|---|---|
| kamailio core（同源树 `../../core/*`） | W（同源） | 成员模块 `include ../../Makefile.defs`；运行期由 kamailio 主程序在 `RTLD_GLOBAL` 下提供 core 符号，**非第三方包** |
| libc / libm / libdl / libpthread / librt / libresolv | S（系统） | 工具链 sysroot；实测 33 个 `.so` 的 `DT_NEEDED` **仅 `libc.so`**（musl 下 libm 并入 libc） |
| make / clang / pkg-config | T（工具） | 构建机自带（conan profile `tools.build:compiler_executables` 提供 clang 绝对路径） |
| DB 驱动（mariadb-connector-c / libpq / sqlite3 / unixodbc / berkeley-db） | O（运行期，独立子包） | 不阻塞本库构建；如需适配 db_mysql/db_postgres/… 应另立目标 |

传递第三方闭包为空（`R` 为空 → 传递闭包自然为空）。

## 4. OHOS 平台适配要点（实测）

### 4.1 首个真实错误 → 根因 → 修复（朴素构建探针）

| # | 项 | 内容 |
|---|---|---|
| 命令 | `cd <src>/src && make cfg`（无参数）→ `make modules modules=modules/acc -j1` |
| config.mak | `OS= harmonyos`（kamailio 以 `uname -s` 判定 OS，OHOS 上是 `HarmonyOS`） |
| **首个真实错误** | `./../../core/resolve.h:290:2: error: neither gethostbyname2 or getipnodebyname present` |
| 退出码 | `MODULES_RC=2`（`make[1]: *** [../../Makefile.rules:100: acc.o] Error 1`） |
| 日志 | `.dep-analysis` 之外的本次证据：`logs/10_naive_probe.log`（`kamailio-db-6.0.6-evidence/logs/`） |
| 根因 | `OS=harmonyos` 不落入 `Makefile.defs` 的 linux 分支 → 缺 `-DHAVE_GETHOSTBYNAME2` 等 OS_DEFS；`core/resolve.h:290` 的 `#error` 被触发 |
| 修复 | `make cfg OS=linux SCTP=0 DEFS_RM="-DHAVE_RESOLV_RES"`（OHOS 无 harmonyos 专属分支，按 Linux ABI 构建） |
| 重新验证 | 同口径 `make modules modules="…33 个…" -j1` → **33/33 产出 `*.so`，rc=0，0 错误**（`logs/20_make_db_modules.log`） |

### 4.2 模块 ↔ core 口径一致性（关键，决定能否被加载）

kamailio 加载模块时做**两项校验**：目标标识 `(aarch64/<os>)` 与**编译标志集合**。不一致即拒绝加载
（`module version mismatch` / `module compile flags mismatch`）。因此本配方与 OHOS 上 core 的口径完全对齐：

- `OS=linux` → 目标标识 `kamailio 6.0.6 (aarch64/linux)`（实测 33/33 一致）
- `SCTP=0` → OHOS sysroot 无 `netinet/sctp.h`
- `DEFS_RM=-DHAVE_RESOLV_RES` → OHOS libc 无 `_res`（`resolv.h` 不声明）

### 4.3 0 补丁

33 个成员模块源码**不含平台条件编译**（实测 `__OS_*` 仅 solaris/darwin 分支，无 `__OHOS__`/`HAVE_*` 命中），
OHOS 工具链下可直接编译 → `patches/` 为空，未改动任何上游源码/构建文件。

### 4.4 为执行上游测试而做的 core（服务端）适配 —— 不属于本包产物

> 上游 `test/unit/**` 需要完整 kamailio 主程序；以下仅在**测试环境源码副本**
> （`/storage/Users/currentUser/tmp/builds/kamailio-db-6.0.6.full`）中处理，**未进入本包配方/补丁**。

| # | 问题（首个真实错误） | 根因 | 处理 |
|---|---|---|---|
| C1 | `core/resolve.h:290: error: neither gethostbyname2 or getipnodebyname present` | OHOS `uname -s`=`HarmonyOS` 无专属分支 | `make cfg OS=linux` |
| C2 | `core/resolve.c:189: use of undeclared identifier '_res'` | `-DHAVE_RESOLV_RES` 为 C_DEFS 基础定义；OHOS musl 无 `_res` | `DEFS_RM="-DHAVE_RESOLV_RES"` |
| C3 | `sysroot/usr/include/linux/socket.h:23:8: error: redefinition of 'sockaddr_storage'` | OHOS sysroot `linux/socket.h` 无条件定义 `struct sockaddr_storage`，与 libc `sys/socket.h` 冲突（经 `core/socket_info.c:1325` 的 `linux/netlink.h` 链式引入） | 在 netlink 引入点前置 `_UAPI_LINUX_SOCKET_H` + `__kernel_sa_family_t`（`#ifdef __OHOS__` 守卫）**（测试环境用，未进本包补丁）** |
| C4 | sysroot 无 `netinet/sctp.h` | OHOS sysroot 不提供 SCTP 头 | `SCTP=0` |

修复后：`CORE_RC=0`，kamailio 二进制 + **136 个模块 `.so`** 构建完成（`logs/31_core_rebuild.log`）。

## 5. 上游测试申报表（R51 三步法）

### 5.1 清点（适配前）

- 测试入口：`test/unit/Makefile`（目标 `all` = 依次执行 `test/unit/*.sh`；`run` = 单用例 `make UNIT=N.sh run`）
- 用例规模：`test/unit` 下 **49 个 `.sh`**（+ 28 个 `.cfg`、`.sip` 数据、`include/` 公共脚本；`test/` 全树 241 文件）
- 项目级测试套件：**无**（`src/` 内无 `enable_testing`/`add_test` 注册；Alpine APKBUILD `options="!check" # no testsuite`）
- 无 `make check` 目标
- 与本包直接相关：多数用例经 `2.cfg`（全模块清单）与各 `.cfg` 间接加载 DB 模块
  （`usrloc`/`registrar`/`dialog`/`htable`/`permissions`/`siptrace`/`db_cluster` 等）

### 5.2 实测（**49/49 全量执行，未漏测**）

- 执行口径：`cd <src>/test/unit && <interp> ./N.sh`（逐用例 120s 超时，用例间清理 kamailio 进程）
- 解释器：OHOS PC **无 `/bin/bash`**（仅 `/bin/sh`），而上游 36/49 用例 shebang 为 `#!/bin/bash`
  → 按 shebang 显式选择（`#!/bin/bash` → `/data/service/hnp/bin/bash`；`#!/bin/sh` → `/bin/sh`）
- 外部工具：`sipsak` 以 conan 包 `sipsak/0.9.7.1` 提供并加入 PATH；`nc`/`sipp`/`mysql`/`psql`/`isql` 环境缺失
  （对应用例按上游自身守卫 `exit 0` 跳过）
- **结果：total=49, OK=5, FAIL=9, SKIP=35, TIMEOUT=0**
- 日志：`reports/upstream_tests.log`（环境摘要+汇总）、`reports/upstream_tests_summary.tsv`（**49 项逐条**：用例号/描述/退出码/解释器/结果/原因）、
  `reports/upstream_tests_detail.log`（逐用例完整原始输出）、`reports/40_fail_probe.log` + `reports/41_fail_probe_deep.log`（FAIL 根因取证）

### 5.3 结果分布与根因

**5 个 OK**：`1`（最小配置加载）、`3`（kamdbctl mysql 建库/删库）、`9`（kamctl mysql DB 操作）、
`24`（kamdbctl postgres 建库/删库）、`60`（sdpops SDP 操作 SIP 端到端）

**9 个 FAIL（逐项根因，均非本包产物缺陷）**：

| 用例 | 退出码 | 根因 | 类别 |
|---|---|---|---|
| 4 | 255 | `jsonrpcs: Can't create FIFO: Operation not permitted (mode=432)` → `jsonrpc_init_fifo_server` 失败；OHOS 亦无 `mkfifo` 命令 | 平台限制 |
| 5 | 255 | 默认 `etc/kamailio.cfg` 使用 jsonrpcs FIFO transport → 同上 | 平台限制 |
| 6 | 255 | `2.cfg` 全模块清单引用 `dialplan` → `could not find module <dialplan>`（属其他子包） | 用例覆盖面 |
| 7 | 255 | `7.cfg` 用 tm 模块 `delete_timer` 参数 → `parameter <delete_timer> … not found in module <tm>`（6.0.6 已移除） | 上游用例陈旧 |
| 8 | 1 | DBTEXT 建库成功（`kamdbctl create` rc=0），`kamdbctl drop` 走交互确认 `Continue with drop? (y/n):`，非交互环境无 stdin | OHOS 非交互环境 |
| 10 | 126 | `kamctl` 调 `dbtextdb.py`，其 shebang 为 `#!/usr/bin/python3`，OHOS 无该路径（`No such file or directory`） | OHOS 路径 |
| 14 | 255 | `14.cfg` `loadmodule "mi_fifo"` → `could not find module <mi_fifo>`（6.0.6 上游已移除该模块） | 上游用例陈旧 |
| 15 | 255 | 同 6（`db_text` + `2.cfg`，`dialplan` 缺失） | 用例覆盖面 |
| 18 | 255 | `-u $(id -u) -g $(id -g)` → `id: inaccessible or not found`（OHOS 无 `id`；另受 setuid/setgid 平台限制） | OHOS 环境 |

**35 个 SKIP**：均为上游用例自身的 `check_module/check_sipsak/check_sipp/check_netcat`
守卫在缺前置时输出 `… not found, not run` 后 `exit 0` —— 缺 DB 驱动模块（`db_mysql` 8 / `db_postgres` 4 /
`db_unixodbc` 2 / `db_berkeley` 1 / `utils` 1，**均属独立子包**）或 `sipp`(15)/`netcat`(2) 工具。

### 5.4 结论（诚实口径）

- 本包 33 个模块在 `test/unit` 中由多个用例间接覆盖，但在**缺 DB 驱动独立子包**时，多数 DB 场景用例按
  上游自身守卫 SKIP；本包**未修改任何上游测试文件**（`patches/` 为空）。
- `test_package` 的断言（37 项）**不替代**上述统计，两者独立汇报。

## 6. 验证结果（真实命令 / 退出码）

```bash
# 1) 依赖可消费性（R36/W0）：本包无强制第三方依赖 → 无需探测
conan download kamailio-db/6.0.6 -r=ohpcd --only-recipe     # rc=1（ohpcd 未发布，非依赖）

# 2) 真实 conan create（源码真实下载 + test_package 37 断言）
conan create archives/k/kamailio-db/6.0.6 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  -c tools.files.download:retry=6 -c tools.files.download:retry_wait=15 \
  --user=ohpcd --channel=stable                              # rc=0
#   → Sources correctly downloaded from https://github.com/kamailio/kamailio/archive/refs/tags/6.0.6.tar.gz
#   → 断言：通过 37 / 失败 0 ；[H7] OHOS 加载器实测 total=33 failed=0
#   → package(): Packaged 33 '.so' files + 1 COPYING

# 3) conan-verify（G0-G4 + L2/L4/L5）
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify kamailio-db 6.0.6     # rc=0
#   → G1 PASS / G2 PASS（干净构建）/ G3 PASS / G4 PASS / L2·L4·L5 PASS；报告 reports/conan-verify-report.md
```

## 7. 知识沉淀

**本包首个错误模式已在知识库中有对应条目，未新增重复草稿**：

| 既有条目 | 覆盖内容 |
|---|---|
| `knowledge/drafts/DRAFT-12718-kamailio-lost-6.0.6-multidep-localbase-and-os-branch` | 同类 error_signature（`neither gethostbyname2 or getipnodebyname present`）+ `OS` 由 uname 推导导致平台分支静默失效 + `OS=linux` 处置（含受控实验证据） |
| `knowledge/drafts/kamailio-extras-6.0.6-ohos-platform-defs-injection` | 另一路线：`extra_defs` 注入 linux 分支等价宏集 |
| 正式条目 `E091` | `sockaddr_storage` 重定义 / netlink 引入点守卫法（与本包测试环境 C3 同源） |

> 曾尝试新增 `E429-draft-548D.kv`，经比对与 `DRAFT-12718` 的 error_signature 与处置口径完全重复，
> 且自动生成的 md 为未填占位符 → **已删除**，改为引用既有条目（避免知识库重复条目噪音）。

本版实测补充经验（notes 层面）：

1. **模块与 core 的"目标标识 + 编译标志集合"双重校验**决定模块必须与 core 同口径构建
   （OHOS：`OS=linux SCTP=0 DEFS_RM=-DHAVE_RESOLV_RES`），否则 `module version/flags mismatch` 拒绝加载。
2. OHOS `test/unit` 用例因 `#!/bin/bash` 在无 `/bin/bash` 的机器上需按 shebang 选解释器。
3. `db_*` 驱动为独立子包，DB 场景用例在缺驱动时按上游守卫 SKIP（非本包缺陷）。


## 8. 交付物

| 文件 | 说明 |
|---|---|
| `lib/kamailio/modules/*.so` | 33 个模块（ELF64 / AArch64 / ET_DYN，`NEEDED` 仅 `libc.so`，无 RPATH，目标标识 `aarch64/linux`） |
| `licenses/COPYING` | 上游 GPL-2.0 许可原文（16,405 B） |

## 9. 注意事项

- 本包产物是 kamailio 运行期 `loadmodule`(dlopen) 的插件，**不可**作为链接库使用（`cpp_info.libs` 为空）；
  使用时放入 kamailio 模块目录（`lib/kamailio/modules/` 或运行期 `-L` 指定）。
- **消费方的 kamailio core 必须与模块同口径构建**（OHOS：`OS=linux SCTP=0 DEFS_RM=-DHAVE_RESOLV_RES`），
  否则 kamailio 会以 version/flags mismatch 拒绝加载。
- **DB 驱动需另装独立子包**（如 `db_mysql`/`db_postgres`/`db_unixodbc`/`db_text`）才能实际持久化；
  本包仅提供"使用数据库后端 API"的模块。
- 仓库既有 `archives/l/libXext/` 与 `archives/l/libxext/` 的大小写冲突（`core.ignorecase=true` +
  文件系统不区分大小写），任一 worktree 中二者必有 2 个文件显示为 modified；**提交必须使用显式文件白名单**，
  禁止 `git add -A`。

## 10. 适配过程对话记录（关键节点）

### 对话 #1 worktree 与分支
- `git fetch origin main`（atomgit SSH）→ `git worktree add -b feat/kamailio-db-6.0.6 <wt> origin/main`
- 结果：HEAD=`2446216757`（origin/main）；未切换主仓库分支（避免影响并发会话）

### 对话 #2 init-build 初始化
- `ohc-run.py init-build kamailio-db 6.0.6 --auto --url=https://github.com/kamailio/kamailio/archive/refs/tags/6.0.6.tar.gz`
- 结果：解压到 `…/kamailio-db-6.0.6.work`（6951 文件），归档骨架建立
- 注：`find_project_dir()` 以脚本所在目录为项目根，故全程显式 `OHC_PROJECT_DIR=<wt>`

### 对话 #3 语言预检（R47）
- `ohc-run.py lang-preflight kamailio-db 6.0.6 --src <work>` → rc=0，`detected=cpp`（主体 94%，c↔cpp 兼容族）

### 对话 #4 朴素构建探针（暴露首个真实错误）
- `cd <src>/src && make cfg`（无参数）→ `OS= harmonyos`
- `make modules modules=modules/acc -j1` → **首个错误**：`core/resolve.h:290:2: error: neither gethostbyname2 or getipnodebyname present`，`MODULES_RC=2`
- 日志：`logs/10_naive_probe.log`

### 对话 #5 修复口径后的 33 模块构建
- `make cfg OS=linux SCTP=0 DEFS_RM="-DHAVE_RESOLV_RES"` + `make modules modules="…33 个…" -j1`（同口径）
- 结果：**33/33 产出 `.so`，rc=0，0 错误**；日志：`logs/20_make_db_modules.log`

### 对话 #6 产物 ABI / 契约核验
- `llvm-readelf -h/-d` ×33 + 自解析 ELF 读 `exports->name`
- 结果：33/33 `ELF64/AArch64/ET_DYN`、`NEEDED` 仅 `libc.so`、无 RPATH、契约名 == 目录名、目标标识 `kamailio 6.0.6 (aarch64/linux)`
- 日志：`logs/21_artifact_abi.log`、`logs/22_contract_names.log`

### 对话 #7 测试环境 core 构建（平台修复 C3）
- 完整构建 core → 首错 `sysroot/usr/include/linux/socket.h:23:8: error: redefinition of 'sockaddr_storage'`（`CORE_RC=2`）
- 处置：`core/socket_info.c` netlink 引入点前置 `_UAPI_LINUX_SOCKET_H` + `__kernel_sa_family_t`（`#ifdef __OHOS__`，**仅测试环境，未进本包补丁**）
- 结果：`CORE_RC=0`，kamailio 二进制 + 136 模块；日志：`logs/30_full_build.log`、`logs/31_core_rebuild.log`

### 对话 #8 上游 test/unit 全量执行
- 逐用例 `cd test/unit && <interp> ./N.sh`（按 shebang 选解释器；120s 超时；用例间清理 kamailio 进程）
- 首轮现象：36/49 用例 `#!/bin/bash` 在无 `/bin/bash` 的 OHOS 上 exit 127 → 按 shebang 显式选解释器 + `sipsak/0.9.7.1` 入 PATH
- 结果：**total=49 OK=5 FAIL=9 SKIP=35 TIMEOUT=0**；日志：`reports/upstream_tests*.log|tsv`

### 对话 #9 FAIL 用例根因取证
- 用例脚本内部 `> /dev/null` 吞掉了 kamailio 输出 → 以 `-DD -E` 前台复现 + 原样复现 `kamdbctl`
- 结果：9 项根因逐条确证（FIFO EPERM / `id` 缺失 / `mi_fifo` 与 `tm delete_timer` 陈旧 / `dialplan` 非本子包 / `dbtextdb.py` shebang / `kamdbctl drop` 交互）
- 日志：`reports/40_fail_probe.log`、`reports/41_fail_probe_deep.log`

### 对话 #10 test_package 与 conan create
- 预验证（fake package 结构）→ `CHECKER_RC=0`（37 断言）、`PROBE_RC=0`（dlopen 33/33）
- `conan create`（真实下载 + test_package）→ 打包 33 `.so` + COPYING、断言 37/0、`[H7] dlopen total=33 failed=0`

### 对话 #11 conan create 网络问题处置
- 首跑：`codeload.github.com Read timed out`（下载 3%），rc=1 —— 网络波动，非配方问题
- 处置：`-c tools.files.download:retry=6 -c tools.files.download:retry_wait=15` 重跑
- 结果：`Sources correctly downloaded from https://github.com/kamailio/kamailio/archive/refs/tags/6.0.6.tar.gz`，rc=0（日志 `logs/51_conan_create_r2.log`）

### 对话 #12 conan-verify 失效镜像处置 / finish
- conan-verify 首跑：G2 卡在 SKILL 的 E017 临时注入镜像 `ghfast.top`（实测 `http=000` 不可达）
- 处置：终止 → 按守卫还原 conandata → 以本机既有 `core.sources:download_cache`（按**内容 sha256** 命中）重跑 → **G1/G2/G3/G4 PASS**
- finish 首跑：W3 的 JC5 命中 **main 上其他包**的存量隐藏文件（`cloog`/`kics`/`libbfio`/`thc`）→ 以 `JUNK_PR_DIFF`（本包 pr.diff）重跑 → **W3 通过**，`.ci-result.json`（exit_code=0）生成
---

**编译结束**: 2026-10-03 15:19
**最终状态**: built
