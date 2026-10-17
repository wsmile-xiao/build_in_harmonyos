# 上游回归测试报告 — daemontools-encore 1.11（OHOS / HarmonyOS PC）

- 提交：`cf7bea0d9051b8993dd847543af726fab04212e0`
- 测试树：`/storage/Users/currentUser/.conan2/p/b/daemo5cdac5efc9ae4/b`（采信轮 `conan-verify` 的 conan build folder，含 `patches/0001-MAN-optional-setuser.patch` 已应用、`conf-cc`/`conf-ld` 为配方写入的 clang）
- 原始日志：`reports/upstream-test.log.md`（逐用例），安装缺陷三段场景：`reports/upstream-install-scenarios.log.md`

## 取数与运行口径

上游套件入口是 `make rts`：

```
rts: programs rts.sh rts.exp
	env - /bin/sh rts.sh 2>&1 | cat -v > rts
	diff -u rts.exp rts
rts.sh:  cat rts.tests/*.sh  > rts.sh
rts.exp: cat rts.tests/*.exp > rts.exp
```

- 用例数取数命令：`ls rts.tests/*.exp | wc -l` → **21**（`00-preamble.sh` 是套件前言，`zz-cleanup.sh` 是清理脚本，都不产生 `.exp`，不计入用例）。
- 本设备不直接运行 `make rts`：跨用例共享一个 shell，任何一个用例的等待循环被阻断就会卡住整个目标。实测 `timeout 300 make -j1 rts` → rc=124、`rts` 输出文件不存在、make 报 `Deleting file 'rts'` / `Error 143`（见日志末尾）。
- 因此按用例运行：`cat rts.tests/00-preamble.sh rts.tests/<case>.sh > <case>.script`，`timeout -k 5 90 env - TMPDIR=<可写目录> HOME=<沙箱> /bin/sh <case>.script`，`cat -v` 后与 `rts.tests/<case>.exp` 做 `diff -u`——与上游同文件、同比较方式，只增加逐用例超时。
- 环境变量只做设备适配、不改测试内容：`TMPDIR` 指向可写目录（设备 `/tmp` 是只读 erofs，toybox sh 的 heredoc 需要可写临时文件，缺失时 `envini` 用例实测报 `can't create temporary file /tmp/shXXXX.tmp: Read-only file system`）；`HOME` 指向任务沙箱，避免触碰真实 HOME。

## 结果统计

| 状态 | 数量 | 用例 |
|------|------|------|
| PASS | 12 | envdir, envini, envuidgid, fghack, matchtest, multilog, nonexistent, pgrphack, readproctitle, setlock, softlimit, tai64n |
| NOT_RUN（环境阻断） | 9 | supervise-base, supervise-downtime, supervise-lock, supervise-notify, supervise-restart, supervise-start, supervise-stop, svc, svscan |
| FAIL（真实断言失败） | 0 | — |
| **合计** | **21** | |

TOTAL = PASS + FAIL + SKIP + NOT_RUN = 12 + 0 + 0 + 9 = 21。统计单位是上游 rts 用例（一个 `.exp` 期望输出文件 = 一个用例）。

## 9 个 NOT_RUN 用例的技术原因（环境限制）

- 失败命令与原始错误：`supervise test.sv` → `supervise: fatal: unable to read supervise/control: file does not exist`，退出码 111。
- 直接根因：HarmonyOS 拒绝用户进程创建特殊文件节点，四类创建路径实测全部 EPERM（原始输出逐字留存：`reports/fifo-probe-raw.log.md`）：
  - `mkfifo probe.fifo` → `mkfifo: cannot create fifo 'probe.fifo': Operation not permitted`，rc=1
  - `python3 -c "import os;os.mkfifo('p2',0o600)"` → `PermissionError: [Errno 1] Operation not permitted`，rc=1
  - `python3 -c "import os,stat;os.mknod('p3',stat.S_IFIFO|0o600)"` → `PermissionError: [Errno 1] Operation not permitted`，rc=1
  - `python3 -c "import socket;s=socket.socket(socket.AF_UNIX);s.bind('p4')"` → `PermissionError: [Errno 1] Operation not permitted`，rc=1
  - 四条路径执行后目录内无任何新节点（`ls -la` 仅 `.`/`..`）。
- 源码定位：`supervise.c:476-496`（`svpath_make("/control")` / `fifo_make()` / `open_read()`），`fifo.c` 在 `HASMKFIFO` 下直接调用 `mkfifo(2)`。
- 触发用例：9 个用例的脚本都启动 `supervise` 并轮询 `svok`/`svup`，`supervise` 一退出，套件的 `waitok` 就无限轮询（`00-preamble.sh` 的 `until "$@"`），因此表现为 4 个用例脚本超时（rc=124）、5 个用例脚本 rc=0 但输出与 `.exp` 不符（都是控制通道错误行）。
- 影响范围：被监管进程生命周期语义（起停、重启、notify 脚本、锁、svscan 目录监管、svc 信号投递）未被这 9 个用例覆盖。
- 替代验证（已在包内 `test_package` 实施，见 `reports/conan-create.log.md` 的 `TOTAL=31 PASS=31`）：
  - `supervise` 的错误路径本身（退出码 111 + 控制通道错误），并确认它**快速退出而不是挂死**；
  - `svstat`/`svc`/`svok` 对"存在但未监管的目录"与"不存在的目录"的退出码与消息（100/111/0），与上游 `nonexistent.exp` 语义一致；
  - `multilog`（日志侧核心功能）在目录、状态文件、stderr 动作、长行、时间戳上的完整实测；
  - 运行期能力探测：脚本先 `os.mkfifo()` 探测，一旦平台允许 FIFO（例如其他 CI worker），同一脚本会自动执行完整的 supervise/svok/svstat/svc 周期，不再是降级断言。

## 与 E074 的区别（避免归因错误）

E074 把「FIFO 被拒」归到 `make -j` 的 jobserver 卡住，修复动作是 `make -j1`。本设备同时实测：

```
GNU Make 4.4.1
$ make -j4 programs   → rc=0（仅打印一行 make: jobserver mkfifo: /storage/.../GMfifo18479: Operation not permitted，回退管道 jobserver）
$ supervise sv        → rc=111 + unable to read supervise/control: file does not exist
```

即 jobserver 面在本 make 版本上退化为一行噪音，而 `supervise` 的控制通道失败是致命的；把 9 个用例按 E074（"改用 -j1 即修复"）处理会得出错误结论。该区别已写入知识草稿 `knowledge/drafts/E6340-draft-8BEF.md`。

## 关于 `git diff --check` 的逐字留档例外

`reports/*.log.md` 是构建日志的**逐字**留档，日志本身含行尾空格（如 `conf-ld: /data/service/hnp/bin/clang ` 与上游 `make` 回显的 ` ./load envdir unix.a byte.a `），因此 `git diff --check upstream/main...HEAD` 会在这些文件上报 trailing whitespace。

实测分布（逐文件计数，非抽样）：本 PR 面上含行尾空格的**只有 4 个文件、共 74 行**，全部是逐字转录——`conan-create.log.md` 24、`w3-local-ci.log.md` 24、`conan-verify-supplement-raw.log.md` 19、`upstream-test.log.md` 7；其余全部文件（配方、补丁、元数据、叙述性报告、知识草稿）为 0 行。取数命令：

```sh
for f in $(git diff --name-only upstream/main...HEAD); do
  n=$(grep -cE '[ 	]+$' "$f"); [ "$n" -gt 0 ] && printf '%4d  %s\n' "$n" "$f"
done
```

（注意两点：`git diff --check` 每处命中会打印**两行**——`<path>:<lineno>: trailing whitespace.` 加一行带 `+` 前缀的内容行，所以它的 `wc -l` 是违规行数的两倍；另外本设备 `grep` 无 PCRE（`grep -P` rc=2），且 ERE 括号表达式里的 `\t` 不是制表符，必须写成字面 TAB 或 `[[:space:]]`。）

这是逐字性要求带来的**预期**结果，与 `patches/` 上下文行的同类取舍：不改留档内容（改了就不再逐字），且不存在消费该检查的门禁（`scripts/`、`ci/`、`.gitcode/` 中均无 `git diff --check` 调用点）。
