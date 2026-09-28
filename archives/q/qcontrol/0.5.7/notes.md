# qcontrol 0.5.7 适配笔记（HarmonyOS PC / aarch64）

编译日期：2026-09-26 · 构建主机：B 机（HarmonyOS aarch64，clang 15.0.4，musl）
worktree：`~/qzy/主理-63-qcontrol-0.5.7` 分支 `feat/qcontrol-0.5.7`
CONAN_HOME：`~/tmp/ch/home-qcontrol` · 断点与日志目录：`~/tmp/uc2/z63-qcontrol/`

---

## 0. 一句话结论

**包能编、能装、能在鸿蒙 PC 上真实运行**：`conan create` 与 `conan-verify`（G1/G2/G3/G4）均通过，
消费者测试全过：静态断言条件 45 条（行为 20 + 平台 25），运行期打印检查点 22 个（11/11 + 11/11），两口径的映射见 §8。真正需要适配的只有一件事——**上游用硬编码的 pkg-config 模块名
`lua5.1` 找它唯一的库依赖，而制品仓里发布的名是 `lua-5.1`**；改在 make 命令行上替换，不打补丁。
但它"能跑"只覆盖到这个程序的**平台无关那一半**（CLI + 内嵌 Lua 配置），
**NAS 硬件那一半在鸿蒙 PC 上没有承载物**（无串口节点、无 `/var/run`、AF_UNIX 的**文件系统** socket 在试过的 4 个挂载点全部 bind 失败；⚠ 第二棒补测：抽象命名空间 AF_UNIX 可用，见 §5.4 与本节末的取舍决定），
这是包本身的定位决定的，不是构建缺陷（证据见 §5）。

---

## 1. 症状（发现窗口径 vs 实测）

任务下发口径写的是："终端会话/多路复用类工具，会用到 pty / termios""零外部库依赖"
"configure/Makefile 探测项 0 个""货源 sha256=ecc6977266531571…（截断）"，
并给了被 PF7 拉黑的 Debian 池地址。实测四条都不成立：

| 下发口径 | 实测事实 | 证据 |
|---|---|---|
| 终端会话/多路复用，用到 pty | **NAS 外设守护进程**（QNAP TS-109/209/219/409/41x、Synology）。终端面只用到**串口 termios**（`/dev/ttyS0`、`/dev/ttyS1`），全树 `grep -E "pty\|forkpty\|openpty\|TIOCGWINSZ\|ioctl"` **0 命中**，没有 ioctl、没有 pty | `01-source-evidence.raw`、Makefile `SOURCES`、README |
| 零外部库依赖 | **必须 `lua5.1`**（`Makefile:9-11` 三处 `$(PKG_CONFIG)` 调用），另有 `-lpthread`，静态目标另加 `-lm -ldl` | Makefile 9-11 行 |
| 探测项 0 个 | **有 1 个条件探测**：`Makefile:13` `ifeq ($(shell $(PKG_CONFIG) --exists libsystemd-daemon …),1)` → 命中就加 `-DHAVE_SYSTEMD` | Makefile 13-17 行 |
| 货源只有 Debian 池址（被 PF7 拉黑） | 上游官网有官方发布物直链，且**与 Debian `.orig` 逐字节相同**；下发的那个池址本身 404 | 见 §2 |

## 2. 货源核实（完整哈希 / 大小 / HTTP 状态码）

| 来源 | HTTP | 字节 | sha256 |
|---|---|---|---|
| **官方** `https://www.hellion.org.uk/qcontrol/releases/0.5.7/qcontrol-0.5.7.tar.gz` | **200** | **29396** | `ecc6977266531571e724146fe18478a3a4a168a8a766c47439c4a63b3f73aa3f` |
| 交叉核对 `https://deb.debian.org/debian/pool/main/q/qcontrol/qcontrol_0.5.7.orig.tar.gz` | 200 | 29396 | 同上（`cmp` 判定两文件**逐字节相同**） |
| 下发的那个址 `https://deb.debian.org/pool/main/q/qcontrol/qcontrol_0.5.7.orig.tar.gz`（缺 `/debian` 段） | **404** | 300（HTML 错误页） | `8e3f6c3259440204a1c778ed1fb396ee11e1697879c7521d400c7e2f614ebfff` |

结论：SCT 台账里那半枚哈希 `ecc6977266531571…` 其实是**官方发布物的完整哈希前缀**；
它标的那条池址因为少一段路径而 404，不是"官方址与 .orig 形态不同"的情形。
因为二者已实测为同一份产物，"与 Debian 同值"是**核实过的事实**而非推断；
conandata 仍只写官方址（R39/PF7 不接受 Debian 重打包宿主），未加镜像、未改哈希。
上游目录页同时提供 `.tar.xz` 与 GPG `.sig`，本配方取 `.tar.gz`（与 Debian `.orig` 同一枚产物）。

## 3. 根因

`Makefile:9-11` 用 `$(shell $(PKG_CONFIG) --cflags lua5.1)` / `--libs lua5.1` 拼编译与链接参数。
制品仓的 `lua/5.1.5` 把 pkg-config 名声明为 **`lua-5.1`**（`cpp_info.set_property("pkg_config_name", "lua-5.1")`）。
在 B 机用 `conan install --requires=lua/5.1.5 -g PkgConfigDeps` 生成 pc 文件后实测：

```
$ pkg-config --exists lua5.1 ; echo $?
1
No package 'lua5.1' found                      <== 上游要的模块名根本不存在
$ pkg-config --cflags lua-5.1
-DLUA_USE_POSIX -DLUA_USE_DLOPEN -I…/lua/5.1.5/…/include
$ pkg-config --libs   lua-5.1
-L…/lua/5.1.5/…/lib -llua -ldl -lm             <== 发布名可正常解析，且 -lm -ldl 已在 Libs 里
```

⇒ 唯一缺陷是**模块名**。（本笔记早期版本曾写"`--libs` 会漏掉 `-lm -ldl`，因为它们落在
`Libs.private`"——这条被上面的实测**否证**，已改正；发布名 `lua-5.1` 的 `Libs` 是完整的。）
不修的话 CFLAGS/LIBS 拿到的是错误文本、`#include <lua.h>` 直接失败。

## 4. 最小复现（任何一台装了 lua/5.1.5 的机器都能重放）

```bash
mkdir -p /tmp/pcexp && cd /tmp/pcexp
conan install --requires=lua/5.1.5 -g PkgConfigDeps \
  -pr:h=<repo>/ci/conan/profiles/ohos-aarch64 -pr:b=<repo>/ci/conan/profiles/ohos-aarch64
export PKG_CONFIG_PATH=$PWD
pkg-config --exists lua5.1; echo "rc=$?"        # => rc=1, No package 'lua5.1' found
# 再按上游原样跑一次 make（不替换任何变量）：
tar -xzf qcontrol-0.5.7.tar.gz && cd qcontrol-0.5.7 && make        # => 编译期找不到 lua.h
```

## 5. 平台能力面实测（给主理窗判 B 的一手数据，只报事实）

探针：`~/tmp/uc2/z63-qcontrol/probe_caps.c` + `run_probe.sh`（逐模式各起一进程），
完整输出 `~/tmp/uc2/z63-qcontrol/04-capability-probe.log`。
`O_NOCTTY=256`（八进制 `0400000`，不是 `0o200000`）。**全部用 open 系探针**，没有用 `stat`/`ls -l`/`[ -e ]` 判节点。

### 5.1 上游真正依赖的终端能力：串口 termios

| 调用 | 实测 |
|---|---|
| `open("/dev/ttyS0", O_RDWR\|O_NOCTTY\|O_NONBLOCK)` | **rc=-1 errno=2 (No such file or directory)** |
| `open("/dev/ttyS1", …)` | **rc=-1 errno=2 (No such file or directory)** |

鸿蒙 PC 上没有这两个节点 ⇒ `a125.c:340`、`ts209/219/409/41x.c`、`synology.c:290` 的
`qnap_serial_open("/dev/ttyS1")` 一类路径在本平台**没有承载物**。
上游在这条路上用的全部终端手段只有：`tcgetattr` 存 oldtio →
`c_cflag = B1200/B9600/B19200 | CS8 | CLOCAL | CREAD` + `cfsetispeed/cfsetospeed` →
`tcsetattr(TCSANOW/TCSAFLUSH)`；**全树没有一处 `ioctl()`、没有 pty、没有 `TIOCGWINSZ`**。
（下发口径说的"termios 13 #5"在本包没有对应物。）

### 5.2 pty（open 系实测，与串口结论要分开看）

| 调用 | 实测 |
|---|---|
| `posix_openpt(O_RDWR\|O_NOCTTY\|O_NONBLOCK)` | rc=0 |
| `grantpt` / `unlockpt` | rc=0 / rc=0 |
| `ptsname(master)` | `/dev/pts/1` |
| `open(ptsname, O_RDWR\|O_NOCTTY)` | rc=0 |
| `tcgetattr(slave)` | rc=0 |
| `tcsetattr(slave, TCSANOW, B38400\|CS8\|CLOCAL\|CREAD)` | rc=0，回读 `c_cflag=04277 ispeed=15 ospeed=15`（波特率确实落盘） |
| `ioctl(slave, TIOCGWINSZ)` | rc=0，初值 `rows=0 cols=0 xpx=0 ypx=0` |
| `ioctl(slave, TIOCSWINSZ, 40x132)` | rc=0；随后 `ioctl(master, TIOCGWINSZ)` rc=0 且回读 `rows=40 cols=132`（ winsize 跨端可见） |
| 规范模式下 `write(master,"abc")` → `read(slave)` | 读 rc=-1 **errno=11 EAGAIN**；再 `write(master,"\n")` 后读回 `abc\n` 4 字节 —— 这是 POSIX 规范模式语义，不是平台缺陷 |
| raw 模式 `write(master,"xyz",3)` → `read(slave)` | **rc=3 bytes=[xyz]（tries=1）** ⇒ master→slave 通 |
| raw 模式 `write(slave,"789",3)` → `read(master)` | 先排空 master 队列（丢弃 5 个历史回显字节）再写：**rc=3 bytes=[789]（tries=1）** ⇒ slave→master 也通 |
| 队列顺序的方法教训 | 上一版把"写 slave"放在"排空 master 队列"之前，drain 恰好吞掉新写的 3 字节，读出来是 `rc=-1 errno=11` —— **一个自己造的假阴性**。调整顺序后才拿到上面的正向结果 ⇒ pty 双向回环在鸿蒙 PC 实测全通（与 sexpect 先例一致） |
| `setsid()`（独立进程） | rc=0 |
| `ioctl(slave, TIOCSCTTY, 0)` | **rc=0**（鸿蒙 PC 上可成功认 pts 做控制终端；随后 `getsid()`=自身 pid） |
| `isatty(slave_fd)` | 1 |

⇒ **就本包而言这组数据是"背景"而不是"依赖"**：qcontrol 不用 pty。它对本平台的终端需求只有串口，
而串口节点不存在。**不要把 5.2 的 pty 可用性读成"qcontrol 的硬件面在鸿蒙可用"。**

### 5.3 evdev / glob / AF_UNIX（守护进程与配置递归的能力面）

| 调用 | 实测 |
|---|---|
| `glob("/dev/input/event*")` | **rc=3 (GLOB_ABORTED) errno=13 (Permission denied)，gl_pathc=0** |
| `open("/dev/input/event0", O_RDONLY\|O_NONBLOCK)` | **fd=-1 errno=13 (Permission denied)**（节点在，但本 uid 不可开） |
| `open("/dev/input/event1", …)` / `open("/dev/input/mice", …)` | 同样 **errno=13 (Permission denied)** |
| `glob("/etc/*.conf")`（与 `confdir()` 同一调用形态） | **rc=0，gl_pathc=9** ⇒ `confdir()` 的 glob 机制本身在鸿蒙可用（消费者测试第 4 条已实测走通） |
| `bind()` AF_UNIX @ `/storage/Users/currentUser/tmp/uc2/z63-qcontrol`（HMDFS） | **rc=-1 errno=1 (Operation not permitted)** |
| `bind()` @ `/dev/shm` | **rc=-1 errno=13 (Permission denied)** |
| `bind()` @ `/data/local/tmp` | **rc=-1 errno=13 (Permission denied)** |
| `bind()` @ `/mnt/temp` | **rc=-1 errno=2 (No such file or directory)**（目录不存在） |
| `connect("/var/run/qcontrol.sock")`（上游硬编码） | **errno=2 (No such file or directory)** |
| `open("/var/run", O_RDONLY)` | **errno=2 (No such file or directory)** —— 该目录在鸿蒙 PC 上不存在 |
| `open("/etc/qcontrol.conf", O_RDONLY)`（上游默认配置） | errno=2 (No such file or directory) |

⇒ 本次试过的 4 个挂载点上 **AF_UNIX `bind()` 无一成功**，且 `/var/run` 根本不存在 ⇒
`qcontrol -d/-f`（守护 + socket 激活）在本平台没有可写的监听地址；
默认 client 模式因此只能拿到 `Error connecting to socket: No such file or directory` 并以 255 退出
（这条已经写进消费者测试第 11 条，作为真实行为断言而非豁免）。
⚠ 本段结论的适用范围经 §5.4 补测收窄为**文件系统** socket：抽象命名空间 AF_UNIX 实测可用，
所以"守护模式在本平台不可验证"的准确说法是"不改上游源码就不可验证"。

### 5.4 抽象命名空间 AF_UNIX（第二棒补测；把"守护模式"从不可行改判为可选）

`~/tmp/uc2/z63-qcontrol2/02-abstract-probe.log`（本窗逐行复核过原文）：

| 试验 | 实测 |
|---|---|
| T1 抽象名 17 字节，bind/connect 两端 addrlen 都给正确长度 | `bind rc=0` → `listen rc=0` → `connect rc=0` → `send rc=4` → `accept rc=6` → 服务端 `recv rc=4 got=[PING]` → `send rc=4` → 客户端 `recv rc=4 got=[PONG]` ⇒ **双向字节真实往返** |
| T3 抽象名 107 字节（`sun_path` 上限内） | 同上全通 |
| T5 两端都用上游那种 `sizeof(struct sockaddr_un)` 长度（结构体已 memset 清零） | 同上全通 |
| T4 bind 用 `sizeof(struct sockaddr_un)`、connect 用名字实际长度 | `connect rc=-1 errno=111 (Connection refused)` |
| T6 bind 的 addrlen 含结尾 NUL、connect 不含 | `connect rc=-1 errno=111 (Connection refused)` |

⇒ **抽象命名空间 AF_UNIX 在本设备完全可用**（E461 的处方在鸿蒙 PC 成立）；§5.3 失败的是**文件系统** socket 路径，两者不是一回事。
⚠ 两条读法纪律：① 成功行里仍打印 `errno=111`／`errno=2`，那是探针无条件输出残留 errno 的显示缺陷，判成败只看 rc 与有没有拿到 PING/PONG；
② 抽象名按**字节长度精确匹配**，两端 addrlen 算法不一致就直接 ECONNREFUSED——上游两处都用 `sizeof(struct sockaddr_un)`，恰好自洽（T5 通）。

**为什么本包仍然不走这条路（决定与代价，供后续 daemon 类包复用）**：要用抽象命名空间必须改上游源码——
`qcontrol.c:45` 的 `#define PIC_SOCKET "/var/run/qcontrol.sock"` 是硬编码，客户端 `qcontrol.c:472-485` 与服务端
`qcontrol.c:527-554` 两处 `strcpy(...sun_path, PIC_SOCKET)` 都要改成 `sun_path[0]=0` 并按名字长度算 addrlen。
这不只是换个地址族：**抽象命名空间没有文件系统 inode ⇒ 拿不到 `chmod`/`chown` 那一层访问控制，可见性改按 network namespace 划分**，
对一个能开风扇、喂看门狗的守护进程属于放宽安全边界。本包 45 条静态断言条件中已有 20 条行为条件覆盖 CLI、配置装载（confdir glob）、
`register()` 命令表、argv→C→Lua→logprint 往返、错误路径退出码，以及默认 client 模式对硬编码路径的真实连接失败诊断
（第 11 条），守护模式回环因此是**可选增益**而不是证据缺口 ⇒ 决定不改源码，把它如实留在「未验证」一侧，
并把"抽象 AF_UNIX 可用 + addrlen 长度敏感 + 安全边界代价"这条实测事实交付给后续包。

## 6. 已试过的失败方案（都留了日志）

1. **`ohc-run.py init-build qcontrol 0.5.7 --auto --url … --tar tar.gz` 崩在 harness 自身**（不是本包问题）。
   `scripts/ohc/init_build.py:543 → check_env() → scripts/ohc/check_env.py:33`：
   ```
   except Exception:
       return False, str(e)          # e 未绑定 —— NameError: name 'e' is not defined
   ```
   触发点是它拿 `~/usr/local/bin/automake --version` 时 exec 失败（该文件在，但其解释器不可用，
   抛 `FileNotFoundError: '/storage/Users/currentUser/usr/local/bin/automake'`），异常处理器自己写错了变量名。
   ⇒ **框架文件不改**（按 CONTRIBUTING「scripts/ 只读」、框架改动须单独 PR），
   骨架只生成了 `manifest.yaml`/`notes.md`/空目录，`conanfile.py`/`conandata.yml`/`test_package` 全部按 SKILL 模板手写。
   这条建议主理窗入表：**任何走 `init-build`/`check-env` 的任务在这台机器上都会挂**。
2. **`recipe-search qcontrol` 无相似配方**（语料 6173 条，含 `-b makefile` 二刷）⇒ 首稿无底稿可抄，
   参照 `archives/a/abduco/0.6`（裸 Makefile C 程序）+ `archives/p/pamixer/1.6`（application 且算 flags）+
   `archives/c/ctronome/0.5.6/test_package/test_ohos.sh`（平台断言范式）手写。
3. **第一版消费者测试自己错两条**（都是测试的错，不是包的错，均已修并留证）：
   - `--direct --help` 漏传 `-c CONF` ⇒ confdir/register 两条断言必然落空（日志 `05-create-2.log`）；
   - 崩溃守卫把 `main() return -1` 的 **255 当成"信号致死"**（rc≥128 一刀切）⇒ 改成
     超时(124)/`rc≥128 且 rc≠255`/崩溃标记字符串三重判据，并把负向用例改成**精确断言 255**。
4. **`-g` 会泄漏宿主路径**：上游 `CFLAGS += -g`，会把 conan 构建目录 `/storage/Users/currentUser/tmp/ch/…`
   写进产物 DWARF，与"产物内无宿主绝对路径"断言冲突 ⇒ 替换 CFLAGS 时去掉 `-g`，
   保留 `-c -Os -Wall -Wextra`；实测产物 `strings -a` 已无任何本机构建路径（`test_ohos.sh` 第 9 条硬断言）。
   注：**不做 strip**——`archives/a/abduco/0.6` 记录过"OHOS 内核 MAC 拒绝被 llvm-strip 过的二进制"。
5. **`qcontrol-static` 目标不可用**：它拼的是 `$(pkg-config --variable=libdir lua5.1)/liblua5.1.a`，
   而 conan 的 lua 包只有 `liblua.a` ⇒ 只构建默认的动态目标 `all`（配方注释里写明原因）。
6. **上游 `#include <sys/signal.h>`（evdev.c:27）** 在 OHOS 头文件里只是一条
   `#warning redirecting incorrect #include` 提示，1 warning generated，不阻塞。

## 7. 最终方案

- `package_type = "application"`，`requires = lua/5.1.5`（唯一的包依赖；systemd 走"探测即关闭"）。
- 不走上游 pkg-config：`make -j1 all CC=<profile 的绝对 clang> PKG_CONFIG=false
  CFLAGS='<-c -Os -Wall -Wextra + lua 的 defines/includes>'
  LIBS_DYNAMIC='<-lpthread + lua 的 libdirs/-llua/-ldl/-lm>'`，
  flags 全部取自 `self.dependencies["lua"].cpp_info`（R33 不碰 shell 变量），**0 补丁、0 源码改写**。
  `CPPFLAGS`/`LDFLAGS` 保持上游值 ⇒ 版本宏 `-DQCONTROL_VERSION` 仍由上游生成（测试第 1 条就是钉这个）。
- `package()` 收 `bin/qcontrol` + 6 份示例配置（`share/qcontrol/examples/*.lua`）+ README/HACKING/COPYING；
  **产物缺失即 `raise RuntimeError` 失败关闭**；systemd unit 不打包（本平台无 systemd）。
- `package_info()` 只声明 `bindirs=["bin"]`、清空 `includedirs/libdirs`，**不导出 `cpp_info.libs`**。
- 软件级 `commands.json`（R38/PF8：`type=tool`、`versions.0.5.7.ref=qcontrol/0.5.7`、`binary: true`）。

## 8. 测试账本（五维 + 消费者）

上游静态测试：**0**（三条实测证据见 `test_package/MANIFEST.yml` 头部：无 tests 目录 /
`make -n check` → `No rule to make target 'check'` / 文件清单 0 个测试源文件；目标只有 all/clean/dist）。
⇒ 上游五维 = 总数 0、可执行 0、通过 0、跳过 0、失败 0；**上游测试文件未做任何修改**。

消费者侧（真机执行，断言决定退出码）：

| 维度 | 数 |
|---|---|
| 行为判定条件（test_qcontrol.sh，静态清点） | 20 | 全部被执行到（其运行期证据＝下面 11 个打印检查点） |
| 平台判定条件（test_ohos.sh，静态清点） | 25 | 同上，对应 11 个打印检查点 |
| 静态条件合计 | **45** | 若干检查点各自包含多个判定条件 ⇒ 条件数大于检查点数 |
| 运行期打印检查点 `OK: n`（脚本自计） | **22 / 通过 22** | 日志原文 `BEHAVIORAL ASSERTIONS PASSED: 11/11` + `OHOS ASSERTIONS PASSED: 11/11` |
| 崩溃守卫（6 次真实运行各带超时/信号/崩溃标记三项） | 控制流，不单独打印计数 ⇒ **不申报数字** | 见 test_qcontrol.sh 的 run_bin/guard 段 |
| 跳过 / 失败 | 0 / 0 | 申报口径：能拿日志逐行核对的是 22 个检查点，45 是静态条件数，两者都写在表里而不是互相替换 |

日志（绝对路径，均在 B 机）：
- `~/tmp/uc2/z63-qcontrol/03-create-1.log` 首跑（构建+打包全绿，测试暴露我自己的两个 bug）
- `~/tmp/uc2/z63-qcontrol/05-create-2.log` 修 bug 中途（1-6 过，守卫误判 255）
- `~/tmp/uc2/z63-qcontrol/06-create-3.log` **conan create 全绿**（11/11 + 11/11，CREATE_RC=0）
- `~/tmp/uc2/z63-qcontrol/07-conan-verify.log` G1 FAIL（缺 MANIFEST.yml，当时故意等数字）
- `~/tmp/uc2/z63-qcontrol/08-conan-verify-final.log` / `09-conan-verify-final2.log` **conan-verify PASS（VERIFY_RC=0）**
- `~/qzy/主理-63-qcontrol-0.5.7/archives/q/qcontrol/0.5.7/reports/conan-create.log` G2 干净构建全日志
  （含 10 条 `clang … -o *.o-dyn` 真实编译行、`Calling build()`、`Package 'cd172a…' built`；
   不是 `- Cache` 蒙过去的绿）
- `~/tmp/uc2/z63-qcontrol/01-source-evidence.raw` 货源三数（HTTP/字节/sha256）
- `~/tmp/uc2/z63-qcontrol/04-capability-probe.log` §5 全部能力面实测原文

## 9. 适用边界（如实划线，不要外推）

1. **已验证**：aarch64 + musl + clang 15 下编译链接打包；`--version/-V`、`--direct` 配置装载
   （confdir glob）、`register()` 命令表、argv→C→Lua→logprint 往返、错误路径退出码 255、
   产物 ELF 属性（musl/PIE/.codesign/无宿主路径）。
2. **未验证且在本平台不可验证**：任何 NAS 硬件动作（LCD、风扇、按键、看门狗）——需要
   `/dev/ttyS0|/dev/ttyS1`（实测 ENOENT）与 `/dev/input/event*`（实测 EACCES）；
   守护模式 `-d/-f` 需要能 bind 的 AF_UNIX 路径（实测 4 个挂载点的**文件** socket 全失败、`/var/run` 不存在；抽象命名空间实测可用，但要用它必须改上游 `qcontrol.c:45/472-485/527-554` 并放宽访问控制 ⇒ 本包选择不改，见 §5.4）。
   这是"包的平台前提不满足"，不是"适配没做完"：程序本体、配置解释器、CLI 三件事都是真的跑通的。
3. `--direct` 之外若有人指望 `qcontrol` 改默认配置路径 `/etc/qcontrol.conf`：该文件不存在（实测 ENOENT），
   但 `-c PATH` 完全可用（测试第 3-10 条都在用 `-c`），无需改上游硬编码。
4. lua/5.1.5 是静态 `liblua.a` ⇒ 产物 NEEDED 只有 `libc.so`（实测），运行时不依赖 conan 缓存里的 .so，
   这也是本包能直接在鸿蒙上 exec 的原因。
5. 版本号四处逐字符 `0.5.7`：任务版本 = 配方 `version` = 归档目录 = 分支名 `feat/qcontrol-0.5.7`。
---

**编译结束**: 2026-09-26 05:50
**最终状态**: built
