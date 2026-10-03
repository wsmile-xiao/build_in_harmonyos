# spinner 1.2.4 适配笔记

## 软件识别（W0 前置澄清）

"spinner 1.2.4" 在生态里存在多个同名包，先排除歧义再动手：

| 候选 | 1.2.4 是否存在 | 结论 |
|------|---------------|------|
| PyPI `spinner` | 否（最新 1.2.0） | 排除（且非 C/C++，R47 也不通过） |
| npm `spinner` | 否（最新 0.3.4） | 排除 |
| conancenter / ohpcd | 无该配方 | 首次适配，版本号用上游版本 1.2.4（R37） |
| **LAFFEY spinner** | **是（1.2.4，2003-02-17）** | **本次适配对象** |

**spinner 1.2.4 = Joe Laffey（LAFFEY Computer Imaging）的 VT100 防空闲守护进程**，
GPL-2，仅 `spinner.c` + `usage.c` 两个编译单元，纯 POSIX（termios/fork/signal/
select），**零第三方依赖**（只链 OHOS musl libc），交付物是单个可执行文件 `spinner`。

- 上游主页：http://www.laffeycomputer.com/spinner.html（GPL，版本自述 1.2.4）
- 语言预检（R47）：`detected=c`，任务语言 cpp 兼容族 → 通过。

## 依赖发布检查（W0）

spinner 无任何 `requires`/`tool_requires`，只依赖系统 libc ⇒ 依赖检查为空集，
不存在 `dependency_missing` 风险。CI 侧 PF4 依赖闸同样无包可探测。

## 编译环境

- 构建系统：autotools（上游自带 autoconf 2.13 时代生成的 `configure`，非重新 autoreconf）
- 编译日期：2026-10-01
- 编译器：clang 15（OHOS aarch64 profile，`aarch64-linux-ohos`）
- profile：`ohos-aarch64-wsl`（host/build 同 profile，与 CI 一致）
- 状态：built

## 源码获取（R39）

上游官方站点只提供**明文 HTTP**，且下载文件名不固定
（`spinner-current.tar.gz`），不可复现，因此不作为配方源。
采用 MacPorts 官方 distfiles 镜像（`sysutils/spinner` Portfile 所引用的同一
distfile）：

```
https://distfiles.macports.org/spinner/spinner-1.2.4.tar.gz
sha256 = 13419c4410db739020532e0628e1b6f7321db102739f3b1b88f105b29a2fcbb2
```

**交叉核验**：同一 distfile 从 FreeBSD `distcache.freebsd.org` 下载后与 MacPorts
副本 `cmp` 逐字节一致，sha256 相同 ⇒ 镜像未被篡改/替换。
（FreeBSD distcache 本身 HTTPS 在本环境不可达，故选 HTTPS 可用的 MacPorts。）

## 上游测试清点（R51 三步法第一步）

| 检查项 | 实测结果 |
|--------|----------|
| `tests/` 或 `test/` 目录 | 不存在 |
| tarball 内 test*/check*/RUNTEST 文件 | 0 个 |
| `Makefile.am` 中 `TESTS` / `check_PROGRAMS` | 无（只有 `bin_PROGRAMS = spinner`） |
| 生成的 `Makefile` 的 `check:` 目标 | 空壳，`checked target = "all"`，不执行任何断言 |

⇒ **上游测试用例数 = 0，assertion_count = 0**。不是"没跑"，是"确实没有"。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 同名包歧义 | PyPI/npm 也有 spinner，版本号都不含 1.2.4 | 逐一核对版本清单 + 上游主页自述版本，确认是 LAFFEY C 程序 |
| 2 | 上游源不可用 | 官方站仅 HTTP 且文件名不固定 | 改用 MacPorts HTTPS distfiles 镜像 + sha256 + 与 FreeBSD 副本逐字节比对 |
| 3 | `generate()` 报 `'AutotoolsToolchain' object has no attribute 'cache_variables'` | 本仓 conan 2.29.1 的 `AutotoolsToolchain` 无该属性 | 去掉 `cache_variables` 写法（该版本通过构造参数 `prefix` 传前缀） |
| 4 | 产物落在 `p/root/.conan2/.../prefix/bin/`（路径翻倍） | 给 `--prefix` 传了**绝对路径**，`make install` 的 `DESTDIR=` 会被拼在其**前**，形成 `DESTDIR + 绝对前缀` | `--prefix` 保持默认 `/`，由 `Autotools.install()` 自动加 `DESTDIR=<package_folder>`，产物落在 `<pkg>/bin/spinner` |
| 5 | 试过 `prefix="prefix"` 相对路径 | autotools 强制要求绝对路径 | 报 `expected an absolute directory name for --prefix: prefix`，回退到方案 4 |
| 6 | D2 断言失败 | 我按猜测写了 `is not VT100 compatible`，实测上游文案是 `Unable to determine TERM type` | 读 `spinner.c`/`usage.c` 源码核对真实文案后改断言（禁止按想象写断言） |
| 7 | F8 断言恒失败 | gate 表达式写坏（`grep ... && [...] && echo 0 \|\| echo 1` 优先级） | 先取计数到变量再比较，附实测值打印 |
| 8 | 本地 JC1/JC5 红灯 | **全仓扫描**命中其它包的存量垃圾（cloog/kics/libbfio/thc 的 `.staging-verified`），经 `git cat-file` 确认均存在于 `origin/main`，与本 PR 无关 | 生成 `pr.diff` 后以 `JUNK_PR_DIFF` 单包口径重跑（同 2048.c 既有做法），JC 全绿 |
| 9 | **W4 独立审计：E 组只能抓到 1 帧** | spinner 守护进程化，前台父进程 fork 后即退出，`script` 随之销毁 pty；实测 `timeout` 6/12/20 秒都只有 12 字节 1 帧 | 用 `script -qc "sh -c '$BIN -F -T 1; sleep 6'"` 挂住 pty，并新增“帧数 ≥3”“4 字形至少出现 3 个”断言（E2/E3），实测 6~14 帧轮转 |
| 10 | **W4 独立审计：manifest 记录了从未传入的 `--host`** | CI host/build 同 profile ⇒ `cross_building()` 为 false，configure 不注入 `--host`（日志实测 `cross compiling... no`） | `configure_options` 改为实际传入的参数，并补 `target_triplet` 与说明注释 |
| 11 | **W4 独立审计：E2 帧数恒为 0** | 我把含 `[`/`]` 的 VT100 序列当**正则**传给 `grep -o`，被解释成字符组 | 改用 `grep -F`（定长字符串匹配），并按字形逐个 `grep -q -F` 统计 |
| 12 | 文件缺少末尾换行（code_style §21） | 写文件时未补换行 | 8 个文件全部补齐 LF 末尾换行并逐一核验（`cr=0`） |
| 13 | **CI #66196 红：`config.status: Permission denied ... confstatXXXXXX/subs.sed`** → `make: *** No targets specified and no makefile found` | HMDFS 强制给新建目录置 setgid 位，`umask 077` 建出的 `./confstatXXXXXX` 变成 `drwx--S---`，连属主都无法在里面写文件，config.status 写不出 subs.sed/subs.frag/out ⇒ Makefile 根本没生成 | 按 **E011/E129** 加 `patches/0001-configure-hmdfs-umask.patch`，把 configure 里 2 处 `umask 077` 改 `022`（与 jpcre2 先例同形） |
| 14 | **CI #66196 红：`make: jobserver mkfifo: .../tmp/GMfifoNNNNN: Operation not permitted`** | 并行 make 需在临时目录建 FIFO 做 jobserver，HMDFS 不允许 | `autotools.make(args=["-j1"])` **且** `autotools.install(args=["-j1"])`（install 不继承 make 的 args，否则会重新附加 `-jN`） |
| 15 | **CI #66242 红：`FAIL E1 - daemon run on a pty emits output (bytes=0)`**（编译已通过，`Packaged 2 files: spinner, COPYING`，A1–D7 全过） | 本地 `script` 会把会话同时写到 stdout 和 typescript 文件，原实现把 typescript 指向 `/dev/null` 恰好两边都能取到；**worker 上的 `script` 只写 typescript 文件**，于是 `/dev/null` 把输出全丢了 | typescript 改为**真实文件** `spin.ts`，断言在 `cat spin.ts spin.out` 的并集上统计帧数（两种实现都覆盖） |
| 16 | 隐患：`script` 可能不接受合并写法 `-qc` | 不同实现对 `-qc` / `-q -c` 支持不一致 | E 组先用**探针命令**（`PTYPROBE`，与 spinner 无关）依次试 `-qc` 与 `-q -c`，探针成功才跑 spinner；探针失败则该组记 skipped 并显式打印，**绝不把 runner 差异误报成 spinner 缺陷**（`script(1)` 时代 E 组共 8 条断言，见下方历史小节） |
| 17 | **CI #66256 红：`FAIL E1 - daemon run on a pty emits output (bytes=0)`**（#66242 的 typescript 修复未奏效）| 探针证明 `script` 能执行并抓到普通命令输出，但 spinner 仍 0 字节 ⇒ 缺的是**控制终端**而非输出通道：worker 的 `script` 不给子进程可用 controlling terminal，而 spinner `OpenTTY()` 要求 `isatty()` | 弃用 `script`，新增 `test_package/pty_capture.py` 用 python3 `pty.openpty()` 自建 pty，spinner 前台跑在 slave 上并在父进程退出后继续读 master；实测 84 字节 / 7 帧（详见下节四种方案对比） |
| 18 | **CI #66303 红：`FAIL E2 - daemon run on a pty emits output (bytes=0)`**（采集器 rc=0，pty 分配成功，但 spinner 仍未写任何字节）| 无头 HarmonyOS runner 上 `pty.openpty()` 能建 pty，但 spinner 前台写 tty 的能力不可用：spinner 的 `OpenTTY()` 要 `isatty()` + `tcdrain()`，且 fork 后 `setsid()`/`chdir("/")` 并按路径重开 tty —— 该组合在 worker 上不成立。**属于 runner 能力边界，不是已证实的 spinner 缺陷** | pty_capture.py 增加**能力探针**（先做 pty 字节往返 + 按路径重开，两者任一失败即 exit 3）；test.sh 在 rc=3 时把 E1–E9 记为 **skipped 并打印证据**，不记为通过（同 tack 先例口径） |

## CI 第二次失败复盘（构建 #66242）

#66196 的 umask 修复**已生效**：日志显示 `Package ... built`、
`package(): Packaged 2 files: spinner, COPYING`，测试跑到 D7 全过。
剩余唯一失败点前移到了 E 组：

```
ok A1 … ok D7
FAIL E1 - daemon run on a pty emits output (bytes=0)
```

根因是 `script` 的输出通道差异（见上表 #15/#16）。这里特别值得记录的一点：
**本地 WSL + qemu 下 `script` 两个通道都写，掩盖了这个缺陷**；
只有在真实 worker 上才暴露。教训：pty 相关断言不能只靠"本地跑通"，
要显式覆盖"不同 runner 实现"的分支，并用探针把环境问题与被测缺陷分开。

> **历史小节（`script(1)` 时代，已被下面的 `pty_capture.py` 方案取代）**
> 下表记录的是第 #66242 轮 `script(1)` 方案的实测结果，当时 E 组共 **8** 条断言、合计 **37** 条，
> 故末行为 `29/29，skipped 8`。**这些数字描述的是历史状态，不是当前状态**；
> 当前状态见下方「CI #66303 后」小节的 `pty_capture.py` 实测表（E 组 9 条、合计 38 条、
> skipped 9）。历史数字原样保留以备追溯。

四种环境组合的本地实测（均已验证）：

| 环境 | 结果 |
|------|------|
| util-linux `script`（两通道都写） | 37/37 |
| 只写 typescript 文件的 `script`（模拟 worker） | 37/37 |
| 拒绝 `-qc`、只接受 `-q -c` 的 `script` | 37/37 |
| 完全没有 `script` | 29/29，skipped 8（显式 `[skip]`） |

## CI 失败复盘（构建 #66196 / worker OpenHarmonyPCDeveloper-CI-033）

分层判定为 **C 类（内容缺陷）**，非 worker 故障：7 个步骤里
`worker_preparation / worker-prep / git-clone / checkout-pr / conan-setup`
**全部 ✅**，只有 `conan-build-test` ❌；且 G0/L0（含 L0n 分支名校验）/
KC/JC 六项门禁均 `pass`，构建耗时 18s 属于真实编译而非环境超时。
若为 worker 故障，失败会落在 `worker-prep`/`git-clone`/`conan-setup` 且耗时 <1s。

关键失败输出：

```
./config.status: line 444: ./confstatdciLGl/subs.sed: Permission denied
./config.status: line 526: ./confstatdciLGl/subs.frag: Permission denied
./config.status: creating Makefile
./config.status: line 697: ./confstatdciLGl/out: Permission denied
mv: bad './confstatdciLGl/out': Permission denied
config.status: executing depfiles commands
spinner/1.2.4: RUN: make -j20
make: jobserver mkfifo: /storage/Users/currentUser/.cache/tmp/GMfifo23631: Operation not permitted
make: *** No targets specified and no makefile found.  Stop.
```

根因链：HMDFS setgid + `umask 077` ⇒ `config.status` 写文件失败 ⇒
**Makefile 未生成** ⇒ 后续 `make` 无从下手（"no makefile found" 是**结果**而非原因，
不要去修 make）。

另外注意日志里的 `[fail] [Errno 2] No such file or directory: 'curl'` 只是
**预下载**阶段没有 curl（worker PATH 无 curl），conan 自身下载成功
（`Sources correctly downloaded from https://distfiles.macports.org/...`），
**非致命**，无需处理。

## 配方关键点

- `package_type = "application"`；`package_info()` 只给 `bindirs = ["bin"]`（无库产出）。
- R39：源 URL 为 HTTPS 权威镜像，附 sha256。
- 源码补丁：`patches/0001-configure-hmdfs-umask.patch`（HMDFS umask 022，见上），
  由 `build()` 里的 `apply_conandata_patches(self)` 应用。**注意**：`basic_layout`
  下 configure 实际从 `source_folder`（`.../p/b/spinnXXX/b/configure`）执行，与
  `patch()` 的默认 cwd 一致，无需 `chdir`。补丁不含任何平台宏（R8 合规）。
- 并行度：build 与 install 均固定 `-j1`（HMDFS jobserver FIFO 限制）。
- R38：产物含可执行文件 ⇒ 软件级 `archives/s/spinner/commands.json`
  （`type=tool`，`ref=spinner/1.2.4`，`binary=false`），CI L0k 已校验通过。
- R33：`build()` 全部走 `Autotools` helper，**不裸用** `${CC}`/`${CFLAGS}`；
  编译器由 `AutotoolsToolchain` 从 `conf:tools.build:compiler_executables` 取。
- R49：prefix 保持 `/` + DESTDIR staging，不注入 `/usr/local` 等共享前缀；
  F8/F9 断言实测产物内 `/usr/local`、`/storage/`、`/home/`、`/Users/` 计数均为 0。
- 源码补丁仅 1 个（HMDFS umask，见上），且**不含任何平台宏**，R8 合规。
- GPL-2：`COPYING` 随包安装到 `licenses/`。

## 测试用例情况（实测执行数）

上游 0 个用例；本次新增消费者行为断言 **38 条，全部实测执行并通过**
（`conan create` 输出 `consumer assertions passed: 38/38 (skipped: 0)`）：

| 组 | 条数 | 内容 |
|----|------|------|
| A | 5 | `-L` 授权路径：退出码 64（`EX_USAGE`）、版本横幅、GPL 版权行、授权声明、stdout 为空（spinner 全部输出走 stderr） |
| B | 5 | 非法选项 `-Z`：退出码 64、诊断信息、usage 概要、返回码契约、**14 个开关全量渲染** |
| C | 1 | `--version` 被拒（spinner 无长选项）→ 证明无静默成功 |
| D | 7 | **鸿蒙特有**：TERM 兼容性守卫（无 TERM / 非 VT100 TERM 均退出 1、诊断文案、-T 建议、失败不留 pid 文件） |
| E | 9 | **鸿蒙特有**：pty 上守护进程**持续旋转**（python3 `pty.openpty()` 自行分配 pty），断言采集器 rc=0、≥3 帧、≥3 个不同字形、四段 VT100 序列齐全、`-F` 不建 pid 文件 |
| F | 9 | **鸿蒙特有**：ELF64 / `Machine: AArch64` / DYN-EXEC / 解释器在 `/lib` / `DT_NEEDED` 含 `libc.so` / 无绝对路径 NEEDED / 无宿主路径泄漏 |
| G | 2 | 交付面：`bin/` 恰好 1 个条目、名为 `spinner` |

**鸿蒙特有测试 = 25 条（D+E+F），满足 PR 要求 N≥1。**

### E 组为何要“挂住 pty”（审计发现并修正）

spinner 是**守护进程**：前台父进程 fork 子进程后立即退出。若直接
`script -c "$BIN -F -T 1"`，`script` 随父进程退出而销毁 pty，实测无论
`timeout` 设 6/12/20 秒都只能抓到 **1 帧 12 字节**（重复实测确认），
即测试只能证明“吐过一帧”，无法证明“在转”。

修正方式是在同一 shell 里让子进程保持前台并追加 `sleep` 撑住 pty：

```sh
TERM=vt100 timeout 20 script -qc "sh -c '$BIN -F -T 1; sleep 6'" /dev/null > spin.out
```

实测抓到 **6~14 帧**，字形按 `\` `|` `/` `-` 轮转，E2/E3 据此断言“帧数 ≥3”
且“4 个字形中至少出现 3 个”。**注意不能用 `&` 放后台**——那样子进程失去
控制终端，写入已销毁的 pty 会 SIGSEGV（实测 0 帧），已在本组注释中标注。

另外 **spinner 拒绝向非 tty 写入**（`OpenTTY()` 里的 `isatty()` 检查 +
`tcdrain()`），所以"把输出重定向到普通文件"**不能**替代 pty——这条约束决定了
E 组必须真的分配 pty，也决定了 typescript 必须指向真实文件而非普通文件。

### 补全说明

上游无任何测试，因此不存在"修改上游用例"的情况；全部 38 条均为**新增消费者
行为断言**，每条都真实执行已安装二进制并以**退出码 + 真实 stderr / pty 字节流**
判定，无 `echo`/`print` 空壳。CI L1e 破坏性反向验证（把 `bin/` 移走再跑）
确认测试与被测包真实耦合。

### 条件跳过项（如实披露，不记为通过）

E、F 两组依赖宿主工具/能力，缺失时按 **skipped** 计入并在汇总行显式打印
（`skipped` 计数不参与通过判定），不会伪装成 `ok`：

| 环境 | 通过 | skipped |
|------|------|---------|
| `python3` 与 `readelf` 均可用（本次本地实测） | 38 | 0 |
| 无 `python3`（pty 采集器不可用） | 29 | 9 |
| 无 `readelf` | 29 | 9 |
| 两者皆无 | 20 | 18 |

> E 组的"可用"由**探针**判定（见上表 #16），探针本身用 `PTYPROBE` 而非 spinner，
> 因此 runner 的 `script` 行为差异只会导致 skip，不会伪装成 spinner 缺陷。

### E 组为何改用 python3 `pty.openpty()`（CI #66256 定位）

CI #66242 我按"`script` 只写 typescript"修了一轮（typescript 指向真实文件 + 双通道并集），
CI #66256 仍然 `FAIL E1 (bytes=0)`。这次加的探针反而给出了决定性证据：
探针 `printf PTYPROBE` **成功**、`script` 能正常执行并抓到输出，而 spinner 仍是 0 字节
——说明**问题不在输出通道，而在"控制终端"**：worker 上的 `script` 不给子进程可用的
controlling terminal，而 spinner 的 `OpenTTY()` 恰恰要求 `isatty()`。

逐项实测排除了三种替代方案：

| 方案 | 实测结果 |
|------|----------|
| `script` + 真实 typescript + 并集 | CI 上仍 0 字节（不给可用控制终端） |
| `pty.openpty()` + spinner `-t <slave>` | **rc=64**：spinner usage 是 `spinner[-IntTuvl<path>...]`，路径必须**紧贴**选项；分离写法 `-t /dev/pts/3` 直接 EX_USAGE |
| `pty.openpty()` + spinner `-t<slave>`（紧贴） | **退出 -11（崩溃）** |
| **`pty.openpty()` + spinner 前台跑在 slave 上** | **84 字节 / 7 帧，四字形齐全** ✅ |

最终实现放在 `test_package/pty_capture.py`：`openpty()` 分配 master/slave，
spinner 以 `stdin/stdout/stderr = slave` + `start_new_session=True` **前台**运行，
并且**在守护进程父进程退出后继续读取 master 直到时间窗结束**——这正是能观测
"持续旋转"（7 帧）而不是"只吐过一帧"（1 帧）的关键。

本地稳定性验证：从仓库根目录/相对路径/绝对路径三种调用方式均 38/38；
连续跑 3 次均 38/38 且无残留 daemon 进程。


### CI #66303 后：E 组改为"能力探针 + 如实 skip"（不再把 runner 边界当缺陷）

第三次红之后我停下来做了取舍（同一错误类别已 3 次，R43 阈值 5）。本地 WSL + qemu 下
`pty.openpty()` 路线**稳定 38/38**（84 字节 / 7 帧），而 worker 上 E1 rc=0（pty 建出来了）
但 spinner 仍 0 字节。继续靠"换一个 pty 姿势"去试，边际收益已经很低，且每一轮都在
消耗远端构建额度；而 `OpenTTY()` 的 `isatty()` + `tcdrain()` + `setsid()` + 按路径重开
这一组合在无头 runner 上确实不成立。

因此改为**先证明能力、再决定是否断言**（与 tack 先例对其"无头交互主循环"的口径一致）。
最初版的探针只有两步，存在假阴性（见下方"探针自身的假阴性"一节），现已扩为三步：

1. `openpty()` 后往 slave 写 `PTYPROBE`，从 master 读回（验证 pty 字节往返可用）；
2. 按 `ttyname(slave)` 路径重新 `os.open(..., O_WRONLY)`；
3. **完整复现 spinner 的守护进程序列**（用已知良好的写入者代替 spinner），
   即 `spinner.c` 里 `Daemonize()` + `OpenTTY()` 真正做的事：
   `fork()` → 子进程 `setsid()` → `close(0/1/2)` →
   `open(ttyname(STDIN), O_WRONLY)`（按路径重开）→ `isatty()` →
   `tcdrain()`（drain 后再写）→ `write()`；父进程同时监视 pipe 与 pty master，
   确认复现进程写出的字节真的回到了 master。

> 第 3 步必须**自行分配一条私有 pty**，不能复用第 1/2 步那条：最后一个 fd 关闭时内核会
> 销毁 pty 设备并 unlink 它的 `/dev/pts/N` 入口，之后再按路径 `open` 必然 ENOENT。
> （这是实现过程中实测踩到的真实坑：初版复用同一条 pty，复现恒在
> `open-by-path:[Errno 2] No such file or directory: '/dev/pts/2'` 处失败。）

退出码语义据此细分，让"环境不可用"与"被测程序有缺陷"**不可能再被记成同一件事**：

| helper 退出码 | 含义 | test.sh 处置 |
|---------------|------|--------------|
| 0 | spinner 抓到了 VT100 帧 | 跑 E1–E9 全部严格断言 |
| 3 | **已证明**宿主无法完成该序列（复现本身失败） | E1–E9 记 **skipped**，打印复现诊断与实际字节数，`declared_not_passed=true` |
| 4 | **复现通过**，但 spinner 零字节 | **E1 判 FAIL**（真实产品回归），E2–E9 无从评估，记 skipped |
| 2 | 用法错误 | skip |

探针整体包在 `try/except` 内：**任何未被证明的能力都归为 exit 3**（skip），
而不是抛一个 Python 栈出来。

四条路径都已本地实测（`test_package/pty_capture.py` 直接调用）：

| 场景 | 注入方式 | helper rc | 判定 |
|------|----------|-----------|------|
| A 真实 spinner、宿主有能力 | 无 | **0** | 84 字节 / 7 帧 |
| B 第 1/2 步受限 | `sitecustomize` 令所有 `O_WRONLY` open 失败 | **3** | `probe could not complete: HostLimitError(13, ...)` |
| C 仅第 3 步受限 | `sitecustomize` 只在 `setsid()` 之后（`getsid(0)==getpid()`）令 open 失败 | **3** | `daemon-sequence replica failed at unexpected:(13, ...)` |
| D 复现通过但产物静默 | 传入一个 daemon 化却不写帧的 shim | **4** | `replica passed but spinner produced 0 frames => product defect` |

`test.sh` 两条分支的端到端实测（stub 掉 helper，只验分支处置）：

| helper rc | test.sh 输出 | 退出码 |
|-----------|--------------|--------|
| 4 | `FAIL E1 - ... host daemon-sequence replica PASSED => product defect, not a runner limit` | **1** |
| 3 | `[skip] E1-E9: host cannot support spinner's daemon/pty sequence`，汇总 `29/29 (skipped: 9)` | 0 |

完整门禁下的两条主路径：

| 场景 | 结果 |
|------|------|
| pty 可用（本地真实环境） | **38/38，skipped 0** |
| pty 不可用（注入模拟 worker） | **29/29，skipped 9**，并打印复现诊断证据 |

这样既不掩盖真实缺陷（复现通过却静默一律 FAIL），也不把 runner 能力边界
伪装成 spinner 的 bug，更不伪装成通过。

> **结论口径（如实声明）**：VT100 持续旋转这一档能力已在**本地 WSL 环境**完整验证
> （84 字节 / 7 帧 / 四字形）。**该结论尚未在 HarmonyOS CI runner 上复验**——
> 构建 #66327 的完整日志平台侧取不到（`/ci/builds/66327`、`/pulls/14154/ci`
> 均 404，CI 看板页面是 SPA 不含日志），因此无法确认 worker 当时走的是
> rc=3（已证明不支持）还是 rc=4（支持却静默）。本次整改把这条歧义变成可判定问题：
> 下一次 CI 若 E 组报 skipped，说明 worker 上连复现也过不去（rc=3，runner 边界成立）；
> 若报 `FAIL E1 ... replica PASSED`，那就是一个**真实的产品缺陷**，需要正面修 spinner
> 在 OHOS 上的行为，而不是继续 skip。
> PR 中的鸿蒙特有测试以 **D 组 7 条 + F 组 9 条 = 16 条已在 CI 上实测通过**为准，
> E 组 9 条按 skipped 申报。

## CI 构建 #67399 复盘：worker 基础设施故障（D 类，非内容缺陷）

MR !14154 整改后第一次触发 CI，落到 worker `OpenHarmonyPCDeveloper-CI-023`，
结果 **CI 校验失败**。分层判定为 **D 类（worker 故障）**，与本次整改的代码无关。

步骤表只有 4 步，**`conan-build-test` 根本没出现**——仓库都没 clone：

| 步骤 | 结果 |
|------|------|
| worker_preparation | ✅ |
| worker-prep | ❌ |
| git-clone | ❌ |
| cleanup | ❌ |

三个失败步骤的报错文本完全一致，且耗时都在 0.01s 以内：

```
eSSH bridge exec failed: connect failed: connection lost before ready:
   Connection was refused by other side: 111: Connection refused.
hprogram finished with exit code -1
helapsedTime=0.010305   (worker-prep)
helapsedTime=0.003320   (git-clone)
helapsedTime=0.004955   (cleanup)
```

这正是「worker 上起不来会话」的特征。与本文件已有的分层判据一致：
worker 故障落在 `worker-prep`/`git-clone`/`conan-setup` 且耗时 <1s，
内容缺陷只落在 `conan-build-test`（对照 #66196：那次前 5 步全 ✅、只有
`conan-build-test` ❌，才是内容缺陷）。

**机器人自动诊断是误判，特此更正**：诊断给的是「网络问题 / 源码下载超时 /
Worker 网络受限，已知可达 zlib.net、已知不可达 ftp.gnu.org」，并建议换镜像或
把源码预缓存进 conan 的 `s/`。这个结论不成立：

1. 该次构建**从未发生任何源码下载**——`git-clone` 就在 SSH 建连处失败，
   `conan create` 根本没被调用；
2. 日志提到的「不可达 ftp.gnu.org」与本包无关：本包唯一源码 URL 是
   `https://distfiles.macports.org/spinner/spinner-1.2.4.tar.gz`，从不访问 ftp.gnu.org；
3. 真实原因是 `Connection refused ... 111`（TCP 连接被拒），与 DNS 可达性无关。

因此**不采纳**「换镜像 / 预缓存」这条建议：照它改会动 `conandata.yml` 的权威 URL
与 sha256 绑定（R39/PF7），而实际问题根本不在那里。同 SHA 重复 `/rebuild` 只会
得到回执不排构建，故以本节记录 + 新提交的方式重新排队。

## 验证结果

```bash
# W3 本地编译验证（硬门槛）
conan create archives/s/spinner/1.2.4 --name=spinner --version=1.2.4 \
  -pr:h=ohos-aarch64-wsl -pr:b=ohos-aarch64-wsl --build=missing
→ rc=0，consumer assertions passed: 38/38 (skipped: 0)

# CI 同源门禁（单包口径 JUNK_PR_DIFF=pr.diff）
CI_PACKAGES="archives/s/spinner/1.2.4" zsh ci/conan/build_and_test.sh
→ rc=0，Pass rate: 100.0% (1/1)
   G0=pass  L0=pass  KC=pass(0 errors)  JC=pass
   L1=pass(test_package executed)  L1e=pass(负向验证)
   L2=skip(spinner 无 --version/--help，上游行为，非阻塞)
   L4=pass  L5=pass
```

> L2 说明：L2 探测 `--version` / `--help`，而 spinner 只有短选项
> （`-L`/`-h` 语义不存在），必然走 EX_USAGE 失败路径 —— 属上游既有行为，
> L2 本身标注 non-blocking，不影响判定。

> 构建形态说明：CI 的 host/build 使用同一 profile（均 os=OHOS arch=armv8），
> 故 conan 的 `cross_building()` 为 false，configure **不注入** `--host`；
> 目标三元组由工具链 shim 的 `--target=aarch64-linux-ohos` 指定。
> manifest.yaml 的 `configure_options` 记录的是实际传入的参数。

## 交付物

| 文件 | 说明 |
|------|------|
| `conanfile.py` | application 型配方（autotools + DESTDIR staging + COPYING） |
| `conandata.yml` | MacPorts HTTPS 镜像 + sha256，注册 1 个 portability 补丁 |
| `manifest.yaml` | 版本级 manifest |
| `test_package/` | 消费者测试（`test.sh` 38 条断言 + `pty_capture.py` pty 采集器 + `MANIFEST.yml` + `conanfile.py`） |
| `commands.json` | CLI 工具声明（R38，软件级） |
| `patches/0001-configure-hmdfs-umask.patch` | HMDFS umask 077→022（E011/E129），修 CI #66196 |

## 注意事项

- 上游 `configure` 是 autoconf 2.13 产物，**不要**加 `autotools.autoreconf()`
  （需要新版 autoconf/automake，且会引入不必要的构建漂移）。
- 该 `configure` 会因 `AC_PROG_MAKE_SET` 缓存而重复调用一次 `config.status
  --recheck`，产生重复 configure 输出——属上游正常行为，不影响构建。
- `make` 并行度由 Conan 决定（实测 `-j32`）；该工程仅 2 个编译单元，无竞态。
- 复跑本地 CI 前必须先 `git add` 新增文件生成非空 `pr.diff`，否则
  `JUNK_PR_DIFF` 口径会退回全仓扫描并被其它包的存量垃圾误伤。

---

**编译结束**: 2026-10-01
**最终状态**: built
