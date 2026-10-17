# E6340 — DJB 风格发行包在 OHOS 上的构建/安装陷阱与 supervise 测试缺口

## 基本信息

- **状态**: draft（待主编审查，协作者不 promote）
- **来源**: daemontools-encore 1.11 适配（HarmonyOS PC / HMDFS / HongMeng Kernel 1.12.0 / clang 15.0.4）
- **严重度**: 2
- **类别**: hmdfs, filesystem, install, testing, selinux
- **原始日志**: 版本目录 `reports/upstream-test.log.md`（逐用例）、`reports/upstream-install-scenarios.log.md`（安装三段场景）、`reports/make-clean-scenario.log.md`（`make clean` 误删 `MAN`/`TARGETS` 的原始复现）、`reports/fifo-probe-raw.log.md`（四类 FIFO 创建路径的原始 EPERM 输出）

## 错误特征

四类可独立出现的信号，均出自「上游按 GNU/Linux 文件系统语义写死构建/安装脚本」的软件包：

```
make: *** No rule to make target 'MAN', needed by 'install'.  Stop.
installer: fatal: unable to write .../share/man/man8/envdir.8: access denied
installer: fatal: unable to read setuser.8: file does not exist
supervise: fatal: unable to read supervise/control: file does not exist
mkfifo: cannot create fifo 'probe.fifo': Operation not permitted
```

检索用的 `error_signature` 只收录上面前四行与 `cannot create fifo '` 这五个**有区分度**的片段。
刻意**不收录**裸 `Operation not permitted`：它虽然出现在上列 FIFO 行的尾部，但同样出现在任何无关的
EPERM 报错上（`chmod`/`rename`/`bind` 等），收录后会让知识引擎在大范围报错上误命中本条目、把执行者
引向无关方向。FIFO 能力探测的另两种形态（`python3 os.mkfifo` / `os.mknod(S_IFIFO)` / AF_UNIX `bind`）
输出的都是无区分度的 `[Errno 1] Operation not permitted`，因此只作为**探测手段**记录在下方复现段与
`verification_cmd` 中，不作为检索签名。

## 触发条件

- 构建系统：DJB 风格 makefile（自写 Makefile + `conf-*` 配置 + 自带 `installer`），本条目在 daemontools-encore 1.11 实测
- 阶段：`make clean` / `make install` / 上游回归套件（`make rts`）
- 平台前提：OHOS HMDFS（大小写不敏感、目录模式落地后不可 chmod）+ 禁止用户进程创建 FIFO

## 根因分析

1. **大小写不敏感使 clean 清单误删内容文件**
   daemontools-encore 的 `TARGETS` 清单同时含 `man` 与 `targets` 两个名字，而发行版自带的安装清单就叫 `MAN`、清单自身叫 `TARGETS`。
   `make clean` 展开为 `rm -f $(cat TARGETS)`；在大小写不敏感的 HMDFS 上这两个名字互相命中，clean 于是删除了 `MAN`（安装清单）与 `TARGETS`（清单本体）。
   之后 `make install` 的依赖 `installer BIN conf-bin MAN conf-man` 找不到 `MAN`，报 `No rule to make target 'MAN'`。

2. **目录创建模式落地后 chmod 不再生效**
   上游 `installer.c` 对清单里的 `d` 行执行 `mkdir(target,0700)`，随后统一 `chown(-1,-1)` + `chmod(target,mode)`。
   HMDFS 上实测：`mkdir -m 700` 落盘为 `drwx--S--- 2700`，随后的 `chmod 0755` 不再改变模式；并且目录属主显示为共享属主 20001006，而进程 euid 是 20020084。
   结果是**创建它的同一个进程**也无法在其中创建文件：`installer: fatal: unable to write .../man8/envdir.8: access denied`。

3. **发行版清单引用了未随包提供的文件（上游打包不一致）**
   `MAN` 清单要求安装 `setuser.8`，但 1.11 的 tarball 既没有 `setuser.8`、也没有 `setuser.8.in`，Makefile 的 `man` 目标列表里只有 `setuidgid.8`（ChangeLog 显示 git 历史做过 `setuidgid.8 => setuser.8` 改名，发布包未同步）。
   因此未修补时任何平台的 `make install` 都必然以 `installer: fatal: unable to read setuser.8: file does not exist` 失败。

4. **FIFO 被拒导致 supervise 类测试无法执行**
   HarmonyOS 拒绝用户进程创建特殊文件节点：`mkfifo(2)`、`mknod(2) S_IFIFO`、`mknod` CLI 全部 EPERM，AF_UNIX `bind()` 同样 EPERM。
   `supervise` 需要 `supervise/control` 与 `supervise/ok` 两个 FIFO 做控制通道，创建失败后以 111 退出并打印 `unable to read supervise/control: file does not exist`。
   上游 `rts.tests` 的 `waitok` 辅助函数在 supervise 退出后无限轮询，所以聚合入口 `make rts` 永不返回（实测 1200s 超时、`rts` 输出为空），21 个用例中 9 个 supervise/svscan 用例因此在设备上无法得到结果（NOT_RUN），而不是失败。

## 解决方案

### 推荐方案（实测通过）

- 构建：不使用 `make clean`，改用 `make -j1 -B programs man`（全量重建且不删除任何文件）；
- 配置：按上游 README 的文档化接口写 `conf-cc` / `conf-ld`（clang + Conan 工具链 flags）与 `conf-bin` / `conf-man`（指向包内 `bin/`、`share/man/`），不打补丁改构建脚本；
- 安装：在 `package()` 里按 `MAN` 清单的 `d` 行预建目录（组可写），让 `installer` 的 `mkdir` 落到它已经实现的 `errno == error_exist` 分支，再执行上游 `make install`；
- 上游缺陷：把 `MAN` 的 `setuser.8` 行改成 `installer` 自带的可选前缀形态 `?c:::644:/man8/:setuser.8:`（源文件不存在时静默跳过，见 `installer.c` 的 `opt` 分支），补丁 `patches/0001-MAN-optional-setuser.patch`；
- 测试：不用 `make rts` 聚合入口，按用例运行 `00-preamble.sh + rts.tests/<case>.sh` 并与 `<case>.exp` 比对（与上游 `make rts` 同一份文件、同一个 `cat -v` + `diff -u` 口径），逐用例加超时；无法执行的能力型用例如实记 NOT_RUN，并在包内 smoke test 中先做 FIFO 能力探测：可用时跑完整的 supervise/svok/svstat/svc 周期，不可用时断言上游文档化的控制通道错误。

实测结果：`make install` 从 rc=2 → rc=0（20 个程序 + 19 个手册页）；`conan create` 全流程 rc=0；包内消费者用例 31/31 通过；上游用例 12/21 通过、9/21 因 FIFO 策略 NOT_RUN。

### 禁止做法

- ❌ `make clean` + `make programs`（HMDFS 上会删掉 `MAN`/`TARGETS`，必须重新解包才能恢复）
- ❌ 用 `chmod 0755 <dir>` 补救 `installer` 建的 0700 目录（chmod 在此文件系统上不生效）
- ❌ 用 `LD_PRELOAD`/桩实现伪造 FIFO 以"跑通" supervise 测试（改变被测语义，且违反工作区禁止用全局注入掩盖问题的口径）
- ❌ 把 9 个 supervise 用例写成 PASS

## 验证

```bash
# 0) 复现前先清掉命令行层注入，避免被自身配置污染结论
env | grep -E '^GIT_CONFIG_(COUNT|KEY|VALUE)' ; # 无输出即为干净基线
# 本设备 /tmp 是只读 erofs（mount 实测 /dev/block/dm-0 on /tmp type erofs (ro,...)），
# 探针统一放到可写目录：
D="${TMPDIR:-$HOME/tmp}/caseprobe"

# 1) 大小写不敏感 + clean 误删
mkdir -p "$D" && cd "$D" && printf 'x\n' > MAN
python3 -c "import os;print(os.path.samefile('MAN','man'))"   # 实测 True
rm -f man && ls MAN                                            # 实测 MAN 已消失
stat -c '%A %a' "$HOME"                                        # 实测 drwxrws--x 2771 (setgid + 属组可写)

# 2) 目录模式不可 chmod（installer 的 mkdir(0700) 场景）
(umask 077; mkdir -m 700 d); stat -c '%A %a' d                # 实测 drwx--S--- 2700
touch d/x                                                      # 实测 Permission denied
python3 -c "import os;os.chmod('d',0o755);import stat;print(oct(stat.S_IMODE(os.stat('d').st_mode)))"
                                                               # 实测仍为 0o2700，chmod 未生效
touch d/x                                                      # 实测仍 Permission denied

# 3) 发行版清单引用不存在的文件（在源码树内执行）
cd <upstream-pristine>/daemontools-encore-1.11
grep -n 'setuser.8' MAN                                        # 实测命中第 11 行
ls setuser.8                                                   # 实测 No such file or directory
grep -n '^man:' -A 2 Makefile                                  # 实测 man 目标只生成 setuidgid.8

# 4) FIFO 能力探测（四类创建路径，实际报错文本，rc 均为 1）
cd "$D"
mkfifo probe.fifo                                              # 实测 mkfifo: cannot create fifo 'probe.fifo': Operation not permitted
python3 -c "import os;os.mkfifo('p2',0o600)"                   # 实测 PermissionError: [Errno 1] Operation not permitted
python3 -c "import os,stat;os.mknod('p3',stat.S_IFIFO|0o600)"  # 实测 PermissionError: [Errno 1] Operation not permitted
python3 -c "import socket;s=socket.socket(socket.AF_UNIX);s.bind('p4')"  # 实测 PermissionError: [Errno 1] Operation not permitted
ls -la                                                         # 实测目录内无任何新节点（仅 . 与 ..）
```

完整实测记录：安装三段场景（未修补 + 未预建目录 / 未修补 + 预建目录 / 打补丁 + 预建目录）见
`archives/d/daemontools-encore/1.11/reports/upstream-install-scenarios.log.md`；
`make clean` 误删清单的原始复现（含 `make: *** No rule to make target 'MAN', needed by 'install'.  Stop.` 原文）见
`archives/d/daemontools-encore/1.11/reports/make-clean-scenario.log.md`；
上面第 4 步四类 FIFO 创建路径的**原始输出**（含设备与内核版本、工作目录、逐条 rc）见
`archives/d/daemontools-encore/1.11/reports/fifo-probe-raw.log.md`。

## 与既有条目的差异

- **E074 / E525**（鸿蒙 SELinux 禁止创建 FIFO，导致 `make -j` jobserver 卡住）只覆盖**构建期并行 jobserver** 这一面，修复动作是 `make -j1`。
  本条目的 FIFO 面是**运行期控制通道**：`make -j1` 完全无法规避（`supervise` 必须自己 `mkfifo`），后果是上游测试用例集合永久缺一块，修复动作只能是能力探测 + 如实记 NOT_RUN + 用客户端工具退出码语义补验证。
  反证命令（同一设备同时实测两者，实测输出见下）：
  ```bash
  make --version                          # 实测 GNU Make 4.4.1
  make -j4 programs; echo rc=$?           # 实测 rc=0，仅打印一行
                                          # make: jobserver mkfifo: /storage/Users/currentUser/GMfifo18479: Operation not permitted
                                          # 即 4.4.1 在 FIFO jobserver 失败后回退到管道 jobserver，构建照常完成
  supervise sv; echo $?                   # 实测 rc=111 + supervise: fatal: unable to read supervise/control: file does not exist
  ```
  结论：本设备当前策略下 `make -j>1` 并不因 FIFO 失败（E074/E525 的症状在本 make 版本上退化为一行噪音），而 `supervise` 必然失败——两者根因同源（特殊文件节点策略）但影响面、严重度与处置完全不同，把 supervise 缺口按 E074 处理（"改用 -j1 即修复"）会得出错误结论。

- **P020 / E016 系**（HMDFS 不支持硬链接与 FIFO）描述的是「创建失败」这一事实，未覆盖本条目的另外两处 HMDFS 语义：
  大小写不敏感导致**文件名清单类构建规则误删内容文件**，以及目录模式落地后 **chmod 无效**（P013 只声明平台限制是系统级差异）。
  反证命令（实测输出）：
  ```bash
  cd "$D" && mkdir -p c1 && cd c1 && touch AlphaBeta     # $D 见上文可写目录约定（/tmp 在本设备只读）
  ls alphabetA                                     # 实测列出 alphabetA（大小写不敏感解析，不报 No such file）
  python3 -c "import os;print(os.path.samefile('AlphaBeta','alphabetA'))"   # 实测 True
  ```
  即 HMDFS 把 `AlphaBeta` 与 `alphabetA` 解析为同一文件——这正是 `MAN`/`man`、`TARGETS`/`targets` 互相命中的机制，与硬链接/FIFO 能力无关（因此不创建任何特殊文件也能复现）。

- **E999 / E046 系**（DJB 包的 musl errno、chmod/chown 无权限效果）覆盖的是源码级与权限位层面的 DJB 适配；本条目覆盖的是**发布包自身的构建/安装脚本语义**（`conf-*` 接口、`TARGETS` clean 清单、`installer` 清单格式、发行版清单与文件不一致），处置手段是配方侧写 conf-* + 一处清单补丁，不改 C 源码。

## 关联条目

- 相关: E074（FIFO 与 make jobserver）、E525（-j1 统一口径）、E999/E046（DJB 包历史适配）、P013、P020
- 关键区别: 本条目的四个信号都属于"上游脚本假设 Linux 文件系统语义"，与 libc/源码层面无关
