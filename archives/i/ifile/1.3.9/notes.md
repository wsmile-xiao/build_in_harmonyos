# ifile 1.3.9 适配笔记（hw-7，2026-09-25，HarmonyOS PC 真机）

任务号 7403 ｜ 分支 `feat/ifile-1.3.9` ｜ 声明语言 C ｜ 构建系统 autotools（autoconf 2.59）
交付形态：命令行工具（`bin/ifile` + `share/man/man1/ifile.1`），上游不安装库与公共头。

## 1. 源码来源判定（R39）

上游作者站点（`people.csail.mit.edu/jrennie/ifile` → `qwone.com/~jason/ifile`）只提供
1.3.8，且为明文 `http://`，R39/PF7 均不可用；`sourceforge`/`github`/`launchpad` 无该
项目发布物。1.3.9 的可用 pristine 来源是发行版档案：

| 来源 | 大小 | sha256 |
|---|---|---|
| `archive.ubuntu.com/.../ifile_1.3.9.orig.tar.gz` | 192718 | `f18f751b…b1ff` |
| `mirrors.mivocloud.com`（登记表给的镜像） | 192718 | `f18f751b…b1ff` |
| `old-releases.ubuntu.com` | 192718 | `f18f751b…b1ff` |

三处字节一致；`.orig` 即未经 Debian 重打包的上游原件（无 `+dfsg`），PF7 黑名单只覆盖
`deb.debian.org`/`snapshot`/`security`/`archive.debian` 四个 Debian 域，`archive.ubuntu.com`
不在列（先例：coco-cpp 20120102）。`conandata.yml` 因此写 archive.ubuntu.com，镜像只用于取件。

版本真实性：1.3.9 解包 65 个文件、1.3.8 为 30 个文件，`Version` 文件与 `configure`
的 `AC_REVISION` 均为 1.3.9，非改名件。

## 2. 四个真实阻塞点与判据

### 2.1 `config.status` 临时目录不可写（E011，判 hit）
`configure` 由 autoconf 2.59 生成，其 `config.status` 用
`(umask 077 && mktemp -d "./confstatXXXXXX")` 建临时目录；HMDFS 上这样建出的目录自身
不可写，报 `./config.status: can't create ./confstatXXXXXX/subs.sed: Permission denied`。
按 E011 把 `umask 077` → `umask 022` 后 `./config.status Makefile` RC=0。
判别记录：曾试过把守卫改成 `test -w "$tmp"`，**无效**——HMDFS 上 `test -w` 对实际写不进
的目录仍返回真，导致 `mkdir` 回退分支永不触发、Makefile 反而不生成；故只改 umask。

### 2.2 `Makefile.in` 里的裸 shell 语句（上游缺陷，打补丁）
第 57–58 行是 `if [ ! $bindir ] ; then …; fi`，GNU make 直接
`Makefile:57: *** missing separator.  Stop.`。这两行是死代码（`bindir`/``mandir` 已由
`@bindir@`/`@mandir@` 赋值），注释掉即可，包 `patches/0002`。**包特有缺陷，不入知识库。**

### 2.3 argp 内联语义（本任务新增知识，`DRAFT-ifile-1.3.9-extern-inline`）
`argp/argp.h` 在 `#ifdef __OPTIMIZE__` 下 `#define ARGP_EI extern inline`，并把
`argp_usage`/`_option_is_short`/`_option_is_end` **定义**写进头文件（`argp-fmtstream.h`
同理给出 8 个 `argp_fmtstream_*`）；上游自己用 `argp-fs-xinl.c` 里
`#define ARGP_FS_EI`（置空）保证**只有一个 TU** 发出实体——这是 GNU89 `extern inline`
的写法。clang 15 默认 C17/GNU11 内联语义下 `extern inline` 会**在每个包含该头的 TU**
发出强符号，最终链接报 20 条 `ld.lld: error: duplicate symbol`。

真机双臂对照（`~/tmp/uc2/hw-7/logs/gnu89-{A,B}.log`）：

| 臂 | CFLAGS | duplicate | `opts.o` 内 `T argp_usage` | `libifile.a` 内 | 产物 |
|---|---|---|---|---|---|
| A | `-O2` | 20 | 1 | 13 | `ifile` 不生成 |
| B | `-O2 -fgnu89-inline` | 0 | 0 | 0（`libargp.a` 2） | `ifile` 125376 B，`--version` → `ifile 1.3.9` |

判重：仓库与本工作区知识库只有 `DRAFT-clang-fno-common-header-globals`
（**变量**暂定定义 + `-fno-common`，解法 extern 化/`-fcommon`）；全库 grep
`extern inline`/`fgnu89`/`C99 inline` 零命中，且 `-fcommon` 对本症状无效
（同符号族、不同根因、不同解法）⇒ 按 §6.2 判 `create`。

### 2.4 System V 信号量被 seccomp 杀（判 hit：`DRAFT-E577`）
`ifile.c` 的 `main()` 第一件事就是 `semget(SEMKEY,…)`/`semop()`，因此**连
`ifile --version` 都以 SIGSYS（rc=159）死掉**，且 `perror` 分支永不触发。真机对照：

| 最小探针 | 结果 |
|---|---|
| 同一 clang 产的 trivial ELF | rc=7 正常运行（证明非签名/非执行门控问题） |
| `semget` / `shmget` / `msgget` | 全部 `Signal 31 (core dumped)` rc=159 |
| `sem_open` + `sem_wait`/`sem_post` | rc=0 正常 |

解法取 E577 同族的"内部锁可剥离"路线：`flock(LOCK_EX)` 锁定 `$HOME/.ifile.lock`。
选 `flock` 而非 POSIX 命名信号量的理由（等效性证明，不是省事）：上游用
`SEM_UNDO` 依赖"进程消失即释放"，`flock` 由内核在关闭 fd 时释放，**崩溃语义与上游一致**；
而 POSIX 命名信号量在 `SIGKILL` 后会永久留在锁住状态，需要额外 `sem_unlink` 恢复，
反而不如 `flock` 等价。锁作用域由"系统级 key"改为"每用户文件"，与 ifile 的数据本就在
`$HOME/.idata` 一致（上游用固定 `SEMKEY` 时跨用户共享本身就是权限隐患）。
**B 判定归属更正（W4 独立审计指出，已采纳）**：症状与"内部实现可剥离 ⇒ 从 SysV 迁走"的路线来自
DRAFT-E577（其 `safety_boundary` 明确"IPC 与公开 API 耦合才走 E584 的披露路线"），但
**本包用的具体解法（`flock`）不在 E577 记载之内**（它给的是 POSIX `shm_open`/`sem_*`）。按 AGENTS
§6.2 判 hit 的第 2 条，"同症状 + 既有条目未写的另一条解法"不得计作 hit，因此本条不占 hit，改为：
把 `flock` 变体（含"崩溃释放等价性"这一取舍依据与实测数据）按 §6.2⑦ 第 1 条写入
`经验文档/B草稿库/DRAFT-PKG-VER-sysv-ipc-flock-mutex-variant.{kv,md}` 通用草稿池，
供后续同族包"取名即用"；本 PR 携带的那一条 B 知识仍是 `DRAFT-ifile-1.3.9-extern-inline`
（一 PR 一知识）。

### 2.5 `ar`/`ranlib` 与安装规则（配方侧处理，不新增知识）
autoconf 2.59 没有 `AC_PROG_AR`，`$(AR)` 落到 make 内置裸名 `ar`（`argp/Makefile` 亦
硬编码裸 `ar`），OHOS 工具链只有 `llvm-ar` ⇒ 建 `<build>/_toolbin/{ar,ranlib}` 软链并
前置 PATH。`make install` 的 `cd $(mandir)/man1 ; rm -f $(MAN_1_PAGES)` 未带 `$(DESTDIR)`，
用常规 `DESTDIR=<pkg>` 安装会让 `cd` 失败后**在构建树里删掉源 man 页**，故改为传绝对
`prefix/bindir/mandir` 且不传 DESTDIR；`INSTALL` 钉成随包自带的可移植 `install-sh -c`
（`AC_PROG_INSTALL` 默认会把宿主绝对路径 `ginstall` 烙进 Makefile，CI worker PATH 未必有）。
`STRIP=` 置空：该规则把 `$(STRIP)` 拼进 install 选项位，且 OHOS MAC 拒绝被 strip 的产物。

### 2.6 `assert()` 里的副作用被 conan 的 `-DNDEBUG` 编译掉（判 hit：经验汇总 §12.11a braa 先例）
`util.c:49` 的 `ifile_sprintf()` 写成 `assert(vsprintf(buf, format, ap) < MAX_STR_LEN - 1)`
——**格式化调用本身在 assert 里**。conan 的 Release 通过 CPPFLAGS 注入 `-DNDEBUG`，
assert 连同 `vsprintf` 一起不编译，`buf` 保持初值 `""`，于是程序构造出的每一条路径
（含 `$HOME/.idata`）都是空串：`Not able to open  for reading!` /
`Not able to open temporary file for writing: `，rc=255。
设备裸编译（我自己在 make 命令行传 `CFLAGS="-O2 -fgnu89-inline"`、不注入 CPPFLAGS）
一切正常，只有 `conan create` 复现 —— 与 §12.11a 记录的"裸环境过、conan create 段错误"
同一机理、同一签名。
修法取该条目的思路但换实现：加 `-UNDEBUG`。§12.11a 原文的"make 命令行显式 `CPPFLAGS=`"
在本包不可用，因为 conan 把 `-I<build>`、`-I<build>/include`、`-I<build>/argp` 也放在
CPPFLAGS 里，整条清空会连带丢头文件路径。**这条实现差异已回写经验汇总 §12.11a**
（本窗只做本地文档修改、不自行 commit 共享文档）。

## 3. 测试账本（§10.1 五维；本节是全包数字的唯一事实源）

**同一套数字在 4 处出现且逐字一致**：本 §3、`manifest.yaml`、`test_package/MANIFEST.yml`、PR 正文两张表。

| 维度 | 值 | 依据 |
|---|---|---|
| `N_static` | **14** | 上游真实注册入口 = `test.sh` 的 8 条断言（`ok 1`…`ok 8`）+ `argp/Makefile.in` 的 `checks` 目标注册的 6 个程序（`argp-ex1.c`…`argp-ex4.c`、`argp-test.c`、`tester.c`） |
| `N_registered` | **8** | ifile 顶层 `Makefile.in` 从不注册 `check`/`test`，只有 `test.sh` 的 8 条进入可执行集合 |
| `N_executed` | **8** | 配方 `build()` 内真实执行 `test-upstream.sh`；对上游脚本只做三类机械改写（`/tmp` 目标重定位、`&>` 改 POSIX 写法、套件内 `make install` 钉住随包 `install-sh`），断言表达式一字未改 |
| 通过 | **4** | `ok 1` 默认 prefix 下的 man 页；`ok 2` `--exec-prefix` 下的 `bin/ifile`；`ok 3` `--bindir` 覆写生效；`ok 8` `--mandir` 覆写生效 |
| 失败（上游陈旧） | **4** | `not ok 4/5/6/7`：上游 `ChangeLog` 记 `ifilter.mh.pl, irefile.mh.pl, knowledge_base.mh.pl, news2mail.pl: removed (added to new mh-ifile)`，这些文件不在 1.3.9 发行件中，且 `install` 目标只装 `ifile` 与 man 页 ⇒ 任何平台均不可通过。保留在分母内、如实计失败，未删用例、未缩分母 |
| 未执行（分类说明） | **6** | argp 的 6 个示例程序属用法演示、无断言与退出码契约，且顶层构建不注册；计入静态分母、不计通过 |
| `N_consumer` | **11** | `test_package/test_ifile.sh` 的 11 项行为断言（1 个驱动脚本、逐项独立判定，清单见 §3.1）；ifile 不安装库与公共头，故按"运行被测二进制并断言行为"的合格形态做 |
| 适配后合计 | **25** | 8 + 6 + 11 ≥ `N_static` 14 ✔ |

通过率申报口径：**执行项 4/8（50%）+ 消费者 11/11（100%）**；分母 14 的逐项来源见上表。

### 3.1 消费者 11 项断言清单

1 版本横幅含 `ifile 1.3.9`；2 `--help` 退出码 0 且含 usage；3 stdin 训练 `spam` 3 封；4 stdin 训练 `work` 3 封；5 `$HOME/.idata` 落盘（实测 301 字节）；6 垃圾类查询首位 `spam`（实测 `spam -28.42 / work -41.64`）；7 工作类查询首位 `work`（实测 `work -27.81 / spam -42.28`）；8 `-u <folder>` 更新路径；9 两进程并发查询均退出码 0（`flock` 迁移的回归测试）；10 `-r` 复位（经 `system()`）后数据库消失；11 man 页安装位置。

输入规模与资源：全部为几百字节小消息，`memcap-run.py --probe` 实测消费者峰值 `peak=4MB`（`MANIFEST.yml` 记 `max_rss_mb: 64`，16 倍余量），构建走轻构建档 `gate.sh 4000` + `build-slot --mem 4000`。


## 4. 待办 / 风险

* `test_package` 在 CI worker 上执行未签名 ELF：本设备实测新链接的 aarch64 ELF 可直接
  执行（trivial 探针 rc=7、`ifile --version` rc=0），故未加签名步骤；若 CI 侧被门控，
  按 E077 补 `llvm-objcopy --remove-section .codesign` + `env -u LD_LIBRARY_PATH
  binary-sign-tool sign … -selfSign 1`。
* commands.json 的 `binary` 取 `true`（对齐 abx/b43-fwcutter 等已合入 CLI 包）；
  该字段口径在登记表里仍标"待裁决"，若统筹改判只需改这一个布尔值。

## 5. 会话记录与收尾

### 对话 #1（hw-7，2026-09-24 17:27 lease → 2026-09-25 13:48 构建收口）

- 需求：任务 7403（平台声明 lang=cpp）适配 ifile 1.3.9 到 HarmonyOS PC。
- 过程与决策：① 先做 W0 依赖预检（零外部硬依赖）与 1.3.9 源码来源判定（无官方 https 件 ⇒
  取 `archive.ubuntu.com` 的 `.orig`，三处镜像 sha256 一致，见第 1 节）；② 影子工程探索
  （`~/tmp/uc2/hw-7/exp3`、`exp4`）依次击破 confstat/E011、`Makefile.in` shell 行、argp 子工程与
  `ar` 缺失；③ 双臂对照坐实 `extern inline` × clang15 C17 内联语义（第 2.3 节，判 create）；
  ④ 用差分探针把 `ifile` 的 SIGSYS 从"未签名被拒"改判为"System V IPC 被 seccomp 杀"
  （第 2.4 节，判 hit DRAFT-E577，并给出 `flock` 相对 POSIX 命名信号量的等效性论证）；
  ⑤ 真机 `conan create` 复现 `-DNDEBUG` 吃掉 `assert(vsprintf(…))` 副作用（第 2.6 节，
  判 hit 经验汇总 §12.11a，实现变体 `-UNDEBUG` 已回写该条）；⑥ 交付出包 + 消费者行为测试。
- 与本工作区规则相关的两点报备：设备共享文件 `~/tmp/uc2/build-slot.sh` 曾带 CRLF 导致槽位脚本
  在 hishell 内刷 `: inaccessible or not found` 死循环，已 `sed -i 's/\r$//'` 幂等修复；
  本机共享私钥 `C:/Users/hongp/.ssh/id_ed25519` 被 20:25 他窗一次 scp 误写覆盖，
  是本轮两次"设备失联"的真因（用户已修复并加只读锁）。
- 补丁集事实源变更说明：`finish` 的 Step1 `refresh-patch --auto` 在无编辑追踪器时走规则兜底、
  会整体替换 `patches/` 并把原内容移入 `.patch-backup-<ts>`（实测发生一次）。已把四处源码修改
  全部落成 `patches/0001…0004`（含把原先写在配方里的 E011 umask 改写迁成补丁），
  并把影子工作树还原为未修改 + 建立追踪器基线（69 文件、零变更），此后 `refresh-patch`
  走"编辑追踪器无变更记录，保留现有补丁"分支，不再回滚补丁集。

编译结束：2026-09-25 13:48（`conan create` 退出码 0，W3 本地 CI 通过）
状态：built（ifile 1.3.9 在 OHOS aarch64 交叉 profile 下构建、安装、消费者测试 11/11 通过）

## 6. 交付提交与证据同源说明

- 本 PR 的交付提交由 `pipeline.py run` 生成（notes-only 追加提交不改 `conandata.yml`/`patches/*`/`conanfile.py` ⇒ **配方 revision 不变**，`conan create` 与 W3 的 100% 通过证据对最终 head 依然同源；若后续需要改这三类文件，W3 与 conan create 日志必须重跑）。
- W3 证据（真机）：`reports/w3-local-ci.log` 末段 `L0_RESULT=pass … L5_RESULT=pass`、`Success: 1 / Failed: 0 / Pass rate: 100.0%`，并含 **L1e 破坏性负向测试**（把 `bin/` 移开后消费者测试即失败 ⇒ 证明测试真的依赖被测二进制，不是空壳）。
- 交付形态：`archives/i/ifile/commands.json` + `archives/i/ifile/1.3.9/{conanfile.py,conandata.yml,manifest.yaml,notes.md,patches/0001-0004,test_package/{conanfile.py,test_ifile.sh,MANIFEST.yml}}` + `knowledge/drafts/DRAFT-ifile-1.3.9-extern-inline.{kv,md}`；`reports/{test-report.md,w3-local-ci.log,conan-verify-report.md,conan-create.log}` 与 `packaging/*.tar.gz`、`.staging-verified` 按框架规则留在本地不入 PR。
- 待补项（不阻塞 CI，提审前补齐）：W4 独立审计报告 `reports/audit-result.json`。已确认审计工具的输入包在本 worktree 上会因分支落后 `upstream/main` 208 提交而把他人归档一并纳入（`--base-branch HEAD~1` 亦然），故按本包 14 个文件为审计范围执行，并把这一基线偏差写进审计结论的边界说明。

---

**编译结束**: 2026-09-25 14:40
**最终状态**: built
