# socklog 2.1.2 适配笔记

- **适配路径**：A（上游 makefile 直译，零源码补丁）
- **使用知识库**：是 —— `knowledge/drafts/DRAFT-cdb-20251021-djbware-cross-safe-adaptation.md`
  第 36 行「conf-\* 首行注入」与 `knowledge/drafts/DRAFT-7324-bglibs-djb-two-stage-cross-build.md`
  第 21/31 行「覆写 conf-cc/conf-ld 第一行」；AF_UNIX 落点面命中
  `经验文档/B草稿库/DRAFT-PKG-VER-hmdfs-refuses-unix-path-bind-hmfs-sandbox-base-allows.md`（⚠ **仓外池件**：该路径属规则工作区、不在代码仓内，不随本 PR 出仓；其全部判据读数已抄进本 notes「失败归因」小节的逐落点表与两道正对照，本 PR 以该表为准）
- **知识库扩展**：本棒两条候选机制均**对得上既有条目行号**（见「候选机制台账」），无新增机制自判；B 档位终判归主理
- **关联 Issue**：本棒未建 Issue（不判档位、不占知识位）

## 判决（三一致）

| 项 | 值 | 出处 |
|---|---|---|
| 文字 | `G1: PASS` `G2: PASS` `G3: PASS` `G4: PASS` `L2/L4/L5: PASS` | `archives/s/socklog/2.1.2/reports/conan-verify-report.md` |
| 判决行 | `**Verdict**: PASS` | 同上 |
| 退出码 | `VERIFY_RC=0` | `~/tmp/uc2/z64-socklog/v3-runner.log` |
| 完成标记 | `✅ 配方验证通过: socklog 2.1.2` | `~/tmp/uc2/z64-socklog/verify-v3.log` |

⚠ **G4 与 L2/L4/L5 是"跳过形"的 PASS，不是实证**：报告正文分别是
`⚠️ 无法找到程序包 ID`（G4）与 `⏭️ 跳过（无 cache 路径）`（L2/L4/L5）。
⇒ 产物完整性的**一手证据改由两处提供**：
① 直接列包目录（`bin/` 5 个 + `share/man/man8/` 3 个 + `share/man/man1/` 2 个 + `licenses/COPYING`）；
② `test_package` 在 G2 的 `conan create` 内实跑 **10/10 断言通过**，
见 `archives/s/socklog/2.1.2/reports/conan-create.log` 第 92–117 行
（`socklog test_package: passed=10 failed=0 total=10`）。
判绿未拿"图标"当依据（`✅ G2: FAIL` 这类图标与文字相反的形态在本包 v1/v2 实拍出现过两次）。

## 编译环境

- 构建主机：B 机（HarmonyOS aarch64）
- 构建系统：makefile（smarden/djbware 风格 `conf-cc`/`conf-ld`，**无 configure 脚本**）
- 编译器：`/data/service/hnp/bin/clang`（Conan profile `tools.build:compiler_executables` 的 `c` 键）
- worktree：`~/qzy/主理-64-socklog-2.1.2`，分支 `feat/socklog-2.1.2`，基线 `48d9cee684`
- CONAN_HOME：`$HOME/tmp/ch/home-socklog-64`
- 构建槽：一律 `gate.sh` → `build-slot.sh --kind short --wait 1800 --mem 2500`（每轮 `GATE_PASS` + `SLOT_OK`）

## 定源（版本串硬纠）

登记表候选行给的是 **Debian 池址 `socklog_2.1.0+repack.orig.tar.gz`**，与本任务 **2.1.2** 版本串不一致，
且 PF7 拉黑 pool/deb 址与 Debian 重打包源。本棒改用官方上游直链并自算哈希：

| 项 | 值 |
|---|---|
| URL | `https://smarden.org/socklog/socklog-2.1.2.tar.gz` |
| HEAD 实测 | `HTTP/1.1 200 OK`，`Content-Length: 60743` |
| 实落盘大小 | 60743 B（与 Content-Length 等值） |
| sha256（自算，conandata 声明同值） | `7bc7a3f9e8e15a7e791281c05741a4c0cf0de86e74870fd2c6f4d7e7942b95e6` |
| 证据日志 | `~/tmp/uc2/z64-socklog/s1-source-01.log` |

三向同哈希成立（HEAD 200+Content-Length ／ 实物落盘 60743B ／ conandata 声明＝实物）。
任务版本 = Conan 版本 = 归档目录 = 分支版本 = **2.1.2**，未归一化、未张冠李戴到 2.1.0+repack。
`conandata.yml` 全程只有官方址单值，**未出现任何镜像前缀**（verify v1/v2/v3 后逐轮回读均为原值；
`archives/l/libXext/*` 两枚脏件是 HMDFS 双 case 幻影，与本包无关，未 add）。

## 这包实际是什么（对候选行假设的证实）

候选行的假设**成立**，已读原文逐条证实：

1. **不靠 configure**：`configure/configure.ac/CMakeLists.txt/meson.build` 全部 absent。
   探测由 `src/Makefile` 的 `sysdeps` 目标 + `src/choose.sh` 跑 `try*.c` 完成。
2. **参数写死在小脚本里**：`src/print-cc.sh` 与 `src/print-ld.sh` 用
   `cc="$(head -n1 conf-cc)"` / `ld="$(head -n1 conf-ld)"` 取**第一行**，
   展开成生成脚本里的整条 `exec` 命令行（实拍生成物：
   `exec /data/service/hnp/bin/clang -O2 -Wall -c ${1+"$@"}`）。
   ⇒ **一等注入点就是这两个文件的第一行**，不必碰上游源码。
3. tarball 根不是构建目录：`admin/socklog-2.1.2/{src,doc,man,package}`，可构建树在 `src/`。
4. 文件普查（实测，与候选行略有出入）：`.c` **93** 个、`.h` 29 个、`.sh` 6 个、`Makefile` 1 个，共 195 个文件。
   候选行写「c/cpp 96 个」——**计数偏大 3，不影响定性**。
5. `socklog` 有 `-V`（打印写死的 `$Id: <blob-sha> $` 再打 usage、exit 1），**没有 `--version`**。

## 关键适配点

| # | 问题 | 根因（一手证据） | 解决方案 |
|---|------|------------------|----------|
| 1 | 默认 `conf-cc`=`gcc -O2 -Wall`、`conf-ld`=`gcc -s` 不可用 | 设备 `command -v gcc` → **MISSING**（只有 clang）；`~/tmp/uc2/z64-socklog/s3-scripts-01.log` | `build()` 从 Conan conf 取 `c` 键，`save()` 覆写两文件第一行。⛔ 不改上游源码、⛔ 不裸用 `$CC`（R33） |
| 2 | `makelib` 硬编码 `ar cr` + `ranlib`，**无 `conf-ar` 入口** | `src/print-ar.sh` 直接 `echo 'ar cr "$main"'`；`case $(cat systype)` 落 `*)` ⇒ 会跑 ranlib | profile `[buildenv]` 已注入 `/data/service/hnp/bin`，`ar`/`ranlib`/`strip` 均在 PATH，实测 `unix.a`(82300B)/`byte.a`(15336B)/`time.a`(15084B) 正常产出，**无需补丁**（注意：与 runit 不同，本包**不要**写 `conf-ar`） |
| 3 | `find-systype.sh` 的 `uname -s` 在本机不是 `Linux` | 实测 `uname -s`=**`HarmonyOS`**、`uname -r`=`HongMeng Kernel 1.12.0` ⇒ 走 `case` 的 `*)` 默认分支，产出 `harmonyos-hongmeng.kernel.1.12.0-…-aarch64-:-` | **无需处置**：该脚本**无 CPU/OS 白名单**，默认分支兜得住，`systype` 只影响 `print-ar.sh` 的 ranlib 判定。⛔ 未把 HarmonyOS 归一化成 Linux |
| 4 | 9 个 sysdeps 行为探测 | 全部落**正面分支**：`+dirent +waitpid +sigaction +sigprocmask +sysselect +ulong64 +poll +mkfifo +flock`；`~/tmp/uc2/z64-socklog/p1-run-01.log` | OHOS libc 全具备 ⇒ **零探测失败、零补丁** |
| 5 | HMDFS 上 GNU make jobserver 需 `mkfifo` | 同作者先例 runit 2.3.1 notes 问题 #2 | 固定 `make -j1` |

## 已试过但**不采用**的方案

- **`-fcommon`**：`knowledge/graph/E491.kv` 对本类明记 `forbid_1_pattern: -fcommon`。
  且本包实测不需要——`socklog.c`/`sgetopt.c`/`subgetopt.c`/`sig.c` 里的 `int x = 0;`
  都是带初始化的**定义**（非 tentative definition），跨文件不重名，`-fno-common` 下不报 multiple definition。
- **改 `src/Makefile` 或 `print-*.sh` 注入编译器**：属"改上游生成器"，且 `conf-cc`/`conf-ld`
  就是上游留的一等注入点，绕开它反而破坏可复现性。
- **`test_package` 用 `VirtualRunEnv` + PATH 查找**（**verify v2 的真实死因**）：
  本平台生成的 `conanrunenv-release-armv8.sh` 里 `for v in` 列表为**空**，不导出 PATH ⇒
  5 个命令 `command -v` 全部 not found，`test()` rc=1、G2 FAIL。
  探针实测 `dependencies["socklog"].cpp_info.bindirs[0]` **本身就是绝对路径**，
  遂改为直接按绝对 bindir 断言（`p2-depprobe.sh`，另见「提交 d87d1f9230」）。

## 三笔真实失败与归因（按"停在第一条真实错误"记录）

| 轮次 | 首错原文 | 归属 |
|---|---|---|
| v1 | `Error in package() method, line 85 / RuntimeError: missing man pages: *.8 in …/p/b/sockl43b3a827db416/b/man` | **配方码路错配**（非平台）：`get(strip_root=True)` 只剥公共首层 `admin/`，还剩 `socklog-2.1.2/`，旧 `source()` 只提升 `src/*`，把 `man/ doc/ package/` 留在下一层 |
| v2 | `Error in test() method, line 28 … FAIL - socklog not found or not executable on PATH`（伴随 `shell-init: error retrieving current directory: getcwd`） | **测试 harness 选错通道**（非平台）：VirtualRunEnv 不导出 PATH，见上 |
| v3 | — | **PASS**（`VERIFY_RC=0`、`**Verdict**: PASS`） |

v1 修法离线自测：`t1-flatten-test.py` 对三种形状（剥 1 层／剥 2 层／完全不剥）先复现
`nested dirs left: ['socklog-2.1.2']`/`['admin']` 两项 FAIL，加 prune 后 `FLATTEN_LOGIC_ALL_OK`。

## 上游测试账本（R51 五维）

上游**有**官方测试：`src/Makefile` 的 `check: default check-socklog-unix check-socklog-inet`
→ `./check-local $(IT)`，`check-local` 逐个跑 `$i.check` 并用 `check-diff` 与随包 `.dist` 黄金输出**逐行**比对。
静态分母 **5 个用例**（`src/*.check` = 5，`src/*.dist` = 5，对应 5 个发布命令）。

| 维度 | as-run（hmdfs cwd） | 改落点后（hmfs `/data/storage/el2/base`） |
|---|---|---|
| 静态总数 | 5 | 5（未缩减） |
| 可执行数 | 5 | 5 |
| 实测通过数 | **1**（uncat） | **3**（socklog、socklog-check、uncat） |
| 跳过数 | 0 | 0 |
| 失败数 | **4** | **2**（socklog-conf、tryto） |

上游日志绝对路径：
- `~/tmp/uc2/z64-socklog/s4-upstream-check-check.log`、`s4-upstream-check-build.log`（`make check` fail-fast 现场）
- `~/tmp/uc2/z64-socklog/s5-run-01.log`（逐用例 + 落点首轮）
- **脚本，不是日志**：`~/tmp/uc2/z64-socklog/s6-landing.sh`（经 `run-s6.sh` 执行，AF_UNIX 逐落点 errno + 往返）。
  ⚠ 该轮 stdout **从未落盘**：`~/tmp/uc2/z64-socklog/` 下没有任何 s6 的输出件（全目录 `grep -rl "errno=1"` 只命中审计件自身对本 notes 的抄录，无日志件）
  ⇒ 下面「失败归因」小节的逐落点五行 errno 读数**只有一份载体＝该脚本自身 + 本 notes 的文字**，无第二处可交叉核，不得写成「见日志」。
  ⚠ 另：第 5 轮同名探针（`s5-run-01.log`）**编译失败且 rc 被吞**——`:14`–`:17` 是 `offsetof` 未声明（缺 `stddef.h`）的 warning 加 `error: expected expression`，而 `:19` 仍印 `afprobe build rc=0`；
  那轮的落点读数 `:20`–`:22` 全是 `afprobe: inaccessible or not found`，**不可**当 errno 证据。`s6-landing.sh:60`–`:63` 已改成 `brc=$?` + 非 0 即 exit，但那一轮的输出没有留下 ⇒ 复核该表需重跑探针（本棒未重跑、也未据此改判）。
- 逐用例 `.local` 实测件：`~/tmp/uc2/z64-socklog/probe/admin/socklog-2.1.2/src/*.local`
  与 `/data/storage/el2/base/z64-socklog/*.local`、`s6-socklog.local`
- ⚠ **台账 harness 偏差（披露）**：两批 `.local` 件由 `s6-landing.sh:79`、`:95` 以
  `PATH="$SRC:$PATH" "./$c.check" </dev/null > "$c.local" 2>&1` 生成，与上游 `src/check-local:7` 的官方口径
  ``env - PATH="$PATH" ctmp="`pwd`/check-tmp" $i.check 2>&1 |cat -v >$i.local`` 有三点不同：**未过 `cat -v`**（控制字符不转义）、**未用 `env -` 清空环境**、
  **stdin 固定 `/dev/null` 且未设 `ctmp`**。⇒ 上面「1/5 与 3/5」是**该偏差 harness 下**的读数：hmdfs 那批的 MATCH/DIFFER 归属由上游自带
  `./check-diff` 判（`s6-landing.sh:80`），el2/base 那轮的 `socklog` 用例是把 `s6-socklog.local`（`:95` 生成、`:97` 打印全文）与 `socklog.dist` 人工逐行核对。
  严格按上游口径复现请走「黄金输出与 argv[0] 的耦合」小节给的 `cd <落点> && PATH="$PWD:$PATH" ./check-local $(IT)`（它自己写 `.local` 并跑 `check-diff`）。

### 失败归因（四本账，配正对照；⛔ 未定性为 OHOS 不支持）

调用原样：`socket(AF_UNIX, SOCK_DGRAM)` + `bind(s, {sun_family=AF_UNIX, sun_path=…}, len)`，
`len = offsetof(struct sockaddr_un, sun_path) + strlen(path) + 1`。

| 落点 | 文件系统 | bind 结果（探针原文） |
|---|---|---|
| `$HOME/tmp/uc2/…/probe/af-hmdfs.sock` | **hmdfs** | `bind() FAILED errno=1 (Operation not permitted)` |
| `$HOME/tmp/af-hmdfs2.sock` | hmdfs | `errno=1 (Operation not permitted)` |
| `…/admin/socklog-2.1.2/src/af-hmdfs3.sock` | hmdfs | `errno=1 (Operation not permitted)` |
| `/data/storage/el2/base/z64-socklog/af.sock` | **hmfs** | `bind() OK roundtrip OK data=ping` |
| `/data/storage/el1/base/z64-socklog/af.sock` | hmfs | `bind() OK roundtrip OK data=ping` |

**两道必要正对照**：① 同目录**普通文件能创建**（hmdfs 与 el2/base 均 `OK`）⇒ 被拒的不是目录写权限；
② **`AF_INET 127.0.0.1:21614` bind OK** ⇒ 不是 socket 子系统整体缺失。
另加**完整往返**（不止 bind）：sendto→recvfrom 收到 `ping`。

⇒ 结论一句可执行的话：**hmdfs 不提供路径型 unix socket（EPERM=1），hmfs 沙箱 base 提供**。
账别：**EPERM(1) 特权/策略类，按文件系统分**，不是 SIGSYS（未按 syscall 号拦）、不是 ENOENT（节点在）、
不是"上游缺功能"。

**救援已实证**：把 `socklog.check` 的 cwd 换到 `/data/storage/el2/base/z64-socklog` 后，
`socklog` 用例输出与 `socklog.dist` **逐行一致**（`listening on socklog.check.socket, starting.` / `foo` / `0` /
`listening on 127.0.0.1:12614, starting.` / `127.0.0.1: foo` / `0` / `U: foo|bar|baz` / `0`），
`socklog-check` 同落点 `check-diff` rc=0。⇒ **改落点可救回 2 个用例，不申报平台能力缺失**。
（照抄到 CI 前必须复跑同路径探针：该 draft 明写 **CI worker 执行 uid 能否写 hmfs base 未验证**。）

**另两例与平台无关，不得混入能力账**：
- `socklog-conf`：本机 `whoami` 报 `cannot find name for user ID 20020084`（uid 无 passwd 条目）⇒
  上游测试脚本 `user=\`whoami\`` 取到空串 ⇒ `mkdir: cannot create directory ‘’`。**环境身份缺失**。
- `tryto`：黄金第 19 行期望 `child "sh" not terminated. sending KILL...`，实得 `child terminated.`。
  `-vt1 -k1` 那条 trap+TERM 用例的**时序竞态**，非平台拦截。**上游测试自身时序敏感**。

### 黄金输出与 argv[0] 的耦合（复现前必读）

`check-local` 以 `PATH=`pwd`:$PATH` + **裸名**调用程序，而 usage 行会原样打 argv[0]。
带 `./` 前缀跑会得到 `usage: ./socklog-check …`，与 `.dist` 的 `usage: socklog-check …` 只差这个前缀
⇒ 复现必须 `cd <落点> && PATH="$PWD:$PATH" ./check-local $(IT)`，**不能带 `./`**。
本包 `test_package` 只断言 `^usage: ` 前缀，正是为了不吃这个耦合。
`-V` 的 `$Id: <sha> $` 是**源码里的字面量**（如 `src/socklog.c:44`），与 `.dist` 逐字相同 ⇒ 平台无关，可稳定断言。

## 运行面划界（⛔ 不声称功能完整可用）

`socklog` 接收面三个后端（`src/socklog.c:39` `USAGE " [-rRU] [unix|inet|ucspi|sun_stream] [args]"`；
`sun_stream` 仅 `__sun__ && __sparc__ && __unix__ && __svr4__` 下编译，本机实测 usage 已无该项）：

- `unix` → `socket(AF_UNIX, SOCK_DGRAM)` + `bind()`（默认 `/dev/log`）
- `inet` → `socket(AF_INET, SOCK_DGRAM)` + `bind()` —— **实测可用**（`127.0.0.1:12614` 收到 `foo`）
- `ucspi` → ucspi 客户端投递 —— **实测可用**（`U: foo/bar/baz`）

**存在可用的替代后端且已一手实证**（inet/ucspi 通过），因此 unix 面的 hmdfs 落点限制
不构成"唯一输出面被拦"，按纪律属**正常交付**，无需停手交回，
也**未用任何 `--disable-*` 缩分母**（上游本无此类开关）。

本棒对 `test_package` 只证到「编译链接成功 + 已安装产物可执行 + 版本/用法面」；
`make check` 的端到端收发证据来自**上游原始树的手工复现**（hmdfs 与 hmfs 两种落点），
**不代表 conan 包在 CI 里跑过端到端**。`socklog.c:85 setuidgid()` 的降权路径本棒未做运行时实证。

⚠ **W3/CI 侧的 `L2_RESULT=skip` 现予披露（此前本地只披露过 verify 报告的「跳过形 PASS」，未提 W3 这一层）**：
`reports/w3-local-ci.log:448`–`:452` 五枚 `[warn] L2: … --version/--help failed (non-blocking)`，判决行 `:456` =
`L2_RESULT=skip: socklog version/help failed, socklog-check failed, socklog-conf failed, tryto failed, uncat failed`。
机制：该步**按绝对路径起进程**（`ci/conan/build_and_test.sh:1685` = `timeout 15 "$bin_file" --version`，`:1693` 是同形的 `--help`），
初值即 `skip`（`:297`–`:298`），只有某枚返 0 才升 `pass`（`:1687`/`:1695`），五枚全非 0 时保持 `skip` 且 non-blocking。
⇒ **`L2_RESULT=skip` 既不是失败，也不能当产物可执行证据**；反过来它也**不是**「产物跑不起来」的证据：上游只认 `-V`
（见「这包实际是什么」第 5 条：有 `-V`、**没有** `--version`），且同一轮 W3 内 `test_package` 由 `:423` 起、`:424`–`:433` 十条 `ok`、
`:434` = `socklog test_package: passed=10 failed=0 total=10`。一手可执行证据两处并列：**`test_package` 在 G2 内实跑 10/10**
（`reports/conan-create.log:92`–`:117`）+ 框架破坏性负例 **L1e**（`reports/w3-local-ci.log:444`–`:446`，把 `bin/` 搬走后测试真红
⇒ 断言确实依赖本包产物，非空壳）。
⚠ 另一条通道要说清以免混记：被证伪的 PATH 查找属 `test_package` 的 **v2 harness**（见「已试过但不采用的方案」第 3 条，
本平台 `conanrunenv-*.sh` 的 `for v in` 为空 ⇒ 不导出 PATH）；W3 的 L2 不走 PATH，两者不是同一件事。

## 候选机制台账 + 四范围查重计数

**范围与命中（计数如实）**

| 范围 | 检索式 | 计数 | 判定 |
|---|---|---|---|
| `knowledge/graph/` | `conf-cc\|conf-ld\|smarden\|find-systype\|print-cc` | **0 文件**（同行检索式实算：`grep -rlE` 无输出＝0 行；`index.tsv` 同式亦 0 行） | **有效 0**（结论不变，且比原写法更强）：此前记的「2 文件（E343.kv、E495.kv）」**取不到字面读数**，只可能来自图谱 CLI 的模糊检索弱命中；两枚按标题复核为 Qt6/CMake 条目（`E343.kv:32` = qtmultimedia 需 qtshadertools 的 Qt6ShaderTools_DIR；`E495.kv:32` = Qt 6 模块 CMake 报 QT_HOST_PATH），与本机制无关 ⇒ 计数按实算写 0 文件 |
| `knowledge/drafts/` | 同上 | **6 文件** | **命中 2 条实质条目**（cdb、bglibs），另有 E6340 等 |
| `经验文档/B草稿库/` | `conf-cc\|smarden` → 0；`AF_UNIX` → 2 文件 | conf-cc **0** / AF_UNIX **命中** | AF_UNIX 机制命中 `DRAFT-PKG-VER-hmdfs-refuses-unix-path-bind-hmfs-sandbox-base-allows` |
| `经验文档/手册/07-技术速查.md` | `conf-cc\|smarden\|find-systype\|print-cc`；`AF_UNIX\|EPERM` | **0 / 0** | 均无 |

**机制 1：smarden/djbware `conf-cc`/`conf-ld` 首行注入 —— 层次对得上，判 HIT（终判归主理）**

对齐到行号：
- `knowledge/drafts/DRAFT-cdb-20251021-djbware-cross-safe-adaptation.md:36`
  —— 「**conf-\* 首行注入**（配方 build() 内做，不进补丁）：conf-cc/conf-ld 首行写…」
- `knowledge/drafts/DRAFT-7324-bglibs-djb-two-stage-cross-build.md:21`
  —— 「spac/djb 树把编译器路径"烤"进生成的包装脚本（conf-cc/conf-ld → …）」
- 同文件 `:31` —— 「阶段 2（target）：**覆写 conf-cc/conf-ld 第一行**为 Conan profile 的目标…」

层次差核对：bglibs 那条的**独有**层次是「交叉两阶段 / native bootstrap 生成器 exec format error」；
本包在 OHOS PC 上 **host==target 本机编译**，生成器 `compile`/`load`/`choose` 直接可执行，
该层次**未触发**（实测 9 个 sysdeps 探测全正面）。⇒ 与 bglibs 是**同族不同层次**；
真正对齐的是 cdb 的"首行注入"那一条（同一层次、同一解法）。
cdb draft 第 64 行自陈「engine 无任何 djbware 条目（conf-cc/conf-home/make prog 关键词零命中）」
—— 与本棒 `knowledge/graph/` 有效 0 命中的实测**互相印证**。

本包**新增的只是 L3 版本笔记**（不上升为机制）：① smarden `admin/<pkg>-<v>/src` 三层嵌套 +
`strip_root` 半剥导致 `man/` 丢失；② `print-ar.sh` 硬编码 `ar`/`ranlib`、本包**没有** `conf-ar`
入口（与 runit 写法不同，照抄 runit 会白写一个文件）。

**机制 2：AF_UNIX 路径 bind 按文件系统分 —— 命中池件，判 HIT**

对齐到 `DRAFT-PKG-VER-hmdfs-refuses-unix-path-bind-hmfs-sandbox-base-allows.md`
的症状形状、逐落点表（hmdfs EPERM(1) / hmfs `el*/base` bind+往返 OK）
与两道正对照（普通文件可建 / AF_INET 可 bind）**逐条同形**，本棒在 **B 机 + 另一个包** 上独立复现。⚠ 该件**原件在仓外**（规则工作区 `经验文档/B草稿库/`，不在本仓、不随本 PR 出仓 ⇒ 评审者按该路径取不到原件）；其症状形状、逐落点 errno 表（hmdfs 三枚 `errno=1 (Operation not permitted)` / hmfs `el2/base`、`el1/base` 两枚 `bind() OK roundtrip OK data=ping`）与两道正对照（同目录普通文件可建 + `AF_INET 127.0.0.1` bind OK）已在本 notes「失败归因」小节整表抄录 ⇒ 本 PR 内以该表为唯一判据载体，不留悬空外部引用。
⛔ 本棒未取用该池件命名新建草稿、未改 `knowledge/drafts/`、未建 Issue（取用与配送归主理）。

⇒ **两条候选都是 HIT，无一需要 create**；本包无"唯一输出面被拦"，不构成路径 C 资质话题。

## 依赖

`build.dependencies: []`。socklog 自带全部支持代码（`unix.a`/`byte.a`/`time.a` 由树内 `.c` 编出），
`requires`/`tool_requires` 均空 ⇒ 无 W0/R36 风险。
`preflight_check.sh socklog/2.1.2` 印「未找到依赖声明 + 预检通过」在**配方生成前是空判**，
配方落地后依赖集为空、`PF4` 无 requires 可探 ⇒ 该"通过"才是真判。

## 交付物形状依据（本仓同类包对照）

参照 **bare-makefile 的 CLI 包** 3 例：`archives/r/runit/2.3.1`、`archives/d/daemontools-encore/1.11`、
`archives/c/cdb/20251021` —— 三者均有软件级 `manifest.yaml` + `README.md` + `commands.json`，本包齐三件。
主参照 **runit/2.3.1**（同作者、同 `conf-cc`/`conf-ld` 风格、同 `admin/<pkg>-<v>/src` 目录形）。

⚠ 本配方**故意比 runit 多两处**：`export_sources()` / `apply_conandata_patches()`。
`scripts/ohc/conan_verify.py` 的 `gate1_recipe_completeness()` 对 `conanfile.py` 做**字面量包含检查**，
硬性要求这两个串，**上游 0 补丁也不能删**（runit 是这条门落地前合入的，盘上没有这两个串）。

⚠ 与 runit 的**两处实质差异**（照抄 runit 会错）：
① 本包**没有** `conf-ar`（`print-ar.sh` 硬编码 `ar cr`），写它是无效文件；
② `source()` 不能用"提升 `src/*`"了事，必须连 `man/ doc/ package/` 一起压平（v1 的实际死因）。

## 补丁

无。`patches_applied: []`，未建 `patches/` 目录（零源码改动）。

## 遗留风险（交下一棒，不隐藏）

1. **CI 侧 hmfs 落点未验证**：若要 PR 正文写上游端到端测试通过数，必须先在 CI 环境复跑
   `el*/base` bind+往返探针并确认 `make check` 落点可用；本棒只证到 B 机 SSH 用户（uid 20020084）可行。
   ⛔ 不得把「3/5」当 CI 结论。
2. **`tryto` 时序竞态**与 **`whoami` 无 passwd 条目** 会让上游 `make check` 在任何落点都稳不过 5/5；
   正文的测试对比须按"分母 5、通过数照实测、失败原因分账"写，⛔ 不许缩分母。
3. 文件模式按 `git ls-files -s archives/s/socklog/2.1.2/` 实算：`conanfile.py`、`test_package/conanfile.py`、`test_package/test_socklog.sh` 三枚是 **100755**，`conandata.yml` 与其余入库件（`manifest.yaml`、`notes.md`、`MANIFEST.yml`、`reports/*`）是 **100644**；仓内同类 runit/2.3.1 全部入库件均为 **100644**。
   外观项、无门禁在读；改它会换 recipe revision 触发重跑，**是否清理由主理定**。
4. `archives/s/socklog/2.1.2/reports/` 与 `test_package/` 下的 conan 生成件（`conan*.sh`、
   `deactivate_*.sh`、`metadata`）**已被 gitignore**，verify 三轮后 `git status` 除 libXext 两枚幻影外干净。
   ⚠ W3 的机器可读结果件 `.ci-result.json` **不入库**：CI build#61442 实拍它同时触发 JC1（运行时状态文件）与 JC5（archives 下未登记隐藏文件）两条 FAIL，`JC_ERRORS=2` ⇒ `L0_RESULT=fail: junk_check failed`，构建被挡在编译之前。其字段值抄录于此备核：`step=W3_local_ci`、`exit_code=0`、`timestamp=2026-09-26T03:39:57.735290`、`log_sha256=d8b6c397a86a25512f509fd2276187e4ec421484da2d5e42c3c2a39bc3845b30`（与 `reports/w3-local-ci.log` 实算同值）；原件另存本地未入库，且其 `archive_dir` 含本机绝对路径，本就不宜公开。
5. 语言/难度标注：平台卡 `lang=cpp`、`difficulty=medium` 与本地【易】不一致；实测本包是纯 C
   （`.c` 93、`.h` 29，**无 C++ 源文件**，`find *.cpp/*.cc/*.cxx` 零命中）+ bare makefile，
   走 conan 流程通吃，**未触发 `env_unsupported`**，故不走 §8 语言例外。

### 对话 1

第 1 棒（定源 → 读 SKILL → 起配方 → build → conan-verify）：
定源三向同哈希、SKILL/KNOW_YOUR_WHY/CONTRIBUTING 全文读毕、配方 10 件落地、
`conan-verify` 三轮至 **PASS（VERIFY_RC=0）**，另附上游 `make check` 五维账本与 AF_UNIX 落点定性。
---

**编译结束**: 2026-09-26 03:39
**最终状态**: built
