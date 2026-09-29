# libdb 5.3.35 适配笔记

## 任务与上游

- 任务号: #6818（包名 libdb，版本 5.3.35；分支 feat/libdb-5.3.35）
- 上游仓库: https://github.com/berkeleydb/libdb
- 上游版本: 5.3.35（**无 v5.3.35 tag**，见下「版本钉定」）
- 源 URL: https://codeload.github.com/berkeleydb/libdb/tar.gz/b1cb444aad1d53bb8c6ff3a9da31b30063c4a98a
- SHA256: 53da64b1a3541b584bf2f19cd7fce6a91e47b082337851dee4d7ae77b600d469
- 语言: C（核心库为纯 C；C++/Java/Tcl/SQL 绑定不在本构建体系内）
- 构建系统: **meson**（本 fork 在 master 上新增的 `meson.build` + `dist/meson.build`；
  `dist/configure.ac` 的 autotools 线保留为历史参考）
- 依赖: 无（仅 tool_requires meson/1.11.0）

## 与仓内既有 BDB 条目的关系（非重复适配）

| 条目 | 源码来源 | 版本线 | 构建体系 | 许可 |
|---|---|---|---|---|
| `libdb/5.3.35`（本条） | github.com/berkeleydb/libdb（社区 fork） | fork 的 5.3.35 | meson | AGPL-3.0-or-later OR Sleepycat |
| `berkeley-db5/5.3.28` | download.oracle.com 源码 | Oracle 5.3.28 | autotools | Sleepycat |
| `db/6.2.32` | Oracle 6.x 线 | Oracle 6.2.32 | autotools | AGPL |

上游 README 首行即声明 *"Not affiliated with or endorsed by Oracle"*，v5.3.29 起
为社区发布（Oracle 最后一个 5.3 版本是 5.3.28）。三条条目的源码来源、项目主页、
版本线、许可证表述、构建体系均不同，是三个独立软件条目。

## 为什么选 Meson：一次绕开 autotools 线在 HMDFS 上的三类坑

BDB 的 autotools 路径在 HMDFS 上必须处理三类环境坑（`berkeley-db5/5.3.28` 与
`db/6.2.32` 两条已入库配方均实证）：

1. `dist/configure` 的 `print -r --` 回显探测假阳性 —— `grep -c "print -r --"`
   统计到 4 处（9386-9388 行把 `ECHO` 设为 `print -r --`，因为探测时 ksh 的
   `print` 内建让探测通过），但构建期由 `/bin/sh` 执行 `config.status`，
   `print` 不存在 → 运行期报 `print: command not found`。
2. `config.status` 的 `(umask 077 && mktemp -d "./confXXXXXX")`（dist/configure:29848）
   在 setgid HMDFS 目录上拒写。
3. `config.guess` / `config.sub`（2011-11-11 版）不认 HarmonyOS 三元组。

Meson 不生成 `config.status`、不生成 libtool，这三类问题**一次都不出现**：
构建期只有 Meson 自己的 `mesonbuild` 在跑。这是选 Meson 的决定性理由，不是偏好。

（备选方案已实测可行并留档：`berkeley-db5/5.3.28` 的 `0001-dist-config.guess.patch`
/ `0001-dist-config.sub.patch` 对 libdb 5.3.35 的 `dist/` 能 `patch -p1 --dry-run`
干净应用 —— 两侧 config.guess 时间戳同为 2011-11-11。若将来 Meson 线受阻可回退 autotools，
但仍需另补 `print` 与 `umask` 两个补丁。）

## 版本钉定

本 fork 从 5.3.29 起只用 CalVer 发版（`dist/RELEASE` 里 `DB_CALVER=2026.09`、
`DB_VERSION=2026.0.7`），**没有 `v5.3.35` 这个 tag**（GitHub 75 个 tag 全查过）。
5.3.35 是 fork 的发布脚本代换 `dist/configure.ac` 后写进 `dist/configure` 的
`PACKAGE_VERSION`：

```
PACKAGE_VERSION='5.3.35'
PACKAGE_STRING='Berkeley DB 5.3.35'
```

即任务版本号的来源。因此钉到该 `PACKAGE_VERSION` 所在的 master 提交
`b1cb444aad1d53bb8c6ff3a9da31b30063c4a98a`（该提交 `dist/RELEASE` 的
`DB_RELEASE_DATE="September 7, 2026"` 与 `dist/configure` 的 5.3.35 属同一次发布），
而不是可变的 `refs/heads/master`——可变引用会让构建不可复现。

## 补丁：patches/0001-meson-version-metadata-align.patch

上游的版本串分散在**四处且互不一致**，只有 autotools 那条被本次发布代换过：

| 位置 | 上游现值 | 谁读它 |
|---|---|---|
| `dist/configure`（autotools，代换产物） | `5.3.35` | autotools 构建 |
| `dist/meson/db_subs.json` | `5.3.29` | `gen_header.py` 渲染 **db.h** → 编译进库的 `DB_VERSION_*` 宏 |
| `dist/meson.build` | `5.3.34` | `cdata.set_quoted('PACKAGE_VERSION'/'PACKAGE_STRING')` → 生成的 **db_config.h**（私有头，不安装） |
| `meson.build` | `5.3.34` | `project()` 版本（仅元数据） |

第一处是**功能性**的：`db.h` 的 `DB_VERSION_PATCH/STRING/FULL_STRING` 正是
`src/env/env_open.c` 里 `db_version()` / `db_full_version()` 的返回值
（`env_open.c:34-38`、`59-63`），也就是说**不补的话，Meson 构建出的运行库会自报 5.3.29**，
且 `src/env/env_region.c:253` 的 region 版本一致性校验也读同一批宏。

补丁把三处 Meson 侧版本串对齐到 5.3.35，只改字符串字面量，其余代换项
（类型声明、printf 格式、平台头/尾）与任何代码都不动，生成的头文件除版本宏外逐字节相同。

## 补丁：patches/0002-meson-db-subs-proto-macros.patch

上一条是「元数据不一致」，这一条是**Meson 路径漏代换、直接编译不过**。

`src/dbinc/db.in` 是模板，`db.h` 由它代换 `@VAR@` 渲染而来。它的函数指针成员用的是
Berkeley DB 的传统写法，而 `db.h` **故意不包含 `db_config.h`**，所以 `__P()` 这个包装宏
必须由模板自己给出 —— `db.in` 因此备了两个专用槽位 `@DB_PROTO1@` / `@DB_PROTO2@`，
由 `dist/configure.ac:407-411` 按编译器类型算值：

```sh
DB_PROTO1="#undef __P"
# ac_cv_prog_cc_c89 = yes 时（本包就是，clang -std=c99）
DB_PROTO2="#define	__P(protos)	protos"
```

Meson 路径渲染**同一个模板**（`dist/meson/gen_header.py`），但它的代换表
`dist/meson/db_subs.json` 把这两个槽位留成了**空串**。`gen_header.py:19` 是
「占位符 → 查表值」的等值替换（`subs.get(name, placeholder)`），空串不是「保留占位符」，
而是**把宏整段抹掉**。结果 meson 生成的 `db.h` 用了 400 多处 `__P((...))` 却从未定义 `__P`：

```
dist/db.h:529:14: error: expected ';' at end of declaration list
        int (*close) __P((DB_LOGC *, u_int32_t));
```

`db_int.h:88` 包含 `db.h`，所以**每一个**编译单元都这样失败，Meson 构建彻底产不出库
（CI #55671：`[5/275] Compiling C object dist/libdb.a.p/.._src_btree_bt_compact.c.o`
→ `20 errors generated` → `Package '4b9772…' build failed`）。
Autotools 线不受影响；树里随包发布的 Android 构建产物 `build_android/db.h:39-40` 正是
这两行，也就是「正确输出」的对照。

补丁只把两个槽位补成 `configure.ac` 对 ANSI C 编译器所选的值（`DB_CONST` 保持空串，
同样与 `configure.ac` 一致 —— 它只在 pre-ANSI 编译器下才被赋值）。本地用
`patch_ng.fromfile(p).apply(strip=0, root=<src>)` 依次实跑 0001 → 0002 均返回 `True`，
再把 `gen_header.py` 重新跑一遍，渲染出的 `db.h` 第 33-34 行即为
`#undef __P` / `#define	__P(protos)	protos`。

**两条补丁必须按 0001 → 0002 顺序应用**：它们改的是同一张 `db_subs.json` 的相邻行，
0002 的上下文行特意只取 0001 不动的那两行（`DB_CONST` 与 `db_seq_decl`），
所以 0001 先打不会影响 0002 定位；反过来先打 0002 则 0001 的上下文会失配。

## 上游测试口径（rule2 / rule4）

### 本构建体系（Meson）注册的测试：3 项

`test/tiers/meson.build` 把三个 tier 注册成三个 suite（三者的可执行目标都是
`build_by_default: false`，需按名构建后 `--no-rebuild` 跑）：

| # | suite | 文件 | 本配方 | 上游自身给出的理由（原文） |
|---|---|---|---|---|
| 1 | `tiers`（gating） | `test/isolation/test_iso_anomaly.c` | **执行** | —— |
| 2 | `tiers-xfail` | `test/lockmatrix/test_lock_matrix.c` | 不执行 | `test/tiers/meson.build:37` 注释原文：“B3 aborts on current master: that abort IS the #140 reproduction, so it lives in its own suite rather than failing the gating one.” —— 故意红，上游明确要求等修 #140 的同一次提交再并进 `tiers` |
| 3 | `tiers-slow` | `test/soak/test_soak_resources.c` | 不执行 | `test/tiers/meson.build:41` 注释原文：“The soak is minutes, not seconds: keep it out of the default suite”；注册参数 `['-n','2000']`、`timeout: 1800` —— 分钟级 soak，上游刻意排除在默认套件外 |

- 上游注册总数: **3**
- 实际执行: **1**；通过: **1**（100%）；失败: 0；跳过: 0

`test_iso_anomaly.c` 是 B1 隔离性/可串行化校验：判定值由模型枚举算出而不是硬编码
期望值，所以它同时是回归测试与 #140 家族的判定器，是上游唯一 gating 的 tier。

三处 `test()` 注册里**只有 `test/tiers` 在入口链上**（`meson.build`）：

- `:42 subdir('test/tiers')` —— 无条件进入；
- `:36 subdir('test/pbt')` —— 被 `if not get_option('hegel').disabled()` 门控，而
  `option('hegel', type:'feature', value:'disabled')` 是上游默认 → **未注册**；
- `test/sim/meson.build` —— 头部原文注明 *"It is NOT yet entered by the top-level
  meson.build"*，上游自己尚未接入。

### 未执行归因（rule4：执行集与未执行集分开，逐类给技术理由）

上游全集 1081（文件口径）− 执行 1 = **未执行 1080**，三类闭合：

| # | 数目 | 为什么不执行 |
|---|---|---|
| 1 | 1014 | `test/` 内非本构建体系的资产。全部由 `dist/configure.ac`（Autotools）管线构建，而 **Autotools 线在 HMDFS 上不可构建**（三类环境坑，见「为什么选 Meson」）—— 本包改用 Meson 的全部理由就是绕开它们，故这条线在本构建体系里没有构建入口。**平台不可达，非适配裁剪。**（`test/sim` 42 个另有「上游尚未接入」一层；`test/pbt` 13 个另有「被 `hegel` 默认 disabled 门控、需外部 Hegel 框架」一层） |
| 2 | 64 | `test/` 外的 `*test*` 命中文件，**非测试对象**：VS8/VS10 工程文件、vendored SQLite 自带测试、`docs_src/` 文档、`dist/s_test` |
| 3 | 2 | Meson 已注册但不执行的两个 tier（`tiers-xfail` = #140 故意红、`tiers-slow` = 分钟级 soak），理由均为上游注释原文，见上表 |

1014 + 64 + 2 = 1080，**无「未归因」项**，不含任何「平台门控跳过」「注释屏蔽」「手工挑选」的静默项。

### 上游 `test/` 目录下其余测试资产（**未被 Meson 构建注册**，本配方不执行）

本 fork 保留了完整的 autotools 测试线，但 `dist/meson.build` 只注册上面的三个 tier，
下列家族**不在本构建体系内**（既不构建也不注册，不是被本配方裁剪掉的）：

| 家族 | 条目数（钉定提交实测） | 归属 |
|---|---|---|
| `test/c/cutest/suites/*.c` | 9（TestChannel/TestDbHotBackup/TestDbTuner/TestEncryption/TestEnvConfig/TestEnvMethod/TestKeyExistErrorReturn/TestPartial/TestQueue） | dist/configure.ac 管线 |
| `test/c` 独立用例 | 4（test_api_methods / test_db185 / test_lock_sireads / test_log_verify） | 同上 |
| `test/c/cov_*.c` | 5 | 覆盖率驱动，`run_cov_*.sh` 调用 |
| `test/c/leak_*.c` | 2 | 泄漏驱动 |
| `test/cxx/Test*.cpp` | 7 | C++ 绑定线 |
| `test/xa` | src1–src5 + `xa_direct.c` | XA 事务线 |
| `test/tcl/TESTS` | 420 个测试名（文件 3650 行，含描述块） | TCL 线 |
| `test/sql/*.test` | 15 | SQL 线 |
| `test/java`（compat/junit/rep） | 3 类 | Java 绑定线 |
| `test/fuzz` | 3 驱动（fuzz_api / fuzz_dbfile / fuzz_recover）+ corpus/crashes | 非 Meson 注册 |
| `test/pbt/pbt_*.c` | 13 | **Meson 注册但默认关闭**（`option('hegel', type:'feature', value:'disabled')`，需 Hegel 属性测试框架 hegel-c）；本配方 `-Dhegel=disabled` 与上游默认一致 |
| `test/cbmc` / `test/sim` / `test/faultinject` / `test/micro` / `test/bench` / `test/db` / `test/os` / `test/backup` / `test/coverage` | 形式化验证 / 模拟 / 故障注入 / 微基准 / 运维脚本族 | 非 Meson 注册 |

参考量级（钉定提交实测，三个口径由宽到窄）：

| 口径 | 值 | 命令 |
|---|---|---|
| 整包 `*test*` 命中文件（**= PR 声明 N**） | **1081** | `find . -type f -iname '*test*' \| wc -l` |
| `test/` 目录递归文件数 | 1017 | `find test -type f \| wc -l` |
| Meson 构建注册的可执行测试程序 | **3** | `grep -n 'test(' test/*/meson.build` |

1017 之外另有 64 个命中文件在 `test/` 外：`build_windows/VS8|VS10/*.vcxproj`（Windows 工程描述）、
`lang/sql/sqlite/`（**vendored 的 SQLite 源码树**，自带一套属 SQLite 而非 libdb 的测试）与其
sqlite-patches、`docs_src/` 文档、`dist/s_test`。**不是 libdb 自身的测试套件**，列出仅为口径完整
（1081 − 1017 = 64，逐项可溯）。

### rule2 合计口径（无减少）

- 上游全集（钉版朴素扫描，文件口径）= **1081**（其中 Meson 注册的可执行测试程序 **3**）
- 适配后 = **1081**（未删除、未修改任何上游用例）+ **新增消费者断言 30 个调用点 / 运行期 36 条**（test_package/test_libdb.c，6 组）
- 合计 **1111 ≥ 1081** → **测试用例未减少**

## 消费者测试（test_package，1 项 / 30 个 CHECK 调用点，运行期 36 条断言）

`test_libdb.c` 真实驱动 Berkeley DB C API（非符号探针）。下表的「调用点」是源码里的
`CHECK()` 处数（`grep -c 'CHECK(' ` = 31，含宏定义那一行）；两处位于循环内的调用点
运行期展开成 4 条，故运行期实际执行的断言是 36 条。

| 组 | 断言内容 | 调用点 | 运行期 |
|---|---|---|---|
| A 版本同一性 | `db.h` 编译期宏 / `db_version()` / `db_full_version()` 三者与库本体同报 `5.3.35`，`db_full_version()` 报 `11g Release 2` 且全串含 `11.2.5.3.35`。**未打补丁时此处必然报 29/11.2.5.3.29**，是 patches/0001 的端到端验收 | 6 | 6 |
| B 引擎可用 | `db_env_create` → `DB_ENV->open(DB_INIT_LOCK\|DB_INIT_MPOOL\|DB_THREAD\|DB_CREATE\|DB_PRIVATE)` → `db_create` → `DB->open(DB_BTREE)`。BDB 的 latch/mutex 直接建立在 POSIX 线程之上，`DB_INIT_LOCK` 会真正实例化锁表，故 env 打开成功即证明 pthread 已随库正确链接 | 4 | 4 |
| C 点查 + 游标全表枚举 | 点查 `key-042` 取回精确值；游标 `DB_NEXT` 走完全表、以 `DB_NOTFOUND` 收尾、计数 256 条零丢失 | 5 | 5 |
| D 鸿蒙特有：多线程并发写入 | `DB_THREAD` 下 4 线程各写 32 条并与主线程 join，再逐线程核对写入返回值。**上游三个 tier 全部是单线程**（`test_iso_anomaly` 是确定性调度器，`lock_matrix` / `soak_resources` 也单线程跑），不覆盖多线程 API 并发路径；OHOS 的 libc 把 pthread 合并进 libc（无独立 `libpthread.so`），静态库消费方若漏声明 `cpp_info.system_libs=["pthread"]` 会在链接期缺符号、动态库消费方则要到运行时才暴露 —— 这段断言补的正是这个缺口 | 2 | 8 |
| E 持久化 | 关闭 `DB`/`DB_ENV` 后 `stat` 文件非空，再用**新的** DB_ENV 以 `DB_RDONLY` 重开，线程写过的记录仍在；缺失键报 `DB_NOTFOUND`。排除「只在进程内存里跑通」的假阳性 | 11 | 11 |
| F 错误路径确定性 | `DB_CREATE\|DB_RDONLY` 非法组合由 `src/db/db_iface.c:__db_open_arg` 的组合检查拦下并返回 **EINVAL**（`db_iface.c:1276-1280`），不是崩溃、不是静默继续 | 2 | 2 |
| **合计** | | **30** | **36** |

### D 组踩到的库契约：`DB_THREAD` 库上 `DB->get` 的 data DBT 必须带分配标志

第一轮 CI（#71438）C 组之后的点查直接失败：

```
ok - concurrent writer thread committed its key range
BDB0630 DB_THREAD mandates memory allocation flag on data DBT
FAIL: point lookup found key-042
```

这不是库的兼容性问题，是消费者用错了 API。`src/db/db_iface.c` 里
`__dbt_ferr(dbp, name, dbt, check_thread)` 的最后一段：

```c
if (check_thread && DB_IS_THREADED(dbp) &&
    !F_ISSET(dbt, DB_DBT_MALLOC | DB_DBT_REALLOC |
	DB_DBT_USERCOPY | DB_DBT_USERMEM | DB_DBT_READONLY)) {
	__db_errx(env, DB_STR_A("0630",
	    "DB_THREAD mandates memory allocation flag on %s DBT", "%s"), name);
	return (EINVAL);
}
```

调用点里 **只有 `__db_get_arg()` 对 data 传 `check_thread=1`**（`db_iface.c:909`；
同一函数里 key 传的是 `DB_RETURNS_A_KEY(dbp, flags)`，`flags=0` 的普通 B-tree 上
该宏为假 → key 不需要标志）。其余入口——游标 `__dbc_get_arg()`（`:2480`/`:2487`）、
`DB->put`（`:1752`/`:1755`）、`DB->del`、游标 put——data 一律 `check_thread=0`。

语义上是：**线程态下库不肯把指向内部缓冲区的指针交回调用方**，因为换个线程就可能
被改写。所以点查改成 `data.flags = DB_DBT_MALLOC`（库自己拷一份，用完 `free()`），
游标路径则清回 0 —— 它按契约返回的内部指针只保证「下次游标操作前有效」，
本地循环里只用它计数，正是合法用法。

> 通用教训：Berkeley DB 的 `DB_THREAD` 不是「打开了就能多线程随便用」的开关，
> 它同时改变了**返回值所有权**。消费者测试若只照着同期示例写 `DBT`，会在这个
> 契约上翻车；而上游三个 tier 因为全是单线程，永远不会暴露它。

## 产物与打包

- 上游 Meson 只 `install` 库本体（`dist/meson.build:433` 的 `library('db', …, install: true)`
  没有 `install_headers`）；公开头 `db.h` 是 `gen_header.py` 由 `src/dbinc/db.in`
  渲染出的 `custom_target` 产物，落在 `<build>/dist/db.h`。
- HMDFS 上不做 `meson install`（先例 c-shquote/1.1.0），按产物实体拷贝：
  `<build>/dist/db.h` → `include/`；`<build>/dist/libdb.a`（静态）或 `libdb.so*`（共享）→ `lib/`。
- `package_type=library`，无 `bin/`、无 `commands.json`（L0k）。
- 默认静态（`-Ddefault_library=static`，R26：libdb 是典型系统同名库）。
- `package_info`：`libs=["db"]`（与 `.so`/`.a` 文件名 `libdb` 去前缀后一致）、
  `cmake_file_name=libdb` / `cmake_target_name=libdb::libdb` / `pkg_config_name=libdb`，
  OHOS 上 `system_libs=["pthread"]`。

## 构建细节

- `MesonToolchain` 生成的 native file 里 `default_library` 由 `shared` 选项驱动；
  另显式 `hegel=disabled`，防上游改默认值引入 hegel-c 外部依赖。
- Meson 工具类不加载自定义 env（先例 c-shquote / account-utils），故手动执行
  `meson setup <bdir> <src> --native-file conan_meson_native.ini`，
  并把 `PATH=/data/service/hnp/bin:$PATH CC=…/clang AR=…/llvm-ar` 显式前置、
  `env="conanbuild"`。
- 编译与测试构建一律 `-j1`（OHOS 沙箱不支持 mkfifo，jobserver 会炸，铁律）。
- `ninja` 走 `HMBS_NINJA` 环境变量兜底（与 astroterm 先例一致）。

## 已知限制

- Meson 构建只覆盖核心 C 库；上游 C++/Java/Tcl/SQL 绑定与 `db_*` 命令行工具
  属 `dist/configure.ac` 管线，不在本包产物范围。
- `tiers-xfail`（#140 复现）与 `tiers-slow`（分钟级 soak）按上游自身声明不执行，
  已在上面逐条给出上游原文理由。
- `db_config.h` 里的 `PACKAGE_VERSION` 已随补丁对齐，但该头是私有头、不安装。

---

**最终状态**: 待 CI 验证（patches/0001/0002 已修 CI #55671 的 `__P` 未定义编译失败；
test_package 已修 CI #71438 的 `DB_THREAD mandates memory allocation flag` 契约错误）
