# pgpgpg 0.13 适配笔记

## 编译环境
- 构建系统: autotools（上游 release tarball 自带 `configure` 与 `Makefile.in`，设备端不再生成 Autotools 文件）
- 编译日期: 2026-09-25
- 编译器: clang/clang++（profile `ci/conan/profiles/ohos-aarch64`，os=OHOS / arch=armv8）
- Conan: 2.29.1；`CONAN_HOME=$HOME/tmp/ch/home-pgpgpg`

## 本包的关键接缝：configure 期把 gpg 绝对路径烧进产物

一手读数（`https://mroth.net/pgpgpg/pgpgpg-0.13.tar.gz` 解出的树）：

| 位置 | 原文 |
|---|---|
| `configure.in:21` | `AC_ARG_WITH(gpg-path, ...)` |
| `configure.in:40` | 首字符非 `/` 即报错退出 ⇒ 必须绝对路径 |
| `configure.in:47` | `if test ! -x "$withval"; then ... exit 1` ⇒ 必须可执行 |
| `configure.in:57` | 缺省路径 `AC_PATH_PROG(path_to_gpg, gpg, no)` |
| `configure.in:58-67` | PATH 里找不到 gpg 直接 `exit 1` |
| `configure.in:69` | `AC_DEFINE_UNQUOTED(GPG_PATH, "$path_to_gpg")` |
| `pgpopts.c:725` | `argv_factory_add(&af, GPG_PATH)`（作为 argv[0]） |
| `defaultkey.c:54` | 同上，取默认密钥时也走 `GPG_PATH` |
| `main.c:147` | `execv(gpg_argv[0], gpg_argv)` |

⇒ `execv` 不搜 `PATH`，"运行期由 PATH 决定 gpg" 不成立；配方必须在 configure 期给出一个**真机存在且可执行**的绝对路径。
⇒ gnupg 的语义是"被 exec 的外部程序"，按 `tool_requires("gnupg/2.4.9.1")` 声明，路径取自其 Conan `package_folder`（R33：不裸用 shell 变量、不引 `/usr/local` 字面量）。取法必须是 `self.dependencies.build["gnupg"]`（见问题表第 5 行），`self.dependencies["gnupg"]` 会 `KeyError`。

## 编译步骤

1. `get()` 取上游官方 tarball（`https://mroth.net/pgpgpg/pgpgpg-0.13.tar.gz`，sha256 `905e1d2c60715a733f30e7469e9255370d69858abfe0c7d4972b10cb0165cbc3`，`strip_root=True`）。
2. `generate()`：`AutotoolsToolchain` + `tc.configure_args.append("--with-gpg-path=" + <gnupg package_folder>/bin/gpg)`。本轮实际烧入的绝对路径见"落点与接缝的实际取值"小节。
3. `build()`：`autotools.configure()` → `make -j1` → `make target=check`（空转，rc=`0`，仅作安装面冒烟，不计入上游测试账本）。
4. `package()`：`Autotools(self).install()` → `make install DESTDIR=<package_folder>`（安装面为 `Makefile.in:300 install: install-am`、`:35 DESTDIR =`、`:166/:308 $(mkinstalldirs) $(DESTDIR)$(bindir)`，支持 DESTDIR）。
5. `package_info()`：`cpp_info.bindirs = ["bin"]`，无库无头。

## 未走一键路径的原因（本机框架缺陷，已入表并上报）

`scripts/ohc-run.py init-build` 在本机必崩，链条如下（一手读数：`~/tmp/uc2/z44-pgpgpg/driver2.out`）：

1. `~/usr/local/bin/automake` 的 shebang 指向不存在的 `~/usr/local/bin/perl` ⇒ `execve` 以**脚本路径**报 ENOENT；
2. `scripts/ohc/check_env.py:31-33` 的 `except Exception:` 分支里 `return False, str(e)` 引用了未绑定的 `e` ⇒ `NameError: name 'e' is not defined`；
3. `scripts/ohc/init_build.py:543` 无条件先调 `check_env()`，位置在生成 `.build-context-pgpgpg-0.13` **之前** ⇒ context 永远生不出来 ⇒ `build` 与 `conan-init` 双双不可用（conan-init 的入参就是 `.build-context-*`）；`init-build --help` 没有跳过环境检查的开关；
4. 绕行入口 `init-archive` 的模板查找键与 `templates/` 实际文件名不匹配（报"模板不可用"，而 `templates/conanfile-autotools.py.tmpl` 等确实存在），且它生成的 `manifest.yaml` 里留下未填充的模板标记。

两条修法（`check_env.py` 的 bugfix、补 perl 软链）分别落在框架面与家目录基础设施区，均已上报主理/用户，**不由本包 PR 触碰**。**未伪造 `.build-context-*`、未伪造任何目录去骗工具。**
⇒ 本包按仓内同形态先例 `archives/a/abnfgen/0.21/`（上游自带 configure、`package_type = "application"`、`Autotools(self).install()`、`validate()` 用 `in ("Linux","OHOS")`、`upstream_tests: []`）配合仓内 `templates/` 模板实例化配方。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 一键入口不可用（见上一节） | 框架 `check_env.py:33` + 设备缺 perl 软链 | 按同形态先例 + 模板手工实例化；缺陷已上报，本包不碰框架 |
| 2 | configure 期 gpg 探测 | 上游要求绝对 + 可执行路径，`execv` 不搜 PATH | `tool_requires("gnupg/2.4.9.1")` + `--with-gpg-path=<package_folder>/bin/gpg` |
| 3 | test 环境拿不到可运行的 gpg | 主配方按工具声明依赖，运行期边不在 test 的 run 环境里 | test_package 同样以 `tool_requires` 声明 gnupg，用 `env="conanbuild"`（VirtualBuildEnv 把 gpg 送上 PATH、其依赖送上 `LD_LIBRARY_PATH`），两个二进制都按绝对路径传入（R34） |
| 4 | 空 `CONAN_HOME` 报 `Remote doesn't exist`，长得像"依赖未发布" | 新建 home 缺 `remotes.json` | 在本任务 home 内 `conan remote add ohpcd ...` + `conan remote disable conancenter`；已作为环境坑入表（未动共享 profile） |
| 5 | `self.dependencies["gnupg"]` 在 `generate()` 里抛 `KeyError: gnupg not found in the dependency set` | conan 2 的 `self.dependencies[...]` 默认只查 **host** 上下文（`conan/internal/model/dependencies.py:36-42`），`tool_requires` 在 build 上下文 | 改用 `self.dependencies.build["gnupg"].package_folder`（同仓先例 `archives/a/abx/0.1/conanfile.py:166`、`archives/a/abiword-plugin-gdict/3.0.8/conanfile.py:189`）；**依赖形态仍是 `tool_requires`，未改成 `requires`** |
| 6 | 站内 gnupg 的 gpg 报 `error running '/bin/gpg-agent': probably not installed` | 该 gpg 把 agent 解析到自己编译期烧进去的默认路径 | 在一次性 `GNUPGHOME/gpg.conf` 里用官方 `agent-program <依赖包内 gpg-agent 绝对路径>` 指过去（不伪造 PATH、不改 gpg 产物） |
| 7 | 按 6 指过去之后 agent 仍起不来：`error binding socket to <GNUPGHOME>/S.gpg-agent: Operation not permitted` | **不是能力墙、也不是 gpg 或本包的问题**：设备侧取证（B 机，同 uid 同进程同一条 `bind()`）定性为**挂载点差异** —— `/storage/Users/**`（hmdfs 族，含 `$HOME/tmp` 与 conan 包目录）对**路径型 socket inode** 与 `mkfifo()` 一律 EPERM；`/data/storage/el1|el2/base/**`（hmfs）bind+connect+accept 端到端通过。路径长度已独立排除（真实 socket 路径 64 字节；缩到 50 字节仍 EPERM，同长度换 hmfs 即 RC=0；长度扫描 60/100/107→EPERM、108/109/115→**EINVAL**，两种读数） | **`GNUPGHOME` 与工作目录改落到仓内约定的可写根**：候选按 `$PGPGPG_E2E_ROOT` → `$TMPDIR` → `/data/storage/el2/base/cache` → `/data/storage/el1/base/cache` → `/data/storage/el2/base` → `/data/storage/el1/base` → `$HOME/tmp` 逐个探测择优（**不硬编码单一 el1/el2**）。主理已查实该路径族是本仓约定的可写根（`git grep -l "data/storage/el" origin/main -- archives` 命中 848 份归档，含 `abbtr/1.0.4`、`acpid/2.0.34`、`actions-up/1.16.0`）⇒ CI 可达。本轮择优结果与逐根读数见下两节 |
| 8 | 翻译面（PGP 选项 → gpg 命令行）没有可断言的出口 | `execv` 的 argv 在产物内部形成，`GPG_PATH` 又是 configure 期烧死的绝对路径 ⇒ 既不能用"假 gpg"挂到 PATH 上，也不该往依赖包的缓存目录里写东西 | 用内核侧接缝记录 argv：把 pgpgpg 的 stdin 接到一根 held 管道（`sleep` 占住写端不写数据），被 exec 的 gpg 阻塞在 `read()` 上，此时读 `/proc/<pid>/cmdline` 就是 `execve` 实际传入的 argv。扫描先用 `/proc/<pid>/comm` 做零 fork 预筛（每个条目 fork 一次 `tr` 会把一轮采样拖到分钟级，本仓实拍） |

## 已知限制（交付口径，请勿外推）

- **`GPG_PATH` 是构建期 Conan 缓存里的绝对路径**（本轮实测烧入值见"落点与接缝的实际取值"）。
  ⇒ 产物只在**同一台机、同一 `CONAN_HOME`、该 gnupg 包未被回收**时可用；清缓存、换机、或 CI 与本地使用不同 home 时，产物运行期会以 `No such file or directory` 失败。**不得表述为"任意环境下可用"**。
  ⇒ `gnupg/2.4.9.1` 的二进制发布态另有证据：`Downloading recipe gnupg/2.4.9.1#6f35614a8ac997cf2316e4e47f37205a`、`conan install --requires=gnupg/2.4.9.1 --build=never` rc=0 带 13.2MB `conan_package.tgz`。
- **下游消费者不会自动获得 gpg**：gnupg 以 `tool_requires` 声明（依据：它是被 exec 的外部程序，不是链接期依赖），装了 `pgpgpg` 不等于装了 `gnupg`；运行期需要使用者自备同一绝对路径下的 gpg。
- **gpg 找 agent 用的是它自己编译期烧进去的默认路径 `/bin/gpg-agent`**（设备上不存在），需在使用者的 `GNUPGHOME/gpg.conf` 里以官方 `agent-program` 指到实际路径；本包测试脚本就是这么做的。这条属 gnupg 包的运行环境限制，本包不代它修。
- **端到端腿的落点约束**：`GNUPGHOME` 必须落在支持路径型 socket inode 的可写根（hmfs 族）。落在 `/storage/Users/**` 时 gpg-agent 绑不上 socket，私钥腿（keygen / 解密 / 带有效收件人的加密）不可用 —— 测试脚本对这种情况**逐条打印 `SKIP: <id> -- <原因原文>` 并计入 skip 维**，不静默、不并入 pass。
- **翻译面（T 组）依赖 `/proc/<pid>/cmdline` 可读**：本轮在 B 机实测可读。若某台 worker 上不可读，T 组会**红**而不是跳过 —— 这是有意的：翻译面是本包唯一的功能面，红比"看起来绿"更有用。
- **上游 0.13 是 1999 年代码**：`--with-gpg-path` 探测的是构建机的 gpg，不校验版本；本包只在 `gnupg/2.4.9.1` 上做过程序化验证，未覆盖 gpg 1.x/2.2 的选项差异。
- **PGP 长选项族（`+keyword`）本轮不在断言面内**：实拍 `+charset=utf-8` 被上游自己的白名单拒（`Error: Charset 'utf-8' not supported.`）、`+batchmode=true` 被 `fetch_bool` 判成非法布尔值（`Error: Invalid boolean value 'true' for long option 'batchmode'.`）⇒ 这两条与 OHOS 无关，属上游选项校验，本轮未继续下钻（见"本棒未验证的点"）。
- **E490（autotools helper 可执行位）本轮不触发**：上游 release tarball 自带**已生成且可执行**的 `configure`/`config.guess`/`config.sub`/`install-sh`/`missing`，无需 `autoreconf` 自举 ⇒ 该风险不落地；`conan-verify` G0 仍按图谱打印 `Knowledge hit: E490` 与「未在配方中处理」提示（`reports/conan-verify-report.md:9-11`），**G2 实测 `## G2: ✅ PASS`（同文件 `:31`）**，故不据此改动配方。

## 未采用方案与理由

- 「给上游打补丁，把 `main.c:147` 的 `execv` 换成 `execvp`，让 gpg 走 PATH 解析」——**不采纳**：那改的是上游语义。把 gpg 钉死在构建期确定的路径正是这个 PGP 兼容包装器的设计意图（`configure.in` 特意拒绝相对路径与非可执行文件），为打包侧缓存路径的不稳定性去动上游运行期行为不值得，也会让产物行为随环境变量漂移。
- 「把 `tool_requires` 改成 `requires` 让运行期自洽」——**本包不采纳**（口径同上：exec 的外部程序归工具）。
- 「为了拿到翻译后的 argv，给配方加 `--enable-debug`（上游 `configure.in:98` 的开关，只有它才让 `main.c:127-137` 打印 `gpg_argv`）」——**不采纳**：那是**为测试改构建配置**，代价是交付物每次运行往 stderr 打两行 argv（并激活 `assert()`），改了所有使用者的可见行为。改用内核侧 `/proc/<pid>/cmdline` 记录（问题表第 8 行），产物保持默认构建。
- 「`GNUPGHOME` 留在 hmdfs，只把 `S.gpg-agent` 符号链接到 hmfs 上的 socket」——**不采纳**：取证一臂实测可行（keygen/sign rc=0，控制组去掉链接则 rc=2），但它把 agent 的密钥文件与撤销证书分裂到两个 homedir，代价不清不楚；本包直接换落点。
- 「在依赖包的 `bin/` 里放一个记录 argv 的假 gpg」——**不采纳**：那是往 `gnupg/2.4.9.1` 的缓存包目录里写东西（污染别人的产物缓存；CI 上还会影响同一 job 里的其它包）。
- 「把跑不通的断言删掉凑绿」——**不采纳**：脚本按 T / E 两组记账，`discovered/passed/failed/skipped` 全部由实际计数器产出（`discovered=$((PS+FS+SS))`），且每个臂结束会自检"本臂有没有产出读数"，产出 0 条即记 `<arm>/accounting` FAIL，防"静默不计数"。

## 测试账本（rule4，数字全部来自本轮真跑）

| 维度 | 数 | 依据 |
|---|---|---|
| 上游注册用例 | 0 | `grep -n TESTS Makefile.in` → RC=1（零命中）；`Makefile.in:285 check-am: all-am` 空转 ⇒ `upstream_test_in_build: false`，空转不算"上游测试在构建内运行" |
| 消费者断言（合计） | 32 | `archives/p/pgpgpg/0.13/test_package/test_pgpgpg.sh`：T 组＝翻译面（必跑，不依赖 agent/密钥/网络），E 组＝端到端（环境不支持则逐条显式 SKIP）；静态站点 T 17 + E 15 = 32，与 `MANIFEST.yml assertion_count` 同源 |
| pass | 32 | 逐条原文见「本轮实测原文」（`reports/conan-create.log:488` 与 `reports/w3-local-ci.log:616` 两处 `TEST_SUMMARY discovered=32 passed=32 failed=0 skipped=0`） |
| fail | 0 | 本轮（W3 2026-09-28T12:52:00.939073）实测 0；整改前旧一轮为 3（`accounting` 两臂 + `two_recipients` 证据通道），已在第 4 棒按「采集写进同一臂」「换 /proc argv 通道」修掉，不是缩分母 |
| skip | 0 | 本轮 hmfs 可用 ⇒ 无降级；降级格式是 `SKIP: <id> -- <原因原文>`，脚本逐条计入 skip 维不并入 pass |

⇒ 五维分开记账，fail 不混进 skip；上游注册用例为 0，本包全部是消费者侧断言。

### 本轮实测原文（取自 W3 的 `test()` 输出；同日另有一次独立 `conan create`，输出与本块逐行一致；**可核行号以随包 `reports/conan-create.log:488` 为准**）

```pgpgpg/0.13 (test package): RUN: "/data/service/hnp/bin/bash" "/storage/Users/currentUser/qzy/主理-48-pgpgpg-0.13/archives/p/pgpgpg/0.13/test_package/test_pgpgpg.sh" "/storage/Users/currentUser/tmp/ch/home-pgpgpg/p/b/pgpgpd9fee54748d7f/p/bin/pgpgpg" "/storage/Users/currentUser/tmp/ch/home-pgpgpg/p/gnupgd91e6a428a824/p/bin/gpg"
PGP=/storage/Users/currentUser/tmp/ch/home-pgpgpg/p/b/pgpgpd9fee54748d7f/p/bin/pgpgpg
GPG=/storage/Users/currentUser/tmp/ch/home-pgpgpg/p/gnupgd91e6a428a824/p/bin/gpg
WORK=/storage/Users/currentUser/tmp/pgpgpg-r3-50035
OUT=/storage/Users/currentUser/tmp/pgpgpg-r3-50035/out
CANDIDATES= /storage/Users/currentUser/tmp /data/storage/el2/base/cache /data/storage/el1/base/cache /data/storage/el2/base /data/storage/el1/base /storage/Users/currentUser/tmp
E_CANDIDATES= /data/storage/el2/base/cache /data/storage/el1/base/cache /data/storage/el2/base /data/storage/el1/base
== arm t01_baked_gpg_path
ASSERT ok   : baked_gpg_path
            -> 产物内烧入的 GPG_PATH = /storage/Users/currentUser/tmp/ch/home-pgpgpg/p/gnupgd91e6a428a824/p/bin/gpg
== arm t02_recorded
ASSERT ok   : recorded
            -> 采到 execve argv：/storage/Users/currentUser/tmp/ch/home-pgpgpg/p/gnupgd91e6a428a824/p/bin/gpg --no-batch --set-filename stdin --output /storage/Users/currentUser/tmp/pgpgpg-r3-50035/out/t02.asc --armor --store 
== arm t02_argv0
ASSERT ok   : t02_argv0
            -> /storage/Users/currentUser/tmp/pgpgpg-r3-50035/evidence/argv.t02 里记录了 [/storage/Users/currentUser/tmp/ch/home-pgpgpg/p/gnupgd91e6a428a824/p/bin/gpg ]
== arm t02_armor
ASSERT ok   : t02_armor
            -> /storage/Users/currentUser/tmp/pgpgpg-r3-50035/evidence/argv.t02 里记录了 [--armor]
== arm t02_store
ASSERT ok   : t02_store
            -> /storage/Users/currentUser/tmp/pgpgpg-r3-50035/evidence/argv.t02 里记录了 [--store]
== arm t02_output
ASSERT ok   : t02_output
            -> /storage/Users/currentUser/tmp/pgpgpg-r3-50035/evidence/argv.t02 里记录了 [--output /storage/Users/currentUser/tmp/pgpgpg-r3-50035/out/t02.asc]
== arm t02_setfilename
ASSERT ok   : t02_setfilename
            -> /storage/Users/currentUser/tmp/pgpgpg-r3-50035/evidence/argv.t02 里记录了 [--set-filename stdin]
== arm t02_nobatch
ASSERT ok   : t02_nobatch
            -> /storage/Users/currentUser/tmp/pgpgpg-r3-50035/evidence/argv.t02 里记录了 [--no-batch]
== arm t02_no_encrypt
ASSERT ok   : t02_no_encrypt
            -> 确认 /storage/Users/currentUser/tmp/pgpgpg-r3-50035/evidence/argv.t02 中没有 [--encrypt]
== arm t02_no_symmetric
ASSERT ok   : t02_no_symmetric
            -> 确认 /storage/Users/currentUser/tmp/pgpgpg-r3-50035/evidence/argv.t02 中没有 [--symmetric]
== arm t05_default_output_name
ASSERT ok   : default_output_name
            -> 无 -o 时产物落在 plain.txt.asc（135 字节，pgpgpg rc=0）
== arm t05_armor_header
ASSERT ok   : t05_armor_header
            -> /storage/Users/currentUser/tmp/pgpgpg-r3-50035/plain.txt.asc 里记录了 [-----BEGIN PGP MESSAGE-----]
== arm t06_encrypt_call
            -> 本轮 gpg stderr 原文：
            | gpg: WARNING: unsafe ownership on homedir '/storage/Users/currentUser/tmp/pgpgpg-r3-50035/homet'
            | gpg: error running '/bin/dirmngr': probably not installed
            | gpg: failed to start dirmngr '/bin/dirmngr': Configuration error
            | gpg: can't connect to the dirmngr: Configuration error
            | gpg: error retrieving 'z44nosuch+t06@example.invalid' via WKD: No dirmngr
            | gpg: z44nosuch+t06@example.invalid: skipped: No dirmngr
            | gpg: /storage/Users/currentUser/tmp/pgpgpg-r3-50035/plain.txt: encryption failed: No dirmngr
            | WARNING: Can't find the right public key-- can't check signature integrity.
ASSERT ok   : t06_pgprc
            -> 找不到收件人公钥时的 PGP 退出码（main.c 的 WEXITSTATUS 映射：gpg rc=2 => PGPERR_KEY_NOT_EXIST=11）：rc=11（预期 11）
== arm t06_recipient_slot
ASSERT ok   : t06_recipient_slot
            -> /storage/Users/currentUser/tmp/pgpgpg-r3-50035/evidence/t06.err 里记录了 [z44nosuch+t06@example.invalid]
== arm t06_input_slot
ASSERT ok   : t06_input_slot
            -> /storage/Users/currentUser/tmp/pgpgpg-r3-50035/evidence/t06.err 里记录了 [/storage/Users/currentUser/tmp/pgpgpg-r3-50035/plain.txt]
== arm t08_decrypt_differential
            -> 裸 -d 的 gpg stderr：
            | gpg: WARNING: unsafe ownership on homedir '/storage/Users/currentUser/tmp/pgpgpg-r3-50035/homet'
            | gpg: WARNING: no command supplied.  Trying to guess what you mean ...
            | gpg: no valid OpenPGP data found.
            | gpg: processing message failed: Unknown system error
            | WARNING: Can't find the right public key-- can't check signature integrity.
            -> -d -f 的 gpg stderr：
            | gpg: WARNING: unsafe ownership on homedir '/storage/Users/currentUser/tmp/pgpgpg-r3-50035/homet'
            | gpg: no valid OpenPGP data found.
            | gpg: decrypt_message failed: Unknown system error
            | WARNING: Can't find the right public key-- can't check signature integrity.
ASSERT ok   : decrypt_differential
            -> 裸 -d 未译出命令（gpg 自行猜），-d -f 则显式 --decrypt ⇒ 差分成立
== arm t08_nocmd_on_bare
ASSERT ok   : t08_nocmd_on_bare
            -> 确认 /storage/Users/currentUser/tmp/pgpgpg-r3-50035/evidence/t08a.err 中没有 [decrypt_message failed]
== arm e1_capable_root
ASSERT ok   : capable_root
            -> GNUPGHOME=/data/storage/el2/base/cache/pgpgpg-r3-50035.home（候选根择优结果）；agent socket 已建成且节点类型是 socket：srwx------
== arm e2_keygen
ASSERT ok   : keygen
            -> 在 /data/storage/el2/base/cache/pgpgpg-r3-50035.home 上 gpg --batch --generate-key rc=0，--list-secret-keys 计 1 把（第一把；e8 另生成第二把；逐根读数见 /storage/Users/currentUser/tmp/pgpgpg-r3-50035/evidence/keygen.*.log）
== arm e3_ownertrust
ASSERT ok   : ownertrust
            -> 密钥已置为终极可信（--with-colons 的 pub 字段第 2 位是 u）
== arm e4_armor_encrypt
ASSERT ok   : e4_armor_rc
            -> pgpgpg -e -a 真加密（stderr 见 /storage/Users/currentUser/tmp/pgpgpg-r3-50035/evidence/e4.err）：rc=0（预期 0）
== arm e4_armor_header
ASSERT ok   : e4_armor_header
            -> /storage/Users/currentUser/tmp/pgpgpg-r3-50035/out/e4.asc 里记录了 [-----BEGIN PGP MESSAGE-----]
== arm e5_recorded
ASSERT ok   : recorded
            -> 采到带有效收件人的 execve argv：/storage/Users/currentUser/tmp/ch/home-pgpgpg/p/gnupgd91e6a428a824/p/bin/gpg --armor --no-batch --output /storage/Users/currentUser/tmp/pgpgpg-r3-50035/out/e5.bin --recipient pgpgpg-e2e@example.invalid --encrypt /data/storage/el2/base/cache/pgpgpg-r3-50035.e5.in 
== arm e5_argv_encrypt
ASSERT ok   : e5_argv_encrypt
            -> /storage/Users/currentUser/tmp/pgpgpg-r3-50035/evidence/argv.e5 里记录了 [--encrypt]
== arm e5_argv_recipient
ASSERT ok   : e5_argv_recipient
            -> /storage/Users/currentUser/tmp/pgpgpg-r3-50035/evidence/argv.e5 里记录了 [--recipient pgpgpg-e2e@example.invalid]
== arm e5_argv_armor
ASSERT ok   : e5_argv_armor
            -> /storage/Users/currentUser/tmp/pgpgpg-r3-50035/evidence/argv.e5 里记录了 [--armor]
== arm e6_armor_roundtrip
ASSERT ok   : armor_roundtrip
            -> pgpgpg -d 解回 35 字节，与明文 cmp 逐字节一致（-e rc=0 / -d rc=0）
== arm e7_binary_roundtrip
ASSERT ok   : binary_roundtrip
            -> 非 armor 腿：密文 384 字节且无 ASCII 头，解回与明文 cmp 一致
== arm e8_recorded
ASSERT ok   : recorded
            -> 采到双收件人调用的 execve argv：/storage/Users/currentUser/tmp/ch/home-pgpgpg/p/gnupgd91e6a428a824/p/bin/gpg --armor --no-batch --output /storage/Users/currentUser/tmp/pgpgpg-r3-50035/out/e8.bin --recipient pgpgpg-e2e@example.invalid --recipient e8b+t07@example.invalid --encrypt /data/storage/el2/base/cache/pgpgpg-r3-50035.e8.in 
== arm e8_argv_recipient_a
ASSERT ok   : e8_argv_recipient_a
            -> /storage/Users/currentUser/tmp/pgpgpg-r3-50035/evidence/argv.e8 里记录了 [--recipient pgpgpg-e2e@example.invalid]
== arm e8_argv_recipient_b
ASSERT ok   : e8_argv_recipient_b
            -> /storage/Users/currentUser/tmp/pgpgpg-r3-50035/evidence/argv.e8 里记录了 [--recipient e8b+t07@example.invalid]
== arm e8_argv_order
ASSERT ok   : e8_argv_order
            -> argv 里 --recipient 恰 2 条，且 pgpgpg-e2e@example.invalid（位置 164）在 e8b+t07@example.invalid（位置 203）之前 ⇒ 顺序与命令行一致，两个收件人操作数都没被丢
AGENT_LEFT=0
--- execve argv 记录清单 ---
t02=/storage/Users/currentUser/tmp/ch/home-pgpgpg/p/gnupgd91e6a428a824/p/bin/gpg --no-batch --set-filename stdin --output /storage/Users/currentUser/tmp/pgpgpg-r3-50035/out/t02.asc --armor --store 
e5=/storage/Users/currentUser/tmp/ch/home-pgpgpg/p/gnupgd91e6a428a824/p/bin/gpg --armor --no-batch --output /storage/Users/currentUser/tmp/pgpgpg-r3-50035/out/e5.bin --recipient pgpgpg-e2e@example.invalid --encrypt /data/storage/el2/base/cache/pgpgpg-r3-50035.e5.in 
e8=/storage/Users/currentUser/tmp/ch/home-pgpgpg/p/gnupgd91e6a428a824/p/bin/gpg --armor --no-batch --output /storage/Users/currentUser/tmp/pgpgpg-r3-50035/out/e8.bin --recipient pgpgpg-e2e@example.invalid --recipient e8b+t07@example.invalid --encrypt /data/storage/el2/base/cache/pgpgpg-r3-50035.e8.in 
--- 逐臂台账（id outcome） ---
t01_baked_gpg_path/baked_gpg_path PASS
t02_recorded/recorded PASS
t02_argv0/t02_argv0 PASS
t02_armor/t02_armor PASS
t02_store/t02_store PASS
t02_output/t02_output PASS
t02_setfilename/t02_setfilename PASS
t02_nobatch/t02_nobatch PASS
t02_no_encrypt/t02_no_encrypt PASS
t02_no_symmetric/t02_no_symmetric PASS
t05_default_output_name/default_output_name PASS
t05_armor_header/t05_armor_header PASS
t06_encrypt_call/t06_pgprc PASS
t06_recipient_slot/t06_recipient_slot PASS
t06_input_slot/t06_input_slot PASS
t08_decrypt_differential/decrypt_differential PASS
t08_nocmd_on_bare/t08_nocmd_on_bare PASS
e1_capable_root/capable_root PASS
e2_keygen/keygen PASS
e3_ownertrust/ownertrust PASS
e4_armor_encrypt/e4_armor_rc PASS
e4_armor_header/e4_armor_header PASS
e5_recorded/recorded PASS
e5_argv_encrypt/e5_argv_encrypt PASS
e5_argv_recipient/e5_argv_recipient PASS
e5_argv_armor/e5_argv_armor PASS
e6_armor_roundtrip/armor_roundtrip PASS
e7_binary_roundtrip/binary_roundtrip PASS
e8_recorded/recorded PASS
e8_argv_recipient_a/e8_argv_recipient_a PASS
e8_argv_recipient_b/e8_argv_recipient_b PASS
e8_argv_order/e8_argv_order PASS
TEST_SUMMARY discovered=32 passed=32 failed=0 skipped=0
```

### 落点与接缝的实际取值

```
GPG_PATH（产物内烧入值，取自本轮 test() 打印 t01_baked_gpg_path）: /storage/Users/currentUser/tmp/ch/home-pgpgpg/p/gnupgd91e6a428a824/p/bin/gpg
PGP=/storage/Users/currentUser/tmp/ch/home-pgpgpg/p/b/pgpgpd9fee54748d7f/p/bin/pgpgpg
GPG=/storage/Users/currentUser/tmp/ch/home-pgpgpg/p/gnupgd91e6a428a824/p/bin/gpg
WORK=/storage/Users/currentUser/tmp/pgpgpg-r3-50035
OUT=/storage/Users/currentUser/tmp/pgpgpg-r3-50035/out
CANDIDATES= /storage/Users/currentUser/tmp /data/storage/el2/base/cache /data/storage/el1/base/cache /data/storage/el2/base /data/storage/el1/base /storage/Users/currentUser/tmp
E_CANDIDATES= /data/storage/el2/base/cache /data/storage/el1/base/cache /data/storage/el2/base /data/storage/el1/base
AGENT_LEFT=0
t02=/storage/Users/currentUser/tmp/ch/home-pgpgpg/p/gnupgd91e6a428a824/p/bin/gpg --no-batch --set-filename stdin --output /storage/Users/currentUser/tmp/pgpgpg-r3-50035/out/t02.asc --armor --store 
conan-create.log sha256=aa70a1ff6645c064cf257b4d81547700014c6c7de25e3072eb19260803b2a9d8（本窗 hashlib 现算；旧值 da0edde8… 系整改前一轮，作废）
```

## 构建期另有两条读数（照实记）

- `make check -j20` 里 make 的 jobserver 建 fifo 被拒：`make: jobserver mkfifo: /storage/Users/currentUser/tmp/GMfifo57369: Operation not permitted`（与问题表第 7 行同一根因 —— hmdfs 不支持特殊 inode；make 继续跑完，不影响 rc）。
- 编译有 1 条上游自身告警：`pgpopts.c:633:13: warning: add explicit braces to avoid dangling else [-Wdangling-else]`。

## 验证结果（HEAD 实测，2026-09-28 收尾-7 按日志回填）

- 编译状态：通过（`conan create` 于 ohos-aarch64 profile 成功；`conan-verify` Verdict=PASS、G0–G4 全 ✅）
- `.ci-result.json`：`timestamp=2026-09-28T12:52:00.939073`、`exit_code=0`、`integrity_hash=17356ac68ccafca7`、`log_sha256=15fac43729cb94ad8ce533b6cad8cbe681fe106bd41c399c6162818c98ca84f7`（与 `reports/w3-local-ci.log` 现算 sha256 逐字相同）
- 上游注册用例：0（`grep -n TESTS Makefile.in` → RC=1；`Makefile.in:285 check-am: all-am` 空转）
- 消费者断言：`TEST_SUMMARY discovered=32 passed=32 failed=0 skipped=0`（`reports/conan-create.log:488`、`reports/w3-local-ci.log:616`）
- `reports/conan-create.log` sha256：`aa70a1ff6645c064cf257b4d81547700014c6c7de25e3072eb19260803b2a9d8`（本脚本 hashlib 现算）


- 适配路径：A（Autotools 配方 + 设备端消费者测试）
- 使用知识库：`archives/a/abnfgen/0.21` 同形态先例、`archives/a/abx/0.1/conanfile.py:166` 与 `archives/a/abiword-plugin-gdict/3.0.8/conanfile.py:189`（`self.dependencies.build[...]` 取 tool_requires 的 package_folder）、`knowledge/operations/dependency-resolution.md:286`（`--with-<dep>=$PREFIX` 传参形态）
- 知识库扩展：无（B 判定 = **hit(E428)**，命中既有条目 `knowledge/graph/E428.kv`「test_package 以 package_folder 绝对路径递交被打包的工具，绕开 OHOS bash 丢 PATH」⇒ 按「一 PR 一知识」不新增草稿、不建 Issue；下面 §B 判定证据是取证棒的逐词查重账，其中「建议 none」是**初判**，终判以登记表与本行为准）
- 关联 Issue：无

## B 判定证据（行号级并排读数）

宽口径逐词 `grep -rn -i <词> knowledge/`（排除 `knowledge/drafts`）+ 手工 `grep knowledge/drafts/`，基线 `48d9cee684`：

| 检索词 | `knowledge/`（非 drafts） | `knowledge/drafts/` |
|---|---|---|
| `with-gpg-path` / `GPG_PATH` | 零命中 | 零命中 |
| `execv` | 仅 `knowledge/doc/E260.md:20,24,28` / `knowledge/graph/E260.kv:12` —— 讲 `fexecve` + ELF magic + 描述符绑定防 TOCTOU，与"argv[0] 必须是绝对路径"不是同一机制 | 仅 `DRAFT-4033-binwalk-2.3.4-ohos-python-subprocess-path-search`（`execve('tar')` 不搜 PATH → `shutil.which()` 解析）与 `DRAFT-8958-clthreads-makefile-stage-install-shadow`（`execvp` 对不可执行文件报 127） |
| `configure --with` | 仅 `knowledge/operations/dependency-resolution.md:286` `parent_configure_args: "--with-openssl=$PREFIX"`（子任务 objective 示例，非 OHOS 机制条目） | `DRAFT-E5xx-nagios-with-temp-dir-tmpdir-shadow`、`DRAFT-osi-0.108.11-glpk5-lpx-api-removal` 等（都是"用 --with-* 指路径"的通用形态，机制各属别的问题） |
| `tool_requires` | 零命中 | `DRAFT-10251-libnfc-tools-...`（用 tool_requires 封装测试框架）、`DRAFT-11301-ohos-compile-fail-suite`（parallel 作 tool_requires） |
| 本轮新增面：hmdfs 不支持路径型 socket inode / `mkfifo`、hmfs 支持；`/proc/<pid>/cmdline` 可作 execve argv 记录接缝 | 本轮按任务书不建草稿、不建 Issue，未做归属判重 | 同左 |

- 三族已知坑经行号级否证**不适用**本包：38 文件内无 `config.guess`/`config.sub`，`configure.in` 无 `AC_CANONICAL_HOST` ⇒ E007 / DRAFT-E564 / config-sub-silent 不适用；`grep "mktemp -d"`、`grep "umask 077"` 于 `configure` 均零命中 ⇒ abnfgen 的 `_patch_configure_mktemp` 不适用。
- （取证棒初判 `B判定 = none`，**已被终判 hit(E428) 取代**——本包 `test_package/conanfile.py` 两个二进制都按 `package_folder` 绝对路径递交，正落 E428 处方；上表的逐词查重账仍有效，它证明的是「**没有需要新建条目**的空白区机制」，与 hit 既有条目并不矛盾。）
- 终判理由：本包没撞出需要新建知识点的东西：取证新增的那条事实（hmdfs 不支持路径型 socket inode 与 `mkfifo`、hmfs 支持）**属平台面知识但归 gnupg/环境线**，按任务书不在本包建草稿、不建 Issue。**判定权在主理。**

### 对话 #1

- 第 1 棒（取证段，终态零提交）已核实并沿用，未重跑：官方直链可达性（200 / 53135B）、`/proc` 假前提否证、三族已知坑不适用性、`configure` 的 gpg-path 接缝定位、`gnupg/2.4.9.1` 发布态与真机可跑性、preflight/slot/gate 前置。
- 第 2 棒补完的取证：sha256 落实为完整 64 位并与 Debian `.orig` 逐字节对：官方直链与 `https://deb.debian.org/debian/pool/main/p/pgpgpg/pgpgpg_0.13.orig.tar.gz` 均为 53135B、同值 `905e1d2c60715a733f30e7469e9255370d69858abfe0c7d4972b10cb0165cbc3`，`diff -rq` 两棵树 RC=0（零差异）。`.orig` 只用于本地对账，**不进 conandata**（`scripts/ohc/preflight.py:361` 把 deb.debian.org 等判为 Debian 下游重打包源）。
- 第 2 棒停在 G2 红（当时 2 pass / 5 fail），未删断言、未改阶段掩盖缺口；其 `candidate` 记账随本轮端到端跑通而更新。

### 对话 #2（第 3 棒：真端到端与门禁收口）

- 按取证结论把端到端腿的 `GNUPGHOME` 换到 hmfs 可写根后，私钥腿在本机全流程跑通：keygen rc=0、四枚 `srwx------` socket、`pgpgpg -e` → `pgpgpg -d` 的 armor 与二进制两条腿都与明文 `cmp` 逐字节一致。
- 测试脚本重写为 T（翻译面，必跑）/ E（端到端，可降级但逐条显式 SKIP）两组；`discovered/passed/failed/skipped` 与逐臂台账都由实际计数器产出。翻译面的 argv 记录用内核侧 `/proc/<pid>/cmdline`（held-stdin 阻塞被 exec 的 gpg），因此**产物保持默认构建**，未为测试开 `--enable-debug`。
- 产物一律写到按 pid 唯一的分址 `$OUT`，正反两轮（框架 L1e 会移走产物后再起一次 `conan test`）不复用同一份文件；工作目录只从绝对环境变量推导，不用 CWD（conan `test()` 里 `getcwd` 不可靠，实拍 `shell-init: error retrieving current directory`）。
- 本棒未验证 / 不背书的点：①未做 W4 独立审计（不自审）、未建 PR、未碰任务登记表与平台、不下"可以提审"结论；②E 组的**降级路径**在本机没触发（hmfs 可用），`SKIP` 文本与计数口径只经过代码走查、没有真跑出一条降级读数；③PGP 长选项 `+keyword` 族没进断言面（上游选项校验先把 `+charset=utf-8`、`+batchmode=true` 拒掉了，见"已知限制"），`+batchmode` 不带值时是否等价于 true 未测；④`gpg-connect-agent KILLAGENT` 的收尾只在端到端腿跑过时经过。

状态：built（第 4 棒 2026-09-25 23:03 起 conan-verify 全绿；此前该处记 candidate，其时 G2 尚 FAIL）
---

**编译结束**: 2026-09-28 12:50
**最终状态**: built
