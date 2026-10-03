# lcmaps-plugins-jobrep 1.5.8 — 适配笔记

## 一、任务与目标

| 项 | 值 |
|---|---|
| 包名 | `lcmaps-plugins-jobrep` |
| 版本 | `1.5.8` |
| 上游 | https://wiki.nikhef.nl/grid/LCMAPS |
| 官方源码 | https://software.nikhef.nl/security/lcmaps-plugins-jobrep/lcmaps-plugins-jobrep-1.5.8.tar.gz |
| SHA256 | `a565bc88f12cf8f8cf3bf32889bdff7daa3f5e24885c17a3f21b86fc3a59d57e` |
| 校验 | 官方同名 `.sha256` 清单与本地实算**逐字一致** ✅ |
| 许可证 | Apache-2.0（tarball 内 `LICENSE`） |
| 构建系统 | autotools（tarball 自带预生成 `configure` / `Makefile.in` / `aclocal.m4`，后者已内联 `pkg.m4`） |
| 产物类型 | **LCMAPS 运行时插件**（非普通链接库）：`lib/lcmaps/liblcmaps_jobrep.so` + `lcmaps_jobrep.mod` 软链接 |
| 状态 | `built`（本地 conan create 通过；未 upload） |

## 二、上游依赖背景：为什么先做了 lcmaps

本包 `configure.ac` 的核心依赖检查：

```
AC_CHECK_LIB([crypto], [X509_free])                       # 缺则 have_crypto=no → AC_MSG_FAILURE
PKG_CHECK_MODULES([UNIXODBC], [unixODBC], ..., [-lodbc + sql.h 回退])
AC_LCMAPS_INTERFACE([basic])                              # 缺则 AC_MSG_FAILURE
```

`AC_LCMAPS_INTERFACE([basic])` 是**硬失败**且**制品仓中 `lcmaps` 系列 recipe 数为 0**，
全仓也无任何 `lcmaps` 归档。按 SKILL.md **W0 / R36** 与 **PF4 依赖闸**，
必须先适配并发布依赖本体。故本任务的实际执行顺序为：

1. 先适配 `lcmaps` 1.6.7（见 `archives/l/lcmaps/`，采用 `--disable-gsi-mode`
   without-GSI 风味，已获任务发起人确认接受无 GSI/VOMS 能力）；
2. 再适配本插件 1.5.8。

> ⚠️ **发布顺序**：`lcmaps/1.6.7` 必须先经 PR → CI → release 流水线
> `conan upload` 到制品仓，本插件才能在 CI 中解析依赖（R36 拓扑序）。

## 三、补丁清单（3 个，全部为 POSIX 兼容改法，未引入 `__OHOS__`）

| 补丁 | 目标文件 | 内容 | 依据 |
|---|---|---|---|
| `0001-config-guess-ohos.patch` | `config.guess` | 增加 `*:HarmonyOS:*:*` case 分支，按 `UNAME_MACHINE` 映射出 `aarch64-unknown-linux-ohos` | E007 |
| `0002-config-sub-ohos.patch` | `config.sub` | ① `ohos-linux` 三元组分支 ② `ohos*` OS 白名单 ③ `case $kernel-$os` 校验段的 `linux-ohos*` | E007 |
| `0003-configure-umask.patch` | `configure` | `umask 077` → `umask 022`（2 处） | E011 |

补丁内容与 `archives/l/lcmaps/1.6.7/patches/` 同构（同一组平台适配问题）。
生成方式：`$TMPDIR` 内 pristine（原始解包）vs patched（改动后）逐文件 `diff -u`。
已通过 PF5 自检（新增行无 `__OHOS__`）。

## 四、关键踩坑与修复

### 4.1 E467 —— `AutotoolsDeps` 污染早期 conftest（**本轮最主要的问题**）

**现象**（首轮 `conan create` exit 1）：

```
checking whether the C compiler works... yes
checking for C compiler default output file name... a.out
checking for suffix of executables...
checking whether we are cross compiling... configure: error: cannot run C compiled programs.
```

**根因**（读 `config.log` 定位，知识点 E467）：

```
Error loading shared library libodbc.so.2: (needed by ./conftest)
Error loading shared library liblcmaps_without_gsi.so.0: (needed by ./conftest)
configure:3950: $? = 127
```

`AutotoolsDeps` 会把**整条依赖闭包**写进全局 `LIBS`：

```
export LIBS="-lssl -lcrypto -lodbc -lodbcinst -lodbccr \
  -llcmaps_return_poolindex_without_gsi -llcmaps_gss_assist_gridmap_without_gsi \
  -llcmaps_without_gsi -ldl -lpthread"
```

autoconf 最早的 `AC_PROG_CC`「whether we are cross compiling」探测会沿用该
`LIBS` 去链接 conftest —— 本应只跑一个空 `main()` 的探测，变成需要加载
`-lodbc`/`-llcmaps*`/`-lcrypto` 全链，而 conftest 没有 rpath 指向 Conan 缓存，
运行时加载失败 → rc=127 → configure 在编译阶段就 rc=77 报错。

**修复**（同 `archives/c/cyrus-sasl-gs2/2.1.28` 先例）：

- 不使用 `AutotoolsDeps`；
- 改为只注入 `-I`/`-L`，经 `tc.configure_args` 以 `VAR=value` 形式传
  `CPPFLAGS=` / `LDFLAGS=`（configure 把 `VAR=value` 实参当环境赋值）；
- 早期探测保持空链接；后续 `AC_CHECK_LIB`/头文件检查自带所需库，仍能命中；
- 同时 `os.environ.pop("LD_LIBRARY_PATH", None)`（E505 forbid_2：不让全局
  `LD_LIBRARY_PATH` 泄漏进 configure/make，避免覆盖 DT_RPATH 并污染工具链子进程）。

**为什么 -I/-L-only 就够**：本项目的全部依赖检查只有两类——头文件编译
（`AC_CHECK_HEADERS`、`AC_LCMAPS_INTERFACE` 的直接编译探测）与显式
`AC_CHECK_LIB`（`-lcrypto`、`-lodbc`）；两者都会在测试链接行自带所需库。
且插件上游 `liblcmaps_jobrep_la_LIBADD` 被注释，链接插件本身也不需要库列表。

### 4.2 AC_LCMAPS_INTERFACE 的查找顺序（决定注入方式）

宏内部顺序为：**先直接编译探测 `#include <lcmaps/lcmaps_basic.h>`**
（该头引用 `lcmaps_version.h` 的 `LCMAPS_API_*_VERSION` 宏并做版本比对），
失败才回退 `PKG_CHECK_MODULES` 找 `lcmaps-basic-interface.pc`。

→ 真正起决定作用的是**头文件能被找到**（`-I`），而不是 `.pc` 是否在
`PKG_CONFIG_PATH`。这也解释了为何 `-I/-L` 注入即足够。

### 4.3 test 自身的缺陷（非插件问题）

第二轮 `conan create` 出现 1 项断言失败：

```
[FAIL] plugin_initialize() recognises the --test switch
```

**根因在测试代码**：`plugin_initialize` 的遍历上界是传入的 `argc`，而我把
6 元素的实参数组传成了 `argc=5`，导致尾部的 `--username` 未被扫描、
`jr_db_user` 保持 NULL，函数按前置校验返回 `LCMAPS_MOD_FAIL`。
**修正**：`argc` 改为 6（必须与实参个数一致）。修正后 10/10 通过。

> 记录此条是为了区分「插件缺陷」与「测试缺陷」——前者要改补丁，后者只改测试。

### 4.4 附带脚本 jobrep-admin 的处置（R38）

`utils/Makefile.am` 用 `sbin_SCRIPTS` 安装 `jobrep-admin`（Conan 把 `sbindir`
映射到 `bin/`），首轮产物确实出现 `bin/jobrep-admin`。

该脚本是 `mysql` 客户端的一层包装（`install` / `destroy` / `show` 三个动作，
执行 `share/jobrepository/sql/` 下的建表/删库 SQL）。而 `mysql` 既不是本包
声明依赖、OHOS 上也不存在 —— 发布它等于对外宣告一个**无法运行的命令**。

**处置**：按仓库既有惯例（`unixodbc/2.3.12`、`libiodbc2/3.52.16`、
`canl-c/3.0.0` 均在 `package()` 中删除 `bin/`）移除 `bin/`，`package_info()`
声明空 `bindirs`，**不创建 `commands.json`**（本包是 library 类型，R38）。
SQL schema 文件仍保留在 `share/jobrepository/sql/`，管理员可手工执行。

### 4.5 与 lcmaps 本体的差异点

| 事项 | lcmaps 1.6.7 | 本插件 1.5.8 |
|---|---|---|
| 依赖注入 | 无 Conan 依赖（without-GSI 只需系统 `libdl`） | 需 `-I/-L` 注入三个依赖并去掉 `AutotoolsDeps`（E467） |
| 产物 | 普通共享库 `liblcmaps_without_gsi.so` 等 | LCMAPS 运行时插件 `liblcmaps_jobrep.so` + `.mod` 软链接 |
| 插件符号 | 提供 `lcmaps_log`/`lcmaps_cntArgs` 等 | **引用**上述符号，未定义在 .so 内，由宿主进程解析 |
| `commands.json` | 不需要（无 `bin_PROGRAMS`） | 不需要（附带脚本已移除，保持纯库语义） |

## 五、上游测试清点（R51 第一步）

**结论：上游无自动化测试套件。**

清点证据：
1. `grep -rn "TESTS *=" --include="*.am"` 对全部 5 个 `Makefile.am`
   （顶层 / `src` / `src/jobrep` / `utils` / `doc`）→ **命中 0 处**；
   `check_PROGRAMS` 同样 **0 处**。
2. 源码树中**不存在** `tests/` 或 `test/` 目录。
3. 无自定义 `check-local` / `check-am` 规则；`make check` 因此为空操作。
4. `src/jobrep/jobrep_test.c` 是手工驱动程序，**仅出现在
   `src/jobrep/Makefile.am` 的 `EXTRA_DIST`（源码分发列表）中**，不在任何
   `_SOURCES`、`check_PROGRAMS` 或 `TESTS` 内 —— 故不被任何目标编译、
   `make check` 也不运行。该文件自身也不具自动化测试特征：`main()` 内硬编码
   用户名与 `job_request` 字面量，需 `USE_VOMS_TEST_PROXY` 的 GSI 代理凭证
   （`gssapi.h` / `globus_gss_assist.h`）与可用数据库连接，且无断言框架、
   无期望输出比对、无退出码语义。

按 R51「上游确无测试须附清点证据」如实申报；**不使用空跑 `make check`
制造假执行痕迹**（R52 点名的欺骗行为）。

### 实测运行结果（R51 第二步/第三步）

| 项 | 值 |
|---|---|
| 上游测试总数 N | 0（无自动化测试套件） |
| 实际运行数 N′ | 0 |
| 上游通过率 | 不适用（N=0） |
| 适配补全测试 | 10 个断言（`test_package/test_jobrep.c`），**10/10 通过（100%）** |

## 六、验证记录

```bash
conan create archives/l/lcmaps-plugins-jobrep/1.5.8 \
    -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
```

**结果：exit 0。**（依赖 `lcmaps/1.6.7` 由本地缓存提供，因制品仓尚未发布）

```
lcmaps-plugins-jobrep/1.5.8: Package 'c43d7c6ff0736c006fbe214db8d9a6fb9347a946' created
  [ok]   plugin_initialize() rejects an unknown option (LCMAPS_MOD_FAIL)
  [ok]   plugin_initialize() fails without --dsn (LCMAPS_MOD_FAIL)
  [ok]   plugin_initialize() accepts --dsn/--username (LCMAPS_MOD_SUCCESS)
  [ok]   plugin_initialize() recognises the --test switch
  [ok]   plugin_introspect() returns LCMAPS_MOD_SUCCESS
  [ok]   plugin_introspect() reports 3 arguments (user_dn/px509_chain/job_request)
  [ok]   plugin_introspect() fills the argument pointer
  [ok]   plugin_introspect() first argument is "user_dn"
  [ok]   plugin_introspect() third argument is "job_request"
  [ok]   plugin_terminate() returns LCMAPS_MOD_SUCCESS
test lcmaps-plugins-jobrep 1.5.8: OK (10/10 assertions passed)
```

产物完整性（包目录实测）：

| 路径 | 说明 |
|---|---|
| `lib/lcmaps/liblcmaps_jobrep.so` | 插件本体（`-avoid-version`，无 SONAME 版本后缀） |
| `lib/lcmaps/lcmaps_jobrep.mod` | LCMAPS 查找插件用的软链接 |
| `share/jobrepository/sql/jobrep-create-basic.sql` | 建库建表脚本 |
| `share/jobrepository/sql/jobrep-drop-total-database.sql` | 删库脚本 |
| `share/man/man8/lcmaps_jobrep.mod.8`、`jobrep-admin.8` | 手册页 |
| `share/doc/lcmaps-plugins-jobrep-1.5.8/` | LICENSE / AUTHORS / BUGS / 安装说明 / 数据库设计 PDF |

**R26 系统同名库检查**：`liblcmaps_jobrep.so` 与 `/lib`、`/lib64` 下无同名冲突。

## 七、待办 / 后续

1. **前置依赖**：`lcmaps/1.6.7` 须先合并并 upload 到制品仓（本仓库
   `archives/l/lcmaps/`），本插件方可进 CI。
2. 本包需经 PR → CI → release 流水线 `conan upload` 发布。
3. `plugin_run` / `plugin_verify` 的真实数据库路径未纳入离线消费者测试
   （需可用 ODBC 数据源 + X.509 凭证链）；如需端到端验证，须在具备
   MariaDB/MySQL 与凭证的环境中另行开展。
4. 若未来补齐 GSI 链并改用 `--enable-gsi-mode` 的 lcmaps，本插件无需改动
   （其 `AC_LCMAPS_INTERFACE([basic])` 对两种风味均通过）。
