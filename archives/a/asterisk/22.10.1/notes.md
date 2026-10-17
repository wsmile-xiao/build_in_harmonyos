# asterisk 22.10.1 HarmonyOS 制品适配笔记

## 适配主线

本 PR（`feat/asterisk-22.10.1`，#9608）的目标是 Asterisk 22.10.1 的 Conan 配方、
HarmonyOS 编译、运行时和模块交付适配，不承担上游 full-PBX 测试套件的整体修复。
`test_poll`、`test_capture`、voicemail/JSON 测试夹具以及 full-PBX runner 的修复已从
本 PR 主线剥离，分别作为独立测试适配工作跟踪。724 条是上游测试库存参考值，不是
本 PR 的功能验收指标。

- 构建系统：Autotools（in-source 构建）+ Conan 2.x
- 目标：HarmonyOS/OHOS，aarch64，clang/clang++ 15.0.4
- issue：TBD（当前项目文件和会话上下文未找到明确编号）
- 当前主线补丁数：20 个（0001~0012、0015、0016、0023、0025~0027、0031、0034）
- 本次真机验证对应修复提交：`2122a08895`；已在鸿蒙 aarch64 真机完成 Conan 构建和 `test_package`

## 编译步骤

1. 使用显式三元组和本地依赖前缀：
   ```bash
   ./configure --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu \
     --with-ldap=$DEFAULT_PREFIX --without-pjproject --without-x11 --without-gtk2
   make -j4
   make install DESTDIR=$TEST_PREFIX INSTALL="$PWD/install-sh -c"
   ```
2. Conan 配方在 configure 前准备 BlocksRuntime 和 ohosshim 垫片，使用 in-source
   构建，安装阶段跳过无法在沙箱下载的 sounds，并将 NEEDED 闭包依赖捆绑到包内
   `lib/` 后执行 ELF 签名。
3. `test_package` 检查 `sbin/asterisk`、LDAP 模块，并在可运行目标执行
   `asterisk -V`。

## 上游 in-tree 测试用例的执行前提

Asterisk 22.10.1 源码内自带上游测试框架用例：`tests/test_*.c` 共 90 余个测试模块，
注册出 `/main/...`、`/res/...`、`/funcs/...` 等**上游 in-tree 用例**（另有
`main/`、`res/`、`funcs/`、`apps/`、`bridges/` 内的模块级用例）。这些模块每个都声明
`<depend>TEST_FRAMEWORK</depend>`，未打开 `TEST_FRAMEWORK` 与 `MENUSELECT_TESTS`
时不会编译进包，设备上也就没有任何上游用例可执行。

配方为此提供 `with_test_framework` 选项（默认 `false`，交付制品模块集合不变）：

```bash
conan create archives/a/asterisk/22.10.1 -o asterisk/*:with_test_framework=True
```

打开后配方按上游 CI（`tests/CI/buildAsterisk.sh`）的顺序执行
`make menuselect.makeopts` → 逐个 `menuselect --enable DONT_OPTIMIZE
--enable TEST_FRAMEWORK` → `--disable COMPILE_DOUBLE` →
`--enable-category MENUSELECT_TESTS` → `--check-deps`，随后才进入主构建。

**不要**在 OHOS 上同时打开上游 CI 的 `MALLOC_DEBUG` 与 `DO_CRASH`：设备实测这样
构建出的二进制会在模块加载阶段死锁——控制台停在 `Asterisk Dynamic Loader
Starting:`，`core waitfullybooted` 永不返回、`module show` 因 loader 持锁而阻塞、
用例注册数停在 8（仅内置用例）；同一台设备上未启用这两个选项的构建可以正常输出
`Asterisk Ready.` 并注册全部可加载用例。因此测试构建的 cflags 组合与已验证基线
保持一致（`DONT_OPTIMIZE TEST_FRAMEWORK OPTIONAL_API BUILD_NATIVE`）。

两个必须注意的机制（否则测试模块根本不会被编译）：

- `TEST_FRAMEWORK` 成员定义在 `build_tools/cflags-devmode.xml`，而该文件只在
  `AST_DEVMODE=yes` 时才被追加进 `menuselect-tree`（顶层 `Makefile` 的
  `menuselect-tree` 规则）。因此测试构建必须在 configure 阶段加
  `--enable-dev-mode`；同时 dev-mode 会把 `-Werror`、`-Wunused`、`-Wundef`
  等严格告警加入 `_ASTCFLAGS`（`Makefile` L211），在 OHOS/clang 上无法整树通过
  （例如 `tests/test_scope_trace.c` 在 dev-mode 下走 GCC 嵌套函数的
  `SCOPE_TRACE`，clang 直接报 `illegal storage class on function`）。所以
  menuselect 选择完成后、主构建之前，配方把 `AST_DEVMODE` 从 `makeopts` 和
  `include/asterisk/buildopts.h` 中去掉，并在 make 命令行再次用
  `AST_DEVMODE= DISABLE_XMLDOC=yes` 兜底；`logger.h` 在非 dev-mode 下会给出
  `SCOPE_*` 的 ast_debug 回退定义，测试模块仍可编译和注册。
- `menuselect --enable` 只接受一个成员（`menuselect.c` 的 long_options 为
  `required_argument`），必须重复给出 `--enable X --enable Y`；写成
  `--enable X Y Z` 只会启用第一个成员。

上游官方 full-PBX 测试套件（`https://github.com/asterisk/testsuite`）是独立于
源码包的 Python 测试框架，需要运行中的完整 PBX、测试配置、dialplan、声音资源和
模拟信道，与上述 in-tree 用例是两套不同的库存，不能混算分母。

## 主线问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | uname 返回 HongMeng/HarmonyOS | 显式指定 aarch64 build/host 三元组 |
| 2 | BlocksRuntime is required for clang | OHOS 无预编译 BlocksRuntime | 配方内编译垫片库并在 configure 前提供 |
| 3 | pthread_cancel/testcancel/setcancelstate 未定义 | musl 不实现 POSIX 线程取消族 | 链入 libohosshim 存根库（E085） |
| 4 | `sched.h: expected ';'` | ASTMM 宏污染 musl 系统头文件 | 受影响生成源码和 parser 源使用 ASTMM_IGNORE |
| 5 | dns.c 找不到 `_res` | musl 不暴露 glibc resolver 全局状态 | 非 NINIT 路径返回空 nameserver 容器 |
| 6 | db1-ast 缺少 `__P`/`__BEGIN_DECLS` | musl 无 glibc cdefs 宏 | 增加受保护的回退定义 |
| 7 | menuselect 找不到 libxml/parser.h | Conan 头文件位于 include/libxml2 | 通过 OHOS_XML2_INCDIR 注入路径 |
| 8 | menuselect 运行时找不到 xmlStrcmp | 依赖库目录不在加载器搜索路径 | 通过构建变量和 makeopts 写入 RUNPATH |
| 9 | third-party/versions.mak 不存在 | out-of-source 构建破坏源码相对路径 | 使用 in-source 构建 |
| 10 | sounds 安装下载失败 | busybox wget 不支持上游 `continue` 下载流程 | 增加 DISABLE_SOUNDS 并在 package() 使用 |
| 11 | install-sh 不存在 | 子目录中的相对 INSTALL 路径失效 | 使用绝对 install-sh 路径 |
| 12 | test_package relocating symbol not found | 依赖散落在缓存且未签名 | 捆绑 NEEDED 闭包并全量 ELF 签名 |
| 13 | stdtime zoneinfo 路径不可部署 | 编译期 TZDIR 不能表达设备部署路径 | 非空 TZDIR 在运行时覆盖，未设置时回退默认值 |
| 14 | REBUILD_PARSERS 下 parser 生成失败 | ast_expr2.y 仍使用 ASTMM_REDIRECT | 0016 将生成器切换为 ASTMM_IGNORE |
| 15 | HarmonyOS 默认路径锁不兼容 | HMDFS 不支持 pathname 硬链接锁 | OHOS 配方设置 AST_LOCK_TYPE_DEFAULT=AST_LOCK_TYPE_FLOCK |
| 16 | 可加载模块缺少 OHOS 运行库 | BlocksRuntime、pthread shim、uuid 未形成模块依赖闭包 | 主程序和模块显式链接 OHOS_MODULE_LIBS |
| 17 | 控制 socket 路径不可用 | HMDFS 不支持 pathname AF_UNIX 控制 socket | 配方设置 AST_USE_ABSTRACT_SOCKET=1，使用 abstract AF_UNIX |
| 18 | Asterisk 内部 PATH_MAX 过小 | 目标头文件提供的 PATH_MAX 小于 4096 | 按 PATH_MAX 能力条件提升内部路径缓冲上限 |
| 19 | 可加载模块无法解析 Blocks ABI | 主程序导出脚本未导出相关符号 | 增加三个 OHOS BlocksRuntime 导出项 |
| 20 | ELF 依赖扫描找不到工具链运行库 | 真机 clang 位于用户可写前缀，旧配方只查固定 SDK 目录 | 从选定 clang 的绝对路径动态加入 runtime/sysroot 候选目录 |
| 21 | 真机启动停在 `Asterisk Dynamic Loader Starting:`，`core waitfullybooted` 永不返回、`module show` 阻塞、用例只注册内置的 8 条 | musl 没有 `PTHREAD_RECURSIVE_MUTEX_INITIALIZER_NP`，`AST_MUTEX_INIT_VALUE` 退化为 `PTHREAD_MUTEX_INITIALIZER`（普通互斥量）；而 `load_modules()` 先锁 `module_list`，`loader_builtin_init()` 内的 `ast_module_register()` 再次加锁，非递归互斥量导致同线程自死锁 | `0034` 增加 `AST_USE_MUTEX_CONSTRUCTOR_INIT` 能力开关，配方注入后 `lock.h` 走构造函数初始化，静态互斥量由 `ast_mutex_init()` 按 `PTHREAD_MUTEX_RECURSIVE` 建立 |

## 审查修复

- `0007` 的无 resolver 状态路径直接返回空 nameserver 容器，不再执行无配对的
  `ast_mutex_unlock(&res_lock)`。
- `0023`、`0026` 的平台选择改由 `AST_LOCK_TYPE_DEFAULT` 和
  `AST_USE_ABSTRACT_SOCKET` 配置宏控制；OHOS 配方通过 `extra_cflags` 注入，默认
  行为仍保持跨平台兼容。
- `0027` 改为依据 `PATH_MAX < 4096` 的能力条件，不在补丁中判断厂商平台宏。

## 源码修改

主线包含 20 个补丁：`0001`~`0012` 为构建、musl 和依赖适配；`0015` 为运行时
TZDIR；`0016` 为 parser 生成路径；`0023`、`0025`~`0027`、`0031` 和 `0034` 为锁、
模块运行库、控制 socket、路径上限、模块符号导出和互斥量初始化适配。纯测试夹具和测试断言补丁未纳入
本 PR，以保持制品适配与 full-PBX 测试修复的责任边界。

另有配方内动态处理（非补丁）：E114 umask 077→022（configure/menuselect 两处）、
install-sh 绝对路径覆盖、依赖闭包打包和 ELF 签名。

## 依赖版本

- openldap/2.6.7（前置产出，PR #6070）
- libedit/20240808、uuid/2.40.1、jansson/2.15.1、libxml2/2.15.3、sqlite3/3.49.1

## 验证结果

宿主侧已验证配方元数据、`commands.json`、知识草稿预审、主线补丁可应用检查、
`python -m py_compile` 和 `git diff --check`。官方 CI #46520 的失败点是 Conan
应用 `0016` 时 hunk 行号不匹配，已将行号从 `-10` 修正为 `-12`；后续修订还补充
了真机可用的 `llvm-readobj` 回退以及 clang runtime/sysroot 动态候选路径。

真机单包 runner（当前提交 `2122a08895`）：

```text
run_dir=/storage/Users/currentUser/ohos-test-runs/codex-22.10.1-asterisk-22.10.1-fix-d66aeaef78-conan-20260914-162720-17126
command=zsh ci/conan/build_and_test.sh archives/a/asterisk/22.10.1
runner=rc=0
conan_create=PASS; test_package=PASS; asterisk -V -> Asterisk 22.10.1
L0=pass; L1=pass; L2=skip(no bin/); L4=warn(dangerous functions); L5=fail(soname_gate_failed)
```

L5 不能作为本次 Conan 构建失败依据：该 runner 固定执行 `readelf -d`，但设备没有
`readelf`，只有 `llvm-readobj --dynamic-table`，因此 runner 将 6 个文件统一报为缺少
SONAME。用设备实际可用工具复核后，`libasteriskssl.so`、`libc++_shared.so` 和
`libz.so` 均有 `DT_SONAME`；`libBlocksRuntime.so`、`libjansson.so` 和 `libohosshim.so`
确实没有 `DT_SONAME`，这属于需要另行处理的包质量问题。共享 runner 的 ELF 工具回退
仍属于基础设施问题，不能在本 PR 修改 `ci/`。旧的
`libc++_shared.so`、`libz.so`、`libtinfo.so.6` 候选路径告警已消失。

## 上游 in-tree 用例真机执行结果（提交 `a6d20a0ac9`）

同一配方加 `-o asterisk/*:with_test_framework=True` 构建的制品，在 HarmonyOS
aarch64 真机启动 PBX 后按类别隔离执行，逐例结果与失败分类见
`reports/upstream-in-tree-test-results.md`、`reports/upstream-in-tree-test-failure-matrix.md`
和逐例清单 `reports/upstream-in-tree-test-case-results.tsv`。

| 指标 | 数量 |
|---|---:|
| 上游源码静态清点（`AST_TEST_DEFINE`） | 712（116 文件） |
| 设备注册用例（`test show registered all`） | 599 |
| 实际产生逐例结果的用例 | 572 |
| PASS | 560 |
| FAIL | 12 |
| SKIP / NOT RUN | 0 / 0 |
| 通过率（已执行口径） | 560/572 = 97.90% |
| 通过率（设备注册口径） | 560/599 = 93.49% |

12 条 FAIL 全部有逐例 XML 证据，按根因分为三类：运行夹具（`/tmp` 只读、声音与
voicemail 配置缺失）8 条、平台工具链输出契约（`test_capture` 三条）3 条、平台
poll 语义差异 1 条。三类都不属于本 PR 的配方缺陷，需要按"一库一 PR"另行处理。

真机证据路径：

```text
run 目录  /storage/Users/currentUser/ohos-test-runs/codex-22.10.1-asterisk-22.10.1-a6d20a0ac9-full-20260926-235507-42616
          /storage/Users/currentUser/ohos-test-runs/codex-22.10.1-asterisk-22.10.1-a6d20a0ac9-full2-20260927-000740-52156
逐类证据  .../testfw/categories/（88 个类别 XML + 控制台日志）
报告      .../testfw/reports/（registered-all.log、case-results.tsv、summary.md、driver.log）
```

未达 724 的部分按四类原因说明（未编译模块、`MENUSELECT_TESTS` 依赖不满足的 8 个
测试模块、上游 `DO_NOT_RUN`/框架自测共 5 条保护用例、定宽注册表的名称截断），
不使用"申请豁免"口径。

最新官方重跑 CI #46946 未进入 checkout 或 Conan 阶段：设备侧
`/data/service/hnp/bin/git` 缺少 `libz.so`，cleanup 又因设备侧缺少
`ci/conan/cleanup.sh` 退出。该结果属于 runner/设备环境故障，不改变本 PR 的本机
补丁链验证结论。

## 路径 C（高难度挑战）候选申请说明

本适配同时提交**路径 C 候选申请**（仅申请纳入高难候选清单，不构成已得分声明；最终档位与分值以赛事方评审委员会专项终审为准）。四条判定逐项如实判断：

1. **`HD1_PRIVATE_OS_INTERFACES: matched=partial`**
   OHOS/HMDFS 暴露的是**平台私有语义限制**而非接口缺失：pathname AF_UNIX 控制套接字不可用（HMDFS）、
   pathname 硬链接锁不可用（HMDFS）、`/tmp` 只读、musl 未实现 POSIX 线程取消族（`pthread_cancel`/
   `pthread_testcancel`/`pthread_setcancelstate`）与 glibc `_res` 全局解析器状态。
   Asterisk 有部分可移植抽象，但这些限制无法由现有抽象覆盖，必须逐项适配。

2. **`HD2_PRIVATE_TOOLCHAIN: matched=true`（主证据）**
   现有知识库无先例的构建/运行时机制共 5 类：
   - **musl 无递归静态互斥量初始值**（无 `PTHREAD_RECURSIVE_MUTEX_INITIALIZER_NP`）→
     静态互斥量退化为普通互斥量 → `load_modules()` 与 `ast_module_register()` 对 `module_list`
     同线程二次加锁自死锁（真机启动停在 `Asterisk Dynamic Loader Starting:`，用例只注册内置 8 条）；
     以能力开关 `AST_USE_MUTEX_CONSTRUCTOR_INIT` 走构造函数初始化修复（补丁 `0034`）。
   - clang `-fblocks` 需自建 BlocksRuntime 垫片；musl 需 `libohosshim` 线程取消存根。
   - ASTMM 陷阱宏污染 musl 系统头（`sched.h`）→ 生成源码与 parser 改 `ASTMM_IGNORE`。
   - `menuselect --enable` 只接受单成员参数、`TEST_FRAMEWORK` 成员仅在 dev-mode 的 menuselect 树中定义
     （测试构建的隐藏前提）。
   - menuselect 与主构建的 libxml2 运行时依赖、in-source Autotools 约束、绝对 `install-sh`。

3. **`HD3_COMPLEX_ARCHITECTURE: matched=partial`**
   338 个可加载模块的模块化运行时、模块 ABI/符号导出闭环（BlocksRuntime ABI 导出）、
   taskprocessor/stasis 多线程调度；本库为开源软件，无闭源二进制，不认领闭源条件。

4. **`HD4_LARGE_DEPENDENCY_TEST_COST: matched=true`（主证据）**
   6 个 Conan 依赖（openldap/libedit/uuid/jansson/libxml2/sqlite3）、338 个模块、87 个测试模块；
   上游用例必须先打开 `TEST_FRAMEWORK` 才存在，执行需真实启动 PBX 并做 88 个类别隔离执行，
   本轮实测 599 条注册、572 条逐例结果（含 12 条失败逐条根因）。

结论：以 **HD2（主）+ HD4（主）** 申请路径 C 候选，HD1/HD3 标注 partial；最终以评审为准。

## 下一步

1. 为缺少 `DT_SONAME` 的 3 个包内共享库另行评估修复方案，并保持与本 PR 的责任边界。
2. 由独立基础设施 issue/分支/PR 将 runner 的 `readelf -d` 改为按能力选择
   `llvm-readelf`、`readelf` 或 `llvm-readobj`。
3. 剩余 12 条 FAIL 按 `reports/upstream-in-tree-test-failure-matrix.md` 的分类，
   由测试适配/内核行为评估类工作另行跟踪；若要提高 724 分母覆盖率，需要另开
   "打开 pjproject 等依赖以编译更多测试模块"的适配工作。
4. 路径 C 候选申请：按平台流程提交 `【高难度挑战】` 申请（任务卡 `contrib-14352`），
   等待评审委员会专项终审结论。
