# kamailio-xmpp 6.0.6 适配笔记

## 1. 编译环境

- 目标平台：HarmonyOS PC（OHOS 6.0 / armv8 / aarch64），profile `ci/conan/profiles/ohos-aarch64`
- 编译器：clang 15.0.4（OHOS SDK 26.0.0.18，target `aarch64-unknown-linux-ohos`）
- 构建系统：kamailio 经典 Makefile 体系（`src/Makefile` + `Makefile.defs` + `Makefile.modules`）
- 编译日期：2026-10-03
- 最终状态：**built**（`conan create` rc=0；`conan-verify` G0-G4 + L2/L4/L5 全 PASS）

## 2. 打包口径

`kamailio-xmpp` 对应上游 kamailio 6.0.6 源码树的 **`src/modules/xmpp`** 模块（SIP↔XMPP 网关：
component/server 形态 + 经 expat 的 XMPP stanza 解析），产物为 `lib/kamailio/modules/xmpp.so`。

- 取官方源码包全量构建，**只编译打包 xmpp 模块**（同族 kamailio-http_async / kamailio-xml / kamailio-db 口径一致）
- **不依赖 kamailio 本体包**：模块 `.so` 由 kamailio 运行时 `loadmodule`（dlopen）加载，core 符号由宿主进程提供
- 产物 3 项（`conan create` 实测）：

| 产物 | sha256 |
|---|---|
| `lib/kamailio/modules/xmpp.so`（350,656 B） | `1f9adb55e0e914612e8677a572c3124a975ea30e9ca136a52541f6c760998b86` |

## 3. 编译步骤（真实命令）

### 3.1 目标模块（本包产物）

```bash
# W0 依赖核验（R36）：expat/2.8.2.1.1 已在 ohpcd 制品仓
conan download expat/2.8.2.1.1 -r=ohpcd            # rc=0

cd $BUILD_SRC_DIR/src
CC=/data/service/hnp/bin/clang make cfg include_modules=xmpp \
   OS=linux SCTP=0 DEFS_RM='-DHAVE_RESOLV_RES' \
   LOCALBASE=<expat pkg folder> BUILDER=            # CFG_RC=0
CC=/data/service/hnp/bin/clang make modules modules=modules/xmpp -j1 \
   OS=linux SCTP=0 DEFS_RM='-DHAVE_RESOLV_RES' \
   LOCALBASE=<expat pkg folder> BUILDER=            # MODULES_RC=0 → src/modules/xmpp/xmpp.so
```

### 3.2 上游测试宿主（仅用于运行 test/unit，**非本包产物**）

上游 `test/unit/*.sh` 需要完整 kamailio（core 二进制 + 模块）：

```bash
cd $WORK/src
make cfg OS=linux SCTP=0 DEFS_RM='-DHAVE_RESOLV_RES' LOCALBASE=<expat> BUILDER=      # CFG_RC=0
make -j4 ... --jobserver-style=pipe                                                  # 首次 CORE_RC=2（见 §4.1）
make -k -j4 modules ... --jobserver-style=pipe                                       # MODULES_RC=0（137 个 .so）
```

## 4. 平台差异与遇到的问题

| # | 问题（首个真实错误） | 根因 | 解决方案 |
|---|---|---|---|
| 1 | `core/resolve.h:290: #error neither gethostbyname2 or getipnodebyname present` | kamailio 用 `uname -s` 判定 OS，OHOS 上是 `HarmonyOS`，不落入 `Makefile.defs` 任何 OS 分支 → 无任何 `HAVE_*` 探测宏 | 显式 `OS=linux`（OHOS 无 harmonyos 专属分支），等价 linux 分支宏集 |
| 2 | 模块被 core 拒绝加载：`module version/flags mismatch` 风险 | `core/sr_module.c` 对 `SER_FULL_VERSION` 与 `SER_COMPILE_FLAGS`（`ver_defs.h` 展开 USE_SCTP/HAVE_RESOLV_RES/分配器/锁等）做**严格 strcmp** | 模块与 core 同口径：`SCTP=0`（sysroot 无 `netinet/sctp.h`）+ `DEFS_RM=-DHAVE_RESOLV_RES`（OHOS libc 无 `_res`）。实测完整 core 装载 xmpp.so 通过（无 mismatch） |
| 3 | 测试宿主 core 编译：`core/socket_info.c:1325 → linux/socket.h:23: error: redefinition of 'sockaddr_storage'` | OHOS 内核 UAPI `linux/socket.h` 与 musl `sys/socket.h` 都定义 `sockaddr_storage`，`linux/netlink.h` 间接引入后同 TU 相遇 | 测试宿主按知识条目 **E091**（`rec_approach=define-guard`）加 `#ifdef __OHOS__` 宏重命名守卫；**该改动只作用于测试宿主，不进入本包补丁/产物** |
| 4 | 无法用 `make modules` 构建全部模块 | `make modules` 只编默认分组，dialplan/utils/db_* 等不在其中 | 如实记录（上游用例 6/14/15 因此 FAIL/SKIP），不影响本包 |

### 4.1 上游测试宿主 core 失败的首个错误与修复（完整闭环）

- 命令：`make -j4 OS=linux SCTP=0 DEFS_RM='-DHAVE_RESOLV_RES' LOCALBASE=<expat> BUILDER= --jobserver-style=pipe`
- 原始输出（首个错误）：`/data/service/hnp/ohos-sdk.org/.../sysroot/usr/include/linux/socket.h:23:8: error: redefinition of 'sockaddr_storage'`；`make: *** [Makefile.rules:100: core/socket_info.o] Error 1`（CORE_RC=2）
- 根因：见上表第 3 行
- 修复：E091 define-guard（`logs/31_core_e091_patch.log`、脚本 `patch_core_e091.py`）
- 重新验证：`make -j4 …` → **CORE_RC=0**，产出 `src/kamailio`（11,426,304 B）（`logs/32_core_rebuild.log`）

## 5. 补丁（1 个）：上游 xode 解析器空指针解引用修复

- 文件：`patches/0001-src-modules-xmpp-xode_from.c.patch`（`patch_type: bugfix`，**与平台无关**，无任何平台宏）

**缺陷**：`src/modules/xmpp/xode_from.c:36`

```c
static void _xode_put_expatattribs(xode current, const char **atts)
{
	int i = 0;
	if(atts == NULL)          /* 只判 atts 本身 */
		return;
	while(*(atts[i]) != '\0') {   /* ← 未判 atts[i] 即解引用 */
```

**实测证据**（`logs/` 内探针源码与输出）：

1. 纯 expat 探针（不经模块）：对 `<a/>`（无属性元素），start 回调收到 **非 NULL 的 atts 数组**且 `atts[0] == NULL`；
   - expat **2.8.2**（conan 依赖）：`START name=a atts=0x…88 atts[0]=0 (数组首元素为 NULL)`
   - expat **2.7.3**（设备 hnp 静态库对照）：同样 `atts[0]=0`
   - 即"无属性 → atts[0]==NULL"是 expat 的稳定语义，**与版本/平台无关**
2. 模块侧：`xode_from_str("<a/>")` 在 SIGSEGV 处理器下定位到 `pc` 属 xmpp.so 偏移 `0x27db4`，落在 `_xode_put_expatattribs` 的 `ldrb w8,[x8]`（x8=0）→ 空指针解引用（`logs/` 探针 probe2）
3. 影响面：任何**无属性元素**（`<body>` / `<status>` / `<show>` …）解析即崩溃 —— XMPP stanza 的常见形态，故必须修复才能交付可用模块

**修复**：补 `atts[i] != NULL` 判空（有属性元素行为完全不变）：

```c
	while(atts[i] != NULL && *(atts[i]) != '\0') {
```

**验证**：修复后消费者用例真实调用 `xode_from_str` 解析
`<presence from="alice@example.com"><status>online</status></presence>` 全部通过（名称/属性/子元素文本/序列化/非法 XML 负例），
`conan create` rc=0，31 项断言 0 失败（`logs/52_conan_create.log`、`logs/20_verify_xode_fix.log`）

**补丁未加平台宏的原因**：该缺陷与平台无关（expat 语义在所有平台一致），加 `__OHOS__` 守卫反而会把缺陷留给其他平台；如按 R8 口径说明，PR 中已注明。

## 6. 上游测试用例申报表（R51 三步法）

### 6.1 清点（第一步）

| 项 | 实测 |
|---|---|
| 上游测试入口 | `test/unit/*.sh`（shell 集成用例，逐个启动 kamailio 二进制加载 SIP 配置并断言退出码） |
| 用例总数 | **49**（`ls test/unit/*.sh \| wc -l`；含 `50.sh`/`60.sh`/`61.sh` 编号跳号） |
| 其他注册式测试 | 无 ctest / pytest / `make check` 目标（`test/README.md` 自述 under development；顶层 Makefile 无 test 目标） |
| 测试宿主依赖工具 | `sipsak`（conan 制品）、`sipp`（缺失）、`netcat`（缺失）、`id`（缺失）、`#!/usr/bin/python3`（路径不存在） |

> 选源说明：**官网发布包 `kamailio-6.0.6_src.tar.gz` 不含 `test/` 目录**（实测 0 命中），
> 故本包采用官方仓库 tag 归档（含完整 `test/` 树）——这是本包与同族 kamailio-xml/http_async
> 选源不同之处，目的是让上游测试入口随源码可核验。

### 6.2 真实执行（第二步）

```bash
# 运行器（含逐用例命令/退出码/原始输出落盘）
/data/service/hnp/bin/bash 40_run_upstream_tests.sh
# 环境：cwd=$WORK/test/unit；BIN=$WORK/src/kamailio；MOD_DIR=$WORK/src/modules（137 个 .so）
#       LD_LIBRARY_PATH=<expat pkg>/lib；PATH 含 sipsak；TMPDIR=$HOME/tmp
#       逐用例 timeout 120，按 shebang 选择解释器（#!/bin/bash → hnp bash；#!/bin/sh → /bin/sh）
```

**结果：49/49 全量执行，无漏测** —— `total=49 pass=5 fail=9 skip=35 timeout=0`

| 口径 | 数量 | 通过率 |
|---|---|---|
| OK | **5** | 5/49 = **10.2%** |
| FAIL | 9 | — |
| SKIP（上游用例自身守卫 "not found, not run"） | 35 | — |
| TIMEOUT | 0 | — |

日志路径：
- 汇总与运行环境：`kamailio-xmpp-6.0.6-evidence/logs/40_upstream_tests.log`
- 逐用例台账（TSV）：`kamailio-xmpp-6.0.6-evidence/logs/40_upstream_tests_summary.tsv`
- 逐用例原始输出：`kamailio-xmpp-6.0.6-evidence/logs/40_upstream_tests_detail.log`
- FAIL 逐项复现首错：`kamailio-xmpp-6.0.6-evidence/logs/42_fail_repro.log`

### 6.3 逐用例台账（49 项，全部执行）

| 用例 | 用例说明（上游原文） | 解释器 | 结果 | 首错/原因 |
|---|---|---|---|---|
| `1.sh` | load a minimal config | bash | **OK** | — |
| `2.sh` | load all modules without external dependencies with mysql | sh | **SKIP** | ../../src/modules/db_mysql/db_mysql.so not found, not run |
| `3.sh` | creates a mysql database with kamailiodbctl and deletes it a | bash | **OK** | — |
| `4.sh` | test basic fifo functionality | sh | **FAIL** |  |
| `5.sh` | loads the kamailio default config | sh | **FAIL** |  |
| `6.sh` | checks a specific configuration with 'kamailio -c' | bash | **FAIL** |  |
| `7.sh` | loads a SIP proxy/registrar config with offnet-termination a | sh | **FAIL** |  |
| `8.sh` | creates a dbtext database with kamailiodbctl and deletes it | bash | **FAIL** |  |
| `9.sh` | test basic db related kamailioctl functionality for mysql | bash | **OK** | — |
| `10.sh` | test basic db related kamailioctl functionality for dbtext | bash | **FAIL** |  |
| `11.sh` | database access and persistent storage for registrar on mysq | bash | **SKIP** | ../../src/modules/db_mysql/db_mysql.so not found, not run |
| `12.sh` | configuration with pseudo-variables, transformations and xlo | sh | **SKIP** | netcat not found, not run |
| `13.sh` | loads a carrierroute config for loadbalancing from mysql dat | bash | **SKIP** | ../../src/modules/db_mysql/db_mysql.so not found, not run |
| `14.sh` | loads a carrierroute config for loadbalancing from config fi | bash | **FAIL** |  |
| `15.sh` | load all modules without external dependencies with dbtext | bash | **FAIL** |  |
| `16.sh` | load all modules without external dependencies with postgres | bash | **SKIP** | ../../src/modules/db_postgres/db_postgres.so not found, not run |
| `17.sh` | load all modules without external dependencies with db_berke | bash | **SKIP** | ../../src/modules/db_berkeley/db_berkeley.so not found, not run |
| `18.sh` | runs ../kamailio with all command line arguments. | sh | **FAIL** | ./18.sh[37]: id: inaccessible or not found |
| `19.sh` | check user lookup for proxy functionality with usrloc and re | sh | **SKIP** | sipp not found, not run |
| `20.sh` | test basic accounting functionality | sh | **SKIP** | sipp not found, not run |
| `21.sh` | tests the authentification via auth_db | bash | **SKIP** | sipp not found, not run |
| `22.sh` | database access and persistent storage for registrar on post | bash | **SKIP** | ../../src/modules/db_postgres/db_postgres.so not found, not run |
| `23.sh` | loads a carrierroute config for loadbalancing from postgres | bash | **SKIP** | ../../src/modules/db_postgres/db_postgres.so not found, not run |
| `24.sh` | creates a postgres database with kamailiodbctl and deletes i | bash | **OK** | — |
| `25.sh` | loads a userblacklist config from mysql database and test so | bash | **SKIP** | sipp not found, not run |
| `26.sh` | do some routing with carrierroute route sets from mysql data | bash | **SKIP** | ../../src/modules/db_mysql/db_mysql.so not found, not run |
| `27.sh` | test publish and subscribe for presence | sh | **SKIP** | sipp not found, not run |
| `28.sh` | tests simple cpl-c script operations with mysql | bash | **SKIP** | sipp not found, not run |
| `29.sh` | tests simple cpl-c script operations with postgres | bash | **SKIP** | sipp not found, not run |
| `30.sh` | do some routing with carrierroute route sets from a config f | bash | **SKIP** | sipp not found, not run |
| `31.sh` | database access with fetch_result for usrloc on mysql | bash | **SKIP** | ../../src/modules/db_mysql/db_mysql.so not found, not run |
| `32.sh` | database access with fetch_result for usrloc on postgres | bash | **SKIP** | sipp not found, not run |
| `33.sh` | test cfgutils and pv module | sh | **SKIP** | netcat not found, not run |
| `34.sh` | load all presence related modules with mysql | sh | **SKIP** | ../../src/modules/db_mysql/db_mysql.so not found, not run |
| `35.sh` | check permissions module functionality | bash | **SKIP** | sipp not found, not run |
| `36.sh` | private memory effiency and fragmentation with ul_dump w/ or | bash | **SKIP** | ../../src/modules/db_mysql/db_mysql.so not found, not run |
| `37.sh` | loading times for bigger carrierroute config from mysql data | bash | **SKIP** | ../../src/modules/db_mysql/db_mysql.so not found, not run |
| `38.sh` | load all modules without external dependencies with unixodbc | bash | **SKIP** | ../../src/modules/db_unixodbc/db_unixodbc.so not found, not run |
| `39.sh` | database access with fetch_result for usrloc on unixodbc | bash | **SKIP** | sipp not found, not run |
| `40.sh` | check pike module | bash | **SKIP** | sipp not found, not run |
| `41.sh` | test one out of PKG_MEM condition with avpops module | bash | **SKIP** | sipp not found, not run |
| `42.sh` | do some (non numerical) routing with carrierroute route sets | bash | **SKIP** | ../../src/modules/db_mysql/db_mysql.so not found, not run |
| `43.sh` | check forward functionality in utils module | bash | **SKIP** | ../../src/modules/utils/utils.so not found, not run |
| `44.sh` | database access and persistent storage for registrar on unix | bash | **SKIP** | ../../src/modules/db_unixodbc/db_unixodbc.so not found, not run |
| `45.sh` | check memcached module with a basic usrloc scenario | bash | **SKIP** | sipp not found, not run |
| `46.sh` | Check configuration framework implementation in k modules | bash | **SKIP** | sipp not found, not run |
| `50.sh` | database access and persistent storage for registrar on mysq | bash | **SKIP** | ../../src/modules/db_mysql/db_mysql.so not found, not run |
| `60.sh` | checks sdpops module function remove_line_by_prefix() | sh | **OK** | — |
| `61.sh` | checks sdpops module function sdp_remove_line_by_prefix() vi | sh | **SKIP** | ../../src/modules/app_lua/app_lua.so not found, not run |

### 6.4 9 项 FAIL 逐项根因（复现取真实首错）

| `4.sh` | test basic fifo functionality | **FAIL** (255) | 复现首错：`jsonrpcs_fifo.c:72: Can't create FIFO: Operation not permitted (mode=432)` → OHOS SELinux 禁止用户进程创建 FIFO（与同族 E525/E074 同源），jsonrpcs 的 fifo transport 无法初始化 → kamailio 启动失败 |
| `5.sh` | loads the kamailio default config | **FAIL** (255) | 复现首错同 4.sh（默认 `etc/kamailio.cfg` 启用 jsonrpcs fifo transport）；另该用例注解 "Needs a default kamailio database setup for mysql"，而 db_mysql 属独立包未构建 |
| `6.sh` | checks a specific configuration with 'kamailio -c' | **FAIL** (255) | 复现首错：`could not find module <dialplan>` → 测试宿主 `make modules` 默认分组未含 dialplan（非本包产物问题） |
| `7.sh` | loads a SIP proxy/registrar config with offnet-termination a | **FAIL** (255) | 复现首错：`parameter <delete_timer> of type <2:int> not found in module <tm>` → 上游 7.cfg 与 6.0.6 tm 模块参数已漂移；且注解注明需 mysql DB 环境 |
| `8.sh` | creates a dbtext database with kamailiodbctl and deletes it | **FAIL** (1) | 复现：`kamdbctl create dbtext` → `** ERROR: database engine not specified`；用例脚本按旧版 kamctlrc 文本 `# DBENGINE=MYSQL` 做 sed，6.0.6 的 kamctlrc 已改格式 → sed 未命中 → DBENGINE 为空（上游用例与 6.0.6 工具链漂移） |
| `10.sh` | test basic db related kamailioctl functionality for dbtext | **FAIL** (126) | 复现首错：`../../utils/kamctl/dbtextdb/dbtextdb.py: No such file or directory` → 该脚本 shebang 为 `#!/usr/bin/python3`，OHOS 无 /usr/bin/python3（python3 在 `~/usr/local/bin/python3`） |
| `14.sh` | loads a carrierroute config for loadbalancing from config fi | **FAIL** (255) | 复现首错：`could not find module <mi_fifo>` → mi_fifo 是被 6.0.6 移除的旧模块，上游 14.cfg 未同步（上游用例陈旧） |
| `15.sh` | load all modules without external dependencies with dbtext | **FAIL** (255) | 复现首错：`could not find module <dialplan>`（同 6.sh），其后还需 db_text 与 dbtext 数据库文件 |
| `18.sh` | runs ../kamailio with all command line arguments. | **FAIL** (255) | 复现首错：`id: inaccessible or not found`（OHOS 无 `id` 命令）+ `18.cfg: Can't initialize shared memory`（该用例用非默认 shm 参数启动） |

> 9 项 FAIL **均非本包产物（xmpp.so）缺陷**：7 项属测试宿主/环境能力缺口（FIFO、第三方 DB 驱动模块、dialplan/mi_fifo 模块、`id`/netcat/sipp 命令、python3 shebang），2 项属上游用例与 6.0.6 工具链/配置漂移（8.sh 的 kamctlrc 文本、7.sh 的 tm 参数）。复现命令：`logs/42_fail_repro.sh`（去掉用例内输出重定向并加 `-E`），原始输出 `logs/42_fail_repro.log`。

**SKIP=35 的精确分类**（用例自身守卫输出 "… not found, not run"，即上游定义的"前置不满足不执行"；逐项由 `logs/40_upstream_tests_summary.tsv` 统计）：

| 缺失前置 | 项数 | 用例 |
|---|---|---|
| `sipp` 命令行工具 | 15 | 19/20/21/25/27/28/29/30/32/35/39/40/41/45/46 |
| 第三方 DB 驱动模块（合计 16） | 16 | db_mysql 10：2/11/13/26/31/34/36/37/42/50；db_postgres 3：16/22/23；db_unixodbc 2：38/44；db_berkeley 1：17 |
| `netcat` | 2 | 12/33 |
| `app_lua` 模块 | 1 | 61 |
| `utils` 模块 | 1 | 43 |
| **合计** | **35** | 与用例总数 49 − OK 5 − FAIL 9 = 35 一致 |

> SKIP 由上游用例自身的 `check_module()`/`require.sh` 守卫产生，本包如实回填，未删除或改写任何上游用例。

### 6.5 结论

- **未修改任何上游测试用例**（`patches/` 内无 test 相关改动，0 删除 0 改写）
- 49/49 全量执行；FAIL/SKIP **如实回填**，未通过删改用例提升通过率
- 5 项 OK 中含 `1.sh`（最小配置启动）、`3.sh`/`24.sh`（kamdbctl 造库）、`9.sh`（kamctl db 操作）、`60.sh`（sdpops 解析）——证明 OHOS 上 core 可启动、模块可加载、SIP 配置可解析
- 本模块（xmpp）在上游 `test/unit` 中**无专属用例**（无 xmpp 相关 .sh），故模块级功能由 `test_package` 消费者用例实测覆盖（§7）

## 7. test_package 消费者用例（含鸿蒙专项）

`test_package/` = 19 项产物/平台契约断言（`check_module.py`）+ 12 项消费者断言（`test_consumer.c`），`conan create` 实测 **31/31 PASS、0 FAIL**。

**鸿蒙专项（[H] 标记，≥1 项要求已满足）**：
1. `[H] e_machine=AArch64` —— 鸿蒙 PC 目标架构
2. `[H] 目标标识 kamailio 6.0.6 (aarch64/linux)` —— core 装载 strcmp 项
3. `[H] 编译标志串含 USE_TCP/F_MALLOC`、`[H] 不含 USE_SCTP`、`[H] 不含 HAVE_RESOLV_RES` —— 与 OHOS core 口径一致
4. `[H] NEEDED 无 glibc 专名库`（musl 契约）、`[H] NEEDED 全为裸文件名`（可重定位）、`[H] NEEDED 含 libc.so`
5. `[H] 动态段无 RPATH/RUNPATH`（无构建机路径泄漏）

**消费者实测（真实功能，非符号断言）**：`dlopen(libexpat.so)` → `dlopen(xmpp.so, RTLD_NOW)`（全部重定位当场解析）→
dlsym 契约符号（`module_version`/`module_flags` 按 core 口径作 `char **` 数据符号）→ 经 dlsym 调用模块
**自身 XMPP stanza 解析 API**：`xode_from_str` → `xode_get_name` / `xode_get_attrib` / `xode_get_tagdata` / `xode_to_str` / `xode_free`，
并含非法 XML 负例（必须返回 NULL）。

> 消费者进程的 core 符号桩由配方按 nm 未解析表生成，**排除依赖库导出符号**（expat 的 `XML_*`）与本进程可解析符号；
> 桩与消费者二进制生成在 `$TMPDIR`，测试结束即清理（不写入归档树）。实现细节见 `test_package/conanfile.py` 头部说明。

**独立于 test_package 的额外运行时验证**（真实 kamailio core 装载本模块）：

```bash
$WORK/src/kamailio -E -DD -L $WORK/src/modules -Y . -P ./kamailio.pid -w . -f load3.cfg
# load3.cfg: loadmodule "tm.so"  /  loadmodule "xmpp.so"  /  request_route { ; }
# 结果：无 "module version/flags mismatch"；mod_init 成功；kamailio 正常启动监听后被 timeout 杀停
#       （唯一运行期告警为模块默认对端 xmpp.example.com 解析失败，属模块默认配置而非装载问题）
```

## 8. 验证结果

| 检查 | 命令 | 结果 | 日志 |
|---|---|---|---|
| W0 依赖可消费（R36） | `conan download expat/2.8.2.1.1 -r=ohpcd` | rc=0 | 05_expat_packages.json |
| 模块编译 | `make cfg/modules ...` | CFG_RC=0 / MODULES_RC=0 | 10_make_xmpp_module.log |
| 上游测试宿主 core | `make -j4 ...`（E091 修复后） | CORE_RC=0（11.4 MB 二进制） | 30_full_build.log / 32_core_rebuild.log |
| 上游测试 | `40_run_upstream_tests.sh` | 49/49 执行，OK=5 FAIL=9 SKIP=35 | 40_upstream_tests*.log |
| test_package | `conan create` | **rc=0**，31/31 断言 PASS | 52_conan_create.log |

## 9. 依赖版本

| 依赖 | 版本 | 来源 | 说明 |
|---|---|---|---|
| expat | 2.8.2.1.1 | ohpcd 制品仓（`conan download` rc=0） | 模块 Makefile 唯一外部依赖（`-lexpat`）；产物 `DT_NEEDED` 含 `libexpat.so`（SONAME 为裸名，可重定位）；OHOS sysroot **无** libexpat ⇒ 非系统同名库，按 R26 口径由 conan 依赖链提供运行时 .so |

## 10. 注意事项

- 本模块运行时需宿主先加载 `tm` 模块（`mod_init` 中 `load_tm_api()` 失败即拒绝初始化），属模块自身使用约束
- 消费者运行需把 expat 包的 `lib/` 加入 `LD_LIBRARY_PATH`（musl 无 rpath；conan `conanrun` 环境已自动注入）
- 上游 9 项 FAIL / 35 项 SKIP 的环境缺口（sipp/netcat/id/python3 shebang/FIFO 权限/第三方 DB 驱动模块）与本包产物无关，复现证据见 §6.4
---

## 11. 对话记录

### 对话 #1 — 适配范围确认、上游缺陷定位、环境阻塞处置（2026-10-03）

* **确认上游与范围**：`kamailio-xmpp` 对应上游 kamailio 6.0.6 源码树 `src/modules/xmpp`（模块名 `xmpp`），
  产物 `xmpp.so`；与同族 kamailio-http_async / kamailio-xml / kamailio-db 口径一致（只编模块、不依赖 kamailio 本体包，
  模块由运行时 `loadmodule` 装载）。
* **选源决策**：官网 `kamailio-6.0.6_src.tar.gz` **不含 `test/` 树**（`tar tzf | grep -c '^kamailio-6.0.6/test/'` = 0），
  为满足 R51「上游测试可核验」，改用官方仓库 tag 归档（sha256 `5b8cd435…`，含 `test/unit` 49 个用例，实测 7731 条目）。
* **平台口径决策**：采用 `OS=linux SCTP=0 DEFS_RM="-DHAVE_RESOLV_RES"`（同族 kamailio-db/lua 口径），
  而非 `extra_defs` 注入宏集——原因是 `core/sr_module.c` 对 `SER_FULL_VERSION`/`SER_COMPILE_FLAGS` 做**严格 strcmp**，
  该口径使模块与 OHOS 上 core 完全对齐；已用完整 core 实测装载通过（无 version/flags mismatch）。
* **发现并修复上游缺陷**：`xode_from.c` 的 `_xode_put_expatattribs()` 缺 `atts[i]` 判空 → 任何无属性元素解析即 SIGSEGV；
  以两个独立探针取证（纯 expat 探针 + 模块 SIGSEGV 处理器定位 pc），跨 expat 2.7.3/2.8.2 行为一致，与平台无关，
  故补丁不加平台宏（按 R8 口径在 PR 说明理由）。修复后消费者用例真实解析 stanza，31/31 全通过。
* **上游测试实跑**：`test/unit` **49/49 全量执行**（OK=5 / FAIL=9 / SKIP=35 / TIMEOUT=0），9 项 FAIL 逐个复现取真实首错，
  均为环境能力缺口或上游用例与 6.0.6 工具链漂移，非本包产物缺陷；未修改任何上游用例。
* **环境阻塞与处置**：`finish` 的 W3（本地 CI 关）连续 4 次失败于设备级 inode 耗尽（
  `mktemp: No space left on device` / `OSError: [Errno 28] No space left on device`），
  同轮 `conan-verify` G1/G2/G3 全 PASS、独立 `conan create` rc=0 ×2 → 判定为环境问题而非产物问题；
  经用户确认后回收 83 个陈旧 `ohc-verify-*` 临时校验树（约 336k inode），W3 随后通过。
* **staging 验证**：按同族 kamailio-memcached 先例，把已验收的包产物安装到 staging prefix
  （`/storage/Users/currentUser/tmp/test-install-kamailio-xmpp-6.0.6`），对 **staged 产物**跑同一套
  test_package harness（19 项产物契约 + 12 项消费者用例 = 31/31），结果写入 `.staging-verified`。
---

**编译结束**: 2026-10-03 20:26
**最终状态**: built
