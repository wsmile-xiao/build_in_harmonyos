# keyd 2.5.0 — OHOS MAC 把整个 input 子系统对用户态隐藏（stat 与 open 同为 EACCES，枚举不是空集合）

> 状态：**草稿**（Path B 知识条目，待人工审核 promote）
> 机器可读配套：`DRAFT-keyd-2.5.0-ohos-input-subsystem-mac-invisible.kv`（同 stem 成对，同一原子 PR）
> 实证环境：HarmonyOS PC 真机 / 非 root 会话 / HongMeng kernel 1.12.0 / clang 15 + musl / 2026-09-24

## 概览

| 项 | 内容 |
|---|---|
| **分类** | OHOS 平台限制（MAC 策略）· 运行期能力探测 · 测试假绿 |
| **严重程度** | 2（数据面整片不可用；编译链与单元面不受影响） |
| **触发工具** | make / clang / python3（消费者测试与集成 runner） |
| **影响软件** | keyd 2.5.0（本条实证）；同族风险见「受影响范围」 |
| **触发阶段** | test / runtime |
| **解决方案** | `stat-open-readdir-triple-probe-with-positives-then-errno-asserted-runtime-degradation`（非 root 探针 + errno 三分诊 + 断言式运行时降级；本包实现 252 行、10 例） |
| **自愈** | ❌ 否（是平台能力边界，不是可自动修补的构建缺陷） |

## 错误签名

```
inotify: Permission denied
Permission denied.*/dev/input
errno=13  Permission denied
existence undecidable from user space
```

**匹配关键词**：`/dev/uinput`, `/dev/input/event`, `EACCES`, `uinput`, `UI_DEV_CREATE`,
`EVIOCGBIT`, `inotify_add_watch`, `opendir 非空集合`, `枚举假绿`, `虚拟键盘守护进程`,
`input 子系统不可见`, `MAC 策略`, `stat 与 open 同为 EACCES`, `keyd`

**预扫描**：`prescan_pattern=/dev/uinput|/dev/input/event|UI_DEV_CREATE|EVIOCGBIT|inotify_add_watch`；`prescan_globs=**/src/**/*.c, **/t/runner.py, **/tests/**/*.py, **/*.py`（与 `.kv:27` 四项一致）
（`prescan_globs=**/src/**/*.c, **/t/runner.py, **/tests/**/*.py`）

## 典型日志（逐字粘贴自复跑 `test_package` 的日志，未重排列宽、未删 detail 行）

```
== keyd input-subsystem probe, uid=20020084 euid=20020084 ==
CASE control open /dev/null       rc=3    errno=0   -                        PASS
                                  fd=3
CASE control opendir /dev         rc=0    errno=0   -                        PASS
                                  243 entries listed
CASE stat /dev/uinput             rc=-1   errno=13  Permission denied        PASS
                                  existence undecidable from user space
CASE stat /sys/class/input        rc=0    errno=0   -                        SKIP
                                  mode=0755 (input class directory)
CASE stat /sys/class/misc/uinput/dev rc=-1   errno=13  Permission denied        PASS
                                  existence undecidable from user space
CASE open /dev/uinput (w)         rc=-1   errno=13  Permission denied        PASS
                                  no fd: UI_SET_EVBIT/UI_DEV_CREATE unreachable
CASE open /dev/input/event0       rc=-1   errno=13  Permission denied        PASS
                                  no fd: EVIOCGBIT capability probe unreachable
CASE opendir /dev/input           rc=-1   errno=13  Permission denied        PASS
                                  device discovery sees no keyboards
CASE inotify_init1                rc=3    errno=0   -                        PASS
                                  descriptor created
CASE inotify_add_watch /dev/input rc=-1   errno=13  Permission denied        PASS
                                  hotplug watch on the keyboard directory
SUMMARY pass=9 skip=1 fail=0
VERDICT OK
```

守护进程侧（**另一条平面**，勿与上表混判；由 `test_keyd.py` 第 2 层逐条断言，断言行见构建日志）：

```
$ keyd            # rc=255
open: No such file or directory          <- src/ipc.c 打开 socket 锁，/var/run 不存在
failed to set effective group 'keyd': ... <- getgrnam("keyd") 路径告警
$ keyd monitor    # 先撞 input 子系统，未走到 IPC
inotify: Permission denied
```

## 触发上下文

- **软件**：keyd 2.5.0（键盘重映射守护进程，需自建虚拟键盘 + 抓取真实键盘）
- **触发点**：按上游真实调用序列做能力探针 ——
  `src/vkbd/uinput.c:41`（`open("/dev/uinput", O_WRONLY|O_NONBLOCK|O_CLOEXEC)`）→ `:106`（`ioctl(fd, UI_DEV_CREATE)`）建虚拟键盘两步、
  `src/device.c:218`（`opendir("/dev/input/")` 枚举）、
  `src/device.c:130`（`open(path, O_RDWR)` 抓取单个 `event*`）、
  `src/device.c:58`（`EVIOCGBIT` 读设备能力）、
  `src/device.c:260/266`（`inotify_init1` + `inotify_add_watch` 监听热插拔）
- **前提**：非 root 会话（本机无 root）

## 根因分析

**(1) 不是 DAC、不是 seccomp，是 MAC 把 input 子系统整片关掉。**
六条入口（`stat /dev/uinput`、`stat /sys/class/misc/uinput/dev`、`open /dev/uinput`、
`open /dev/input/event0`、`opendir /dev/input`、`inotify_add_watch /dev/input`，按 syscall 归 4 类）**全部 EACCES(13)**，而 `inotify_init1()` 本身成功（fd=3）。
⇒ 被拒的是"访问 input 节点"这一整类操作，而非某个具体 syscall。

**(2) errno 落在 EACCES 而非 ENOENT ⇒ 存在性在用户态不可判定。**
`stat()` 自身就被拒，"探测节点是否存在"这段代码拿不到任何存在性信息。
这与 **E237**（ACPI 类节点 `ENOENT`＝根本不存在）是**两种失败模式、两种处置**——
这是本条最容易被误并入 E237 的地方，也是申报 create 的理由。

**(3) `opendir("/dev/input")` 返回 EACCES，不是返回空目录 ⇒ 计数式探测静默假绿。**
凡是"枚举 `event*` 得到 0 个就当没有键盘"的写法，都会把"被策略拒绝"读成"没有设备"
并**正常继续**。本包上游 `src/device.c:218` 与集成测试 `t/runner.py:146`
（`glob.glob("/dev/input/event*")`）正是这个形状。与 **E584**
（configure 探测报 yes、运行期被 `SIGSYS` 终止）同属"假绿家族"但机制不同——
这里 syscall 规矩地返回 `-1/EACCES`，**是调用方没检查 `opendir` 的返回值**。

**(4) 拒绝是子系统级而非全局，且可见性按节点分层。**
阳性对照：同进程 `open("/dev/null")` 成功、`readdir("/dev")` 成功（243 项）。
非对称：`stat("/sys/class/input")` **成功**（mode 0755），而
`stat("/sys/class/misc/uinput/dev")` 为 EACCES ⇒ sysfs 的 class 目录可见、其下 misc
设备节点不可见。**按单一目录外推"整片可见/整片不可见"都会错。**

**(5) 顺序性事实：守护进程先死在 socket 平面，拿不到 input 平面的 errno。**
本机 `/var/run` 不存在，`src/ipc.c` 的 `open` 返回 ENOENT（rc=255），
因此"跑一下守护进程"看到的错误串**不是** MAC 的结果。两个平面
（socket＝ENOENT / input＝EACCES）必须分开断言，否则会把 MAC 结论记成路径缺失。

## 修复

### 主方案：三入口 + 双对照探针，按 errno 三分诊，再交"断言式运行时降级"

1. **探针覆盖上游真实使用的三类入口**（缺一判不准）：`stat` 读属性 / `open` 写入端 /
   `opendir` 父目录枚举；上游若监听热插拔，再加 `inotify_init1` + `inotify_add_watch`
   （**init 成功不代表 add_watch 成功**）。
2. **对照项不可省**：同进程 `open("/dev/null")`、`readdir("/dev")` 必须成功。
   没有对照，EACCES 只能说明"这个 uid 什么都干不了"，说明不了 input 子系统被单独关闭。
3. **errno 分诊**（决定申报口径，不得凭印象）：
   - `EACCES/EPERM` ⇒ 策略性不可见 ⇒ 按本条交付降级；
   - `ENOENT` ⇒ 数据面根本不存在 ⇒ **停手上报用户**（工作区【无法适配】赛道已取消，
     agent 不得自判）；
   - 被**信号**终止（`SIGSYS`）⇒ 转 **E584** 口径。
4. **交付形态**：**不加 ifdef 宏砍功能、不改判通过、不用 `timeout`/`|| true` 吞错**。
   数据平面照常编译链接进包；探针编成 `test_package` 里的真实消费者二进制，
   逐入口断言"被拒且 `errno == EACCES`"，并同时断言两条对照项成立。
5. **不因平台受限缩分母**：上游同一批 86 个 `t/*.t` 语料有两条入口——
   进程内单元入口（`Makefile:113`）真实执行 **86/86 通过**；需 root + uinput 的端到端
   集成入口（`t/run.sh` 第 5-9 行 whoami!=root 即 sudo 重启）单列"**平台受限未执行 86 例**"并附逐字 errno。

```bash
# 定罪探针（非 root，设备真机；完整逐字读数见上「典型日志」）
clang -O1 -o probe_input probe_input.c && ./probe_input
# 单元入口必须一个用例一个进程（见下方失败方案 3）
./bin/test-io t/test.conf t/x.t     # for each x in t/*.t
```

### 备选方案

**单进程跑完整套件** —— ❌ **不可行**：`t/test-io.c:268` 的 `run_test()` 在首个不匹配处
`exit(-1)`，共用进程会在第 1 例之后静默截断整条套件（`0 failed` 假象）。

## 失败方案与弯路

1. **照 profile 的 `compiler_executables` 直接用 → 全链失败**：仓库 CI profile 把
   `c` 钉成绝对路径 `/data/service/hnp/bin/clang`，而它的可达性**随设备状态变化**：重启前的
   会话里 `stat` 报 `Permission denied` → `make Error 2`；重启后同一路径可 `stat`、`os.access(X_OK)`
   为真，且交付构建实际用它（`create11.log:101` 逐字 `CC="/data/service/hnp/bin/clang"`）。
   修法是把 profile 取值先过 `os.access(X_OK)` 校验、失败再退 PATH 查找
   （与本条第 (1) 点是同族现象：**配置里存在 ≠ 本执行域可用**）。
2. **照 `uname -s` 分支编译 → 链接期找不到 `-linotify`**：`uname -s` 在本机返回
   `HarmonyOS`，走非 Linux 分支追加 `-linotify`，而 OHOS 把 inotify 留在 musl libc 内、
   不提供 libinotify。修法：命令行 `platform=Linux` 覆盖 makefile 的 `=` 赋值。
3. **`make install` 在本机不可用**：理由是**权限**（`Makefile:72` 的 `groupadd` 与 `/usr/local` 前缀需 root），
   不是缺 `install` 工具（`/bin/install`=toybox 0.8.12 实测可用），也不是 PATH（profile 用 `PATH=+(path)`
   前插而非替换）⇒ `package()` 逐条复现安装行到 package_folder（含 `chmod 755`）。
4. **消费者测试的四处先验假设错判**（都是"我以为平台应该这样"）：
   `list-keys` 有 4 行空项而非全部有名字；`shift`/`meta` 不是键名（是 `leftshift` 等）；
   `keyd monitor` **先**撞 `inotify: Permission denied` 而根本走不到 IPC；
   layouts 里没有 `us`（有 `af`）。⇒ 断言必须从真机读数反推，不能按直觉写。

## 受影响范围

任何把 `/dev/uinput`、`/dev/input/event*` 或 inotify-on-`/dev/input` 当作**运行期数据面**的包：
虚拟键盘/重映射守护进程（keyd、interception-tools、input-remapper、evsieve）、
裸读 evdev 的库（libevdev、X 的 evdev 驱动后端）、以及"枚举 `event*` 判断有无键盘"的工具。

**边界（不得越界引用）**：

- 不适用 E237 的 ENOENT 形态（那类应上报用户，不按本条降级）；
- 不适用 seccomp 信号终止形态（E584）；
- **不等于"以 root 运行即可用"**：本机无 root、`/var/run` 不存在，root 或 MAC 调整后
  的可达性**未经验证**，不得据本条承诺守护模式可用；
- CI worker 若以特权运行，结论可能整体反转 ⇒ 申报前在目标执行路径重测；
- sysfs 可见性按节点分层，不得由单一目录成败外推整片。

## 验证

| 判据 | 预期 | 实际 | 来源 |
|---|---|---|---|
| 探针逐字 errno | **6 个 input 入口**（按 syscall 归 4 类：stat/open/opendir/inotify_add_watch）`errno=13`，2 条对照成功 | `SUMMARY pass=9 skip=1 fail=0` | 设备 `~/tmp/uc2/hw-3/keyd/create12.log:128-150`（验证记录，不随 PR 提交，可按下文复现命令重跑） |
| 上游单元套件全量执行 | `registered=86 passed=86 failed=0` | 一致（导出的 recipe rev 与交付同为 `cd56cda1…`） | `create11.log:161` |
| 消费者断言 | `FAIL=0` | `[test] assertions: PASS=41 FAIL=0 SKIP=0`（严格 EACCES 整改后；整改前同位置为 `PASS=40`） | `create12.log:168` |
| 内存预算 | 远小于门槛 | 整次 `conan create` `MEMCAP[probe] peak=176MB budget=0MB rc=0 用时14.4s`（一次运行同时产出 86/86 与 41 条断言） | `create11.log:279` |

```bash
# 复现（设备真机，非 root）
export PATH=$HOME/usr/local/bin:$PATH CONAN_HOME=$HOME/tmp/ch/home-hw-3-keyd
conan create archives/k/keyd/2.5.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
```

## 与既有条目的查重结论

| 既有条目 | 形似之处 | 为何仍判 create |
|---|---|---|
| **E237**（ACPI 缺失，`compile-verify-with-runtime-degradation`） | 同为"运行期数据面不可用 ⇒ 编译+单元交付 + 降级披露" | errno 不同（E237 是 ENOENT＝不存在；本条是 EACCES＝存在性不可判定），**处置分支也不同**（ENOENT 须停手上报，EACCES 可按本条降级）；本条另含 E237 未记录的"父目录 readdir 非空集合 ⇒ 枚举假绿"与"探针须带阳性对照"两条可复用结论 |
| **E584**（System V IPC 被 SIGSYS + configure 假绿） | 同属"假绿家族" | 机制不同：E584 是 syscall 被信号终止；本条 syscall 正常返回 `-1/EACCES`，缺陷在调用方未检查 `opendir` 返回值 |
| **E031 / E303 / E008**（SELinux 拒 `/proc`；受限运行域拒读根目录项；SELinux 对用户进程访问非普通文件的 fstat/lseek 返回 EACCES） | 同属策略性不可见，E008 甚至同为"stat 族返回 EACCES" | 三条的客体都不是设备节点目录：E031 客体是 `/proc` 内容、E303 客体是**根目录** readdir、E008 客体是**已打开的**非普通 fd 上的 fstat/lseek。本条的客体是 input 子系统的设备节点 + 其**父目录枚举**，增量是"节点 EACCES 与父目录 EACCES **叠加**导致枚举计数不可判别（0 个 event* 既可能是没键盘也可能是被拒）"这一特定组合，以及随之而来的 errno 三分诊处置口径 |
| **DRAFT-libevdev…-meson-harmonyos-uapi-header-probe**（hw-1，Issue 12123） | 同为 input 子系统 | 那条讲**构建期** uapi 头（`linux/uinput.h`）缺失的探测与回退；本条讲**运行期**设备节点被 MAC 拒绝。两条可先后命中同一个包，互指仅为便于检索，**不互为重复** |

`draft-review` 实测（2026-09-24 交付前复跑，与本文件同一条命令）：质量预检 signature/root_cause/rec 三项全 ✅；相似 TOP3 = **E008 0.32 / E303 0.28 / E031 0.27**，工具据此给出 **`review-similar → E008`（灰区，需人工判断关联性）**，并明示“是否纳入正式知识库由人工审核决定”。分值会随签名/关键词修订而变动，此处只记最后一轮实测值，不挑早期低分快照。灰区按上表的客体范围裁决：E008 的客体是**已打开的非普通 fd** 上的 `fstat()`/`lseek()`，本条的客体是**未被打开的设备节点路径 + 其父目录枚举**——同为 EACCES，但可观测面（存在性不可判定 vs 调用被拒）与处置口径（errno 三分诊 + 计数不可判别 vs 换调用路径）不同，故按新机制申报并以 `similar_to` 与 E008/E303/E031 互指。

## 相关 PR / 提交

| PR | 软件 | 关系 | 说明 |
|---|---|---|---|
| keyd 2.5.0（本条来源） | keyd 2.5.0 | 首次 | 6 入口（4 类 syscall）双阳性对照探针 + errno 三分诊 + 86 例单元真跑 / 86 例集成未执行 |
| #12123 | libevdev-tools 1.13.7 | `similar_to` | 构建期 uapi 头探测，与本条运行期节点拒绝为不同机制 |

## 备注

- 平台任务 7806 声明语言为 `cpp`，而 keyd 2.5.0 源码为 **19 个 `.c` / 0 个 `.cpp`**
  （官方 tarball 实测：`src/` 顶层 15 个 + `src/vkbd/` 3 个 = `stdout.c`/`uinput.c`/`usb-gadget.c`，共 18 个，
  再加 `t/test-io.c`）。本条结论与语言声明无关，
  但该不匹配已按工作区口径记进登记表备注，供用户对外说明。
- 上游 `t/runner.py:197` 的 `on_timeout()` 与 `:204-205` 的
  `signal.signal(signal.SIGALRM, on_timeout)` + `signal.alarm(20)` 确实构成一条 SIGALRM 看门狗，
  它属于集成入口（需 root + uinput）的执行路径；本机该入口 0 执行，**未撞上"看门狗静默失效"**，
  因此**不**申报该机制（无实证即申报属空走，会被复核打回）。
