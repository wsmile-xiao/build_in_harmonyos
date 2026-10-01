# scanmem 0.17 → HarmonyOS PC (aarch64) 适配笔记

> 结论：**可适配**（application，非内核态交付物，用户态工具）。
> 产物：`bin/scanmem` + `lib/libscanmem.so{,.1,.1.0.0}` + `lib/libscanmem.a`
> + `include/scanmem/*.h`（8 个）+ man page + README。

---

## 0. 任务与前置核验

| 阶段 | 结论 | 证据 |
|---|---|---|
| W0 依赖发布检查 | **PASS** | `conan download "readline/8.3" -r=ohpcd --only-recipe` 成功；`ncurses/6.6`、`automake/1.18`、`libtool/2.5.4.1` 同。注：裸包名 `conan download readline`（不带版本）会误报 `Recipe 'readline' not found`，**必须带版本号**才符合 R35 口径 |
| W0b 历史归档 | **无** | `git grep -l scanmem origin/main -- archives` 无命中；`archives/s/` 下无 scanmem 目录 |
| W0b CI 能力矩阵 | **可构建** | 语言是 C + Autotools（CI 具备）；530 个现存配方在 `build()` 里跑 `autoreconf`，证明 CI 有 autoconf 系工具链 |
| W1 同步 main | 已同步 | `10cbaf8b29` |

**W0b 的关键结论（不能照搬设备原生经验）**：`htscodecs/1.6.5` 记录了
「CI 预装 autoconf 但**不**预装 automake/aclocal」，因此必须
`tool_requires("automake/1.18")` + `tool_requires("libtool/2.5.4.1")`。
本配方照此办理，并遵守同一条告警：**不要** `tool_requires autoconf`
（它会拖进自己的 perl，XS 模块覆盖系统 perl，导致系统 autoreconf 失效）。

---

## 1. 源码形态：这是一次真正的 autotools 引导

上游 v0.17 的 GitHub **release 资产不存在**：

```
GET https://github.com/scanmem/scanmem/releases/download/v0.17/scanmem-0.17.tar.gz
→ HTTP 404
```

tag 归档里**只有** `configure.ac` / `Makefile.am` / `autogen.sh`，**没有**预生成的
`configure`。所以 `autoreconf -fi` 是必经步骤，而不是可选优化。
（对比 lftp/4.9.3 用的是自带 `configure` 的 tarball，完全不需要这一步。）

依赖图（`configure.ac` 审计）：

- `LT_INIT` → 需要 libtool 的 m4
- `IT_PROG_INTLTOOL` → 需要 intltool + perl `XML::Parser`
- `AC_CHECK_LIB([readline],[readline])` → **硬要求**，找不到直接 `exit 1`
- `AC_CHECK_FILE([/proc/self/maps])` → 需要 `/proc`
- `AM_PATH_PYTHON([2.7])` → **仅** `--enable-gui` 时；默认关闭

---

## 2. 适配点逐条（均已复现→修复→复验）

### 2.1 E007 平台三元组：三重失败，且必须放在 autoreconf **之后**

autoreconf 生成的 `config.sub` 时间戳是 `2022-01-03`，早于 HarmonyOS 支持。
两个错误**依次**出现，不是同一个：

```
① configure: error: /bin/bash ./config.sub aarch64-linux-ohos failed
   Invalid configuration `aarch64-linux-ohos': OS `ohos' not recognized
   → 补 ohos-linux 三元组 + OS 类型表

② configure: error: ... failed
   Invalid configuration `aarch64-linux-ohos': Kernel `linux' not known to work with OS `ohos'
   → 还必须补 kernel-OS 校验表
```

**框架 perl 脚本的第三个 hunk 是死代码**，本次独立复现（lftp/4.9.3 已记录过）：

```perl
# 2.3 的守卫条件
unless ($sc =~ /linux-ohos/) { ... }
# 但 2.1 刚刚写入了 basic_os=linux-ohos
```

守卫条件在 2.1 之后**必然**为真，所以 kernel-OS hunk 永远不执行。
本配方改为**对 kernel 列表本身**做守卫，并在补丁后跑 `sh -n config.sub` 自检。

**顺序铁律**：`autoreconf -fi` 会重新安装 `config.guess` / `config.sub`。
先打补丁再 autoreconf = 补丁被无声覆盖。配方里 E007 严格在 autoreconf 之后。

### 2.2 踩坑：正则重建 case 分支会把 config.sub 写成语法错误

第一版自实现补丁用「分别捕获缩进分组再重建」的方式插入 `ohos-linux` 分支：

```python
m = re.search(r"...basic_os=linux-android[ \t]*\n([ \t]*;;[ \t]*\n)", cs)
```

其中 `basic_os=linux-android[ \t]*\n` 的**尾部** `[ \t]*` 会把下一行 `;;` 的
缩进一起吃掉，于是重建出的分支变成：

```
	ohos-linux)
		basic_machine=$field1-unknown
		basic_os=linux-ohos
		;;
;;            ← 裸 ;;，零缩进
```

`config.sub` 变成 shell 语法错误，而 configure 只报一句极难定位的
`configure: error: cannot run <shell> ./config.sub`，看起来像「缺 shell」。

**改法**：整体克隆 `android-linux` 分支再做字符串替换，缩进天然一致；
并加 `sh -n` 自检把这类问题在打补丁当场就拦下。

### 2.3 readline：静态库 + terminfo 依赖顺序

`readline/8.3` 的 OHOS 包是**纯静态**（只有 `libreadline.a` / `libhistory.a`）。
直接 `-lreadline` 链接失败：

```
ld.lld-15: error: undefined symbol: tputs / tgoto / tgetnum / tgetent / tgetstr / PC / BC / UP
>>> referenced by display.o:(rl_redisplay) in archive libreadline.a
```

根因是**两件事叠加**：

1. readline 的 `package_info()` 只声明 `cpp_info.libs = ["readline", "history"]`，
   **不透传**它自己 `requires()` 的 `ncurses/6.6`；
2. scanmem 自己的 `AC_CHECK_LIB([termcap],[tgetent])` 失败**不致命**
   （action-if-found 为空），所以它不会把 `-ltermcap` 带进 `LIBS`。

解法：scanmem 直接 `requires("readline/8.3")`，Conan 依赖图把 `ncurses/6.6`
带进来并按 **消费者在前、提供者在后** 的顺序聚合
（`-lreadline -lhistory -lncursesw -lformw -lmenuw -lpanelw`），链接即通过。
`ncurses/6.6` 的配方本身注释就写明了这个顺序约定。

### 2.4 intltool / po/ 是死代码

`po/Makefile.in` 在 `AC_CONFIG_FILES` 里，但生成它所需的
`po/Makefile.in.in` 只有 intltool 才会造。不打补丁直接：

```
config.status: error: cannot find input file: `po/Makefile.in.in'
```

补丁 0001 删掉 `IT_PROG_INTLTOOL` 与该 `AC_CONFIG_FILES` 条目。
**零功能损失**，依据是源码级审计：

- 全树没有 `_()`、没有 `#include <libintl.h>`、没有任何 gettext 符号
  （`grep -rn 'gettext\|libintl\|_("' *.c *.h` 无命中）；
- `po` 只在 `SUBDIRS += po gui` 的 `if ENABLE_GUI` 分支里，而 `--enable-gui`
  额外要求 `AM_PATH_PYTHON([2.7])`（EOL，且 CI 无 py2.7）；
- 上游默认配置就是**不开 GUI**。

### 2.5 BSD 别名 `uint`

```
scanroutines.c:372:5: error: use of undeclared identifier 'uint'; did you mean 'int'?
```

sysroot 的 `sys/types.h` **确实**有 `typedef unsigned u_int, uint;`（第 66 行），
问题只是 musl 系头文件不再把它**传递引入**到
`scanroutines.c` / `targetmem.h` / `test/memfake.c`（只有 `ptrace.c` 自己引了）。

`uint` 就是 `unsigned int` 的别名，所以补 `#include <sys/types.h>` 即可，
不改类型、不改语义。

### 2.6 环境适配（沿用已验证先例）

| 措施 | 依据 |
|---|---|
| `chmod 0755` 补回 autoreconf 生成的辅助脚本 | E490（HMDFS 解包不保执行位） |
| `CONFIG_SHELL`/`SHELL` 显式指向 `/system/bin/sh`（**必须设，不能 unset**） | 见下方踩坑 |
| `make -j1` | E074（HMDFS jobserver fifo EPERM） |
| 原生构建，不传 `--host/--build` | R1/E007。传了会让 `AC_CHECK_FILE(/proc/self/maps)` 直接报 `cannot check for file existence when cross compiling` |

**`CONFIG_SHELL` 只能设不能 unset**：gtypist/2.10.1 用的是
`env -u CONFIG_SHELL`，但本项目直接照搬会踩第二个坑——unset 之后 autoconf
回落到硬编码的 `/bin/bash` 去跑 `config.sub`，而 OHOS worker 没有它：

```
configure: error: cannot run /bin/bash ./config.sub
```

显式设成健康 shell 同时解决「hnp bash 在 HMDFS 上 getcwd 失败」和这个回落问题。

---

## 3. 测试

### 3.1 上游测试（口径：10 条）

`test/Makefile.am` 只有 **1 条** automake 条目（`TESTS = sm_test.sh`），
`sm_test.sh` 内部用 `test_sm()` 包了 **10 次** `../scanmem -p $pid -e -c "..."`：

| # | 命令 | 覆盖 |
|---|---|---|
| 1 | `option scan_data_type int8;0;exit` | int8 基础扫描 |
| 2 | `…int8;snapshot;exit` | 快照 |
| 3 | `…int8;snapshot;1;exit` | 快照后写入 |
| 4 | `…int8;1;delete 0;1;exit` | 按区间删除 |
| 5 | `option scan_data_type int;1;exit` | 任意宽度整型 |
| 6 | `…float;1;exit` | 浮点 |
| 7 | `…number;1;exit` | 数字 |
| 8 | `…bytearray;<257×"00 ??">;exit` | 257 项通配字节数组（强制完整分块扫描例程） |
| 9 | `…string;"<257 个 a>";exit` | 长字符串 |
| 10 | `…int32;<哨兵>;list 5;exit` | **本包补充**：让结果可判定（见下） |

补充第 10 条的理由：`sm_test.sh` 自身用了 `set -ev`，但它对
「扫描没命中」和「扫描命中」区分得不够硬。第 10 条利用
`handler__list()` 在 `num_matches == 0` 时 `return false`、配合 `-e`
（errexit）转成非零退出码这一事实，让「确实扫到了」变成可断言的信号。

`build()` 会跑 `make check` 并解析 `test/test-suite.log`，
把结果写进 `HMBS_UPSTREAM_TEST_RESULT`。**上游测试失败不否决打包**
（leatherman/1.12.1 + lftp/4.9.3 先例），但状态如实记为 `failed` 并附 gaps。

### 3.2 test_package（8 项消费者断言，全部真实执行）

| # | 断言 | 性质 |
|---|---|---|
| t1 | `scanmem --version` 输出含 `scanmem version 0.17` | 上游原样 |
| t2 | `scanmem --help` 输出含 `Usage: scanmem` / `--pid=pid` / `--command` | 上游原样 |
| t3 | `scanmem -p 0` 被拒，输出 `invalid pid` 且非零退出 | 负向测试 |
| t4 | 对已知哨兵 `0x0BADF00D`(=195948557) 扫描 + `list 5` 成功 | **真实内存扫描** |
| t5 | `snapshot` → 写入 → `delete 0;1` 往返 | 真实内存改写 |
| t6 | 257 项通配字节数组扫描（分块扫描例程） | 真实深路径 |
| t7 | `dlopen`+`dlsym` 打包的 `libscanmem.so.1`，`sm_get_version`/`sm_printversion` 可解析且版本为 0.17 | **鸿蒙特有** |
| t8 | 打包布局完整：`bin/scanmem` + `lib/libscanmem.so.1` + `include/scanmem/scanmem.h` | **鸿蒙特有** |

t7 是本包真正的鸿蒙特有断言：它验证 libtool 的
`-export-symbols-regex '^sm_|^show_'` 生成的版本脚本在 **OHOS 动态链接器**下
确实只导出公共 API（实测 59 个 `sm_`/`show_` 符号），且 `.so` 自身依赖能解析——
这是 CLI 的 `--version` 冒烟永远证明不了的一层。

### 3.3 两个会直接把 CI 拉红的坑（已修）

1. **绝不能写 `self.run("scanmem --version")`**。
   `main.c` 对 `-v` 的处理是 `printversion(stderr); exit(EXIT_FAILURE)`——
   成功也返回 **1**。放进 `test()` 会被 Conan 当失败抛异常。
   同理 CI 的 L2 冒烟对这个包只会给非阻塞 `warn`，这是上游行为，不改。
2. **`scanmem --version` 之后不能接 `&&`**。
   `… && grep -q "scanmem version 0\.17"` 会因非零退出短路，
   grep 根本不执行，断言必假失败。t1/t2 已改为「先无条件跑，再单独 grep 判定」。

---

## 4. 本地验证与一处**必须说明**的运行期差异

`conan create`（`-pr:h/-pr:b=ohos-aarch64-wsl`）实测结果：

- 构建/打包：**PASS**，`Package '88569b18…' created`
- test_package 编译（两个辅助程序）：**PASS**
- test_package 运行：**本机被阻**

本机运行被阻的原因**不是配方问题**，而是本地 guest 运行时与真机 OHOS 的 ABI 差异：

| 事实 | 证据 |
|---|---|
| registry 的 `libreadline.a`（真机 OHOS 构建）引用 `__fd_chk` ×2 | `nm -u` |
| **真机 OHOS libc 导出 `__fd_chk`** | `readelf -sW <OHOS SDK>/sysroot/…/libc.so` → 命中 1 |
| **本机 guest libc 不导出 `__fd_chk`** | `readelf -sW /opt/ohos-guest/lib/libc.so` → 命中 0 |

于是任何链接了 registry OHOS readline 的 aarch64 二进制在本机
`Error relocating …: __fd_chk: symbol not found`，而真机上该符号由
OHOS 自带 libc 提供。

为了**验证断言本身是对的**（而不是靠猜），我用本机可访问的
**真机 OHOS SDK sysroot**
（`/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot`）
重新构建了一份 scanmem，并用一个**仅存在于本机、且不进入交付物**的
`__fd_chk` 桩（`LD_PRELOAD`）补上 guest 缺失的符号，实跑结果：

```
PASS t1 version_string
PASS t2 help_usage
PASS t3 reject_invalid_pid
target pid 56418
PASS t4 find_sentinel
PASS t5 snapshot_delete
PASS t6 bytearray_wildcard
PASS t7 libscanmem_exports
PASS t8 packaged_layout
Results: 8/8 consumer checks passed
```

即：8 条断言（含 3 条真实内存扫描/改写）在 aarch64 OHOS ABI 下**全部成立**。

> ⚠️ **诚实边界**：本机 `conan create` 的 test_package 阶段仍会红，
> 因为本机运行时缺 `__fd_chk`。**运行时结论以 CI 真机为准**，
> 本报告不把本地运行期结果当作 success 上报。

> ✅ **该开口已被真机 CI 闭合**（2026-09-30）：平台 CI 构建 **#65258**
> （worker `OpenHarmonyPCDeveloper-CI-039`）在真机 OHOS 上判定
> **Conan test_package: 通过 / L0 门禁: 通过 / L1 门禁（测试执行验证）: 通过**，
> `conan-build-test` 等 7 个步骤全 ✅。真机 libc 自带 `__fd_chk`、不需要本机那个桩，
> 详见 §5.8。故本地运行期红**不代表**真机红，真机结论为绿。

---

## 5. CI 实跑记录（build #64615 → 本地定位与修复）

### 5.1 第一次红灯：#64615 = worker 故障（层 A），与内容无关

`PR #13783`，构建 **#64615**，worker `OpenHarmonyPCDeveloper-CI-018`，
`## CI 校验失败` 评论 id=192137847。

| 步骤 | 结果 |
|------|------|
| worker_preparation / worker-prep / git-clone / checkout-pr / conan-setup | ✅ |
| conan-build-test | ❌ |
| cleanup | ❌ |

失败日志只有两行，且**耗时 0.046 秒**：

```
zsh:1: fork failed: out of memory
elapsedTime=0.045960
```

`cleanup` 步骤以完全相同的方式（`fork failed: out of memory`，0.069s）失败。
判层依据（对应「层 A：worker 故障」的典型迹象：报错 `fork failed: out of memory`
+ 耗时 < 1s + 失败步骤与内容无关）：构建在 zsh 第一次 fork 时就死了，
**一个字节的源码都没编译**，与本包内容无关。

worker 侧证据（`/api/dashboard/worker-stats`，`recentBuilds` 0=成功/2=失败）：

- 平台共 **47 个 worker，last-10 成功率全部为 0/10**，
  「有近期成功的 worker」集合为**空**——不存在可挑选的健康 worker；
- 本次 worker CI-018 的 last-10 同样 0/10（历史累计成功率 35.3%）；
- `/api/ci/builds?limit=10` 连续 3 次采样（约 5 分钟）完全不变，
  最新构建仍停在 `68069 @2026-09-24`，且 **10 条全部 failed**、
  分布在 7 个不同 worker 上。

→ 结论：**平台级 worker 容量/OOM 故障**，属调度问题，不改代码。
处置：不做任何产品代码改动；按平台 SHA 去重规则，需要新 SHA 才能重新排队，
故用一次**如实记录时间线**的 notes 提交产生新 SHA 后再 `/rebuild`。

### 5.2 worker 恢复后暴露的真实内容红灯：L1e（层 C）

在本地同源门禁上跑到 L1e 时出现**确定性红灯**（此前被 worker OOM 掩盖）：

```
[sabotage] bin/ moved away
[sabotage] lib/ moved away
[sabotage] include/ moved away
[fail] L1e: test passed WITHOUT package artifacts — fake test detected (R34)
```

**根因不是测试内容空壳，而是 `can_run` 在 L1e 的调用方式下恒为 False。**

L1e 用的是**单个 `-pr`**：

```bash
conan test "$TEST_PKG_DIR" "${pkg_name}/${pkg_ver}" -pr "$PROFILE_FILE" --build=missing
```

而 Conan 2 里单个 `-pr` 只作用于 **host**，`settings_build` 回落到机器默认
profile。实测（探针 recipe 打印 `settings` 与 `settings_build`）：

| 调用方式 | host | build | `cross_building` | `can_run` |
|---|---|---|---|---|
| `conan create … -pr:h -pr:b`（流水线用） | OHOS/armv8 | OHOS/armv8 | False | **True** |
| `conan test … -pr`（L1e 用） | OHOS/armv8 | **Linux/x86_64** | True | **False** |

`can_run()` 的定义就是 `not cross_building(self)`。于是原版
`test()` 里的 `if not can_run(self): return` 在 L1e 场景下**直接 return
且返回成功** → 零断言执行 → L1e 判定为「假测试」。

**修复（两处，均在本包内，未改任何框架文件）**：

1. **去掉 `test()` 里的 `can_run` 静默短路**。本执行器是 aarch64 OHOS 原生，
   产物本就能跑；若将来真有跑不了的执行器，应当**显式失败**而不是静默
   报成功（R34「0 执行一律不可交付」）。
2. **让 test_package 具备真实的编译期+链接期依赖**：新增
   `test_package/check_api.c`，`#include <scanmem/scanmem.h>` 并链接
   `-lscanmem`；`build()` 用依赖包真实的 `cpp_info.includedirs/libdirs`
   编译它。`include/` 与 `lib/` 被移走后链接必然失败，测试随即失败——
   这正是 L1e 期望的形态。t7 也因此升级为**双重证明**：
   `check_api`（链接期符号解析）+ `check_libscanmem`（dlopen 运行期解析）。

修复后 L1e 实测：

```
[ok] L1e: Negative test confirmed — test genuinely depends on scanmem
```

### 5.3 第二次内容红灯：`_verify_config_sub` 硬编码 `sh`（层 C，#64654）

构建 #64654（worker CI-030）跑完 5 个准备步骤后在 `conan-build-test` 失败，
报错链极其明确：

```
ERROR: scanmem/0.17: Error in build() method, line 368
	self._patch_autotools_ohos()
while calling '_patch_autotools_ohos', line 267
	self._verify_config_sub(cs_path)
while calling '_verify_config_sub', line 278
	proc = subprocess.run(["sh", "-n", cs_path], capture_output=True)
FileNotFoundError: [Errno 2] No such file or directory: 'sh'
```

**根因是我自己加的安全网写死了 `sh`。** CI worker 的 PATH 是
`/data/app/bin:/system/bin:/system/sbin:/vendor/bin:/storage/Users/currentUser/.local/bin`
加 profile 注入的 `/data/service/hnp/bin`，**这些目录里没有 `sh`**。
本地 WSL 有 `/bin/sh`，所以本地怎么跑都发现不了——典型的
「设备原生/本地成功不可迁移」。

同一份日志里 `E007 config.guess HarmonyOS branch added` /
`config.sub ohos-linux triplet added` 都已经打上，说明补丁逻辑本身在真机是对的，
只是紧随其后的自检崩了。

日志里成片的

```
[fail] [Errno 2] No such file or directory: 'curl'
[WARN] Failed to pre-download v0.17.tar.gz, will rely on conan's download
```

是 CI **预下载**步骤的告警，**非致命**（随后 conan 自己的下载器正常工作，
`Exporting package recipe` → `autoreconf` 都跑起来了），与本次失败无关。

**修复（把「假设存在」全部改成「探测存在」）**：

1. 新增 `_shell()`：依次探测 `CONFIG_SHELL` → `which sh` → `which bash` →
   `/data/service/hnp/bin/bash` → `/system/bin/sh` → `/bin/sh`，
   只接受「文件存在且可执行」的候选；一个都没有就返回 `None`。
   `_verify_config_sub()` 拿到 `None` 时**告警并跳过**自检而不是崩溃
   （configure 仍会隐式校验 config.sub，只是报错信息差一些）。
2. `_good_shell()` 改为只返回**确实存在**的路径，否则退到 `_shell()`。
   绝不把不存在的路径交给 configure——否则会撞上
   `configure: error: cannot run <shell> ./config.sub`，
   与「config.sub 被改坏」这个必须区分的故障长得一模一样。
3. `make check` 的上界改用 `_timeout_bin()` 解析出的**绝对路径**并加引号
   （`"/usr/bin/timeout" --signal=KILL 900 make check`），
   不再靠 PATH 里的裸 `timeout`；两者都探测不到才退回无界并告警。

### 5.4 第三次内容红灯：HMDFS `umask 077` 导致 config.status 写不出临时文件（层 C，#64927）

构建 #64927（worker CI-011）。前一轮的 `sh` 问题已修复，configure 这次跑到了
第 438 行才失败，且失败点非常典型：

```
configure: creating ./config.status
./config.status[1001]: can't create ./confLGAKDj/subs1.awk: Permission denied
config.status: error: could not setup config files machinery
```

注意前面 430–436 行**全部通过了**，包括关键的两条：

```
checking for /proc/self/maps... yes
checking for /proc/self/mem... yes
checking for readline in -lreadline... yes
```

**根因 = E011（HMDFS uid 映射）**。autoconf 的 `config.status` 用
`umask 077 && mktemp -d "./confXXXXXX"` 建临时目录；HMDFS 把目录属主 uid 映射成
另一个 uid，于是 0700 的目录**当前进程写不进去**。

关键点：**命令行的 `umask 022` 救不了它**，因为 `configure` 与 `config.status`
各自在脚本内部重新 `umask 077`，覆盖掉继承值。必须在**生成之后、
再执行之前**改写脚本本身——这正是 E011 推荐的 `edit-umask-in-configure`。

**修复**：新增 `_relax_autoconf_umask()`，两处都改（缺一不可）：

1. `configure` 在**运行前**改（它会顺带生成 config.status）；
2. 生成的 `config.status` 再改一次——**真正报错的是它**
   （`./config.status[1001]`），它带着独立的一份 `umask 077`；
   改完若 `Makefile` 仍缺失则重跑一次 `config.status` 兜底。

单元复验（隔离执行该方法）：能改写、结果含 `umask 022`、无残留 `umask 077`、
**二次调用为空操作**（幂等）、文件缺失与 `None` 参数均不抛异常。
本地门禁日志确认生效：`scanmem: E011 relaxed umask 077->022 in configure`。

> 本地 WSL 是普通 ext4，天然可写，所以本地**永远复现不出** E011；
> 这也是必须按知识库条目（而不是凭直觉）处理的原因。

### 5.5 顺带加固：`make check` 加超时上界（900s）

`test/sm_test.sh` 的 10 条 `test_sm` 都是对活进程（4 MiB 的 `memfake`）做真实扫描，
且**自身没有任何 per-test 超时**。若目标平台读不到别的进程的 `/proc/<pid>/mem`
（见 §6 风险），一次扫描可能**阻塞而不是失败**。不设上界时它会吃掉整个
CI 步骤预算（14400 s = 4 h），**一个结论都产不出来**——这正是构建 #64654
超过 4 小时仍无任何结果时最需要排除的形态。

因此把 `make check` 包进 `timeout --signal=KILL 900`（900 s 对健康主机是
极大余量：10 次扫描本地不到 1 分钟），并对 137/超时做显式识别，
在 `HMBS_UPSTREAM_TEST_RESULT` 里以 environment gap 如实记录
（思路同 lftp/4.9.3 的 per-test `timeout` 包装）。同时 `build()` 不再用
`can_run` 门控上游测试：跑不了就该**快速失败并留下证据**，而不是静默跳过。

本地复验：门禁仍 rc=0，日志中可见
`CONFIG_SHELL="/system/bin/sh" timeout --signal=KILL 900 make check`，
上游 10/10、消费者 8/8、L1e `[ok]`。

### 5.6 修复后本地同源门禁全绿

```
CI_PACKAGES="archives/s/scanmem/0.17" CI_BRANCH="feat/scanmem-0.17" \
  CI_PR_NUMBER="13783" zsh ci/conan/build_and_test.sh     → rc=0
[step] All packages built and tested successfully ✅
```

| 阶段 | 结论 |
|------|------|
| G0 / G0e | pass（541 entries；根目录白名单通过） |
| L0（含 L0a–q） | **pass**（含 L0i 依赖在仓、L0j 无版本撞车、L0k commands.json、L0m 目录结构、L0n 分支名） |
| KC（KC1–5） | pass |
| JC（JC1–6） | pass |
| L1a/L1b/L1c/L1d/L1e | **全部 ok**（含 `[ok] L1e: Negative test confirmed`） |
| L2 | skip（非阻塞）：`scanmem --version` 按上游语义 `exit(EXIT_FAILURE)`，见 §3.3 |
| L4 | pass（patches clean） |
| L5 | pass（bin/ has content） |
| 上游用例 | `HMBS_UPSTREAM_TEST_RESULT` status=passed，10/10 |
| 消费者断言 | `HMBS_TEST_PACKAGE_RESULT` passed=true，8/8 |

> 本地复现说明：本机 WSL guest 的 glibc 不导出 `__fd_chk`（真机 OHOS libc 导出，
> 见 §4），因此本地跑 t1–t6 需要一个**仅本机、不进入交付物**的 `__fd_chk` 桩
> （`LD_PRELOAD`）。真机 CI 不需要任何桩。

### 5.7 顺带修掉的仓库既有红灯

rebase 到最新 `origin/main`（`445d5d05db`）后，main 上的 `junk_check.sh`
已改为 **prdiff 模式**（只检查本 PR 变更文件）。原先在旧 base 上 JC1/JC5
报出的 5 个运行时状态文件（cloog / kics / libbfio / thc）不再计入本 PR，
JC 全绿。

### 5.8 真机 CI 绿灯（build #65258）——§4 / §6 的运行期开口在此闭合

| 项 | 结果 |
|---|---|
| 构建 | **#65258**，worker `OpenHarmonyPCDeveloper-CI-039` |
| `conan-build-test` | ✅ |
| Conan test_package | **通过** |
| L0 门禁（结构完整性） | 通过 |
| L1 门禁（测试执行验证） | 通过 |
| 其余步骤 | `worker_preparation` / `worker-prep` / `git-clone` / `checkout-pr` / `conan-setup` / `cleanup` 全 ✅ |

平台评审 rule7 亦独立判定「CI 状态: 通过 #13783」。

**为什么这条结论对当前 HEAD 成立**：CI 是**评论触发型**门禁（`push` 本身不触发
CI），故本 MR 曾用一次 `--allow-empty` 空提交 `92341408b1` 换新 SHA 求重排队。
该空提交与父提交 `2308fc6cc4` **内容完全一致**（`git diff 2308fc6cc4 92341408`
为空），因此 #65258 所构建的内容与当前 HEAD 逐字节相同，结论可直接适用。

**这条绿灯同时证实了三件事**：

1. **§4 的 `__fd_chk` 运行期差异确实只是本机差异**——真机 libc 自带该符号，
   无需本机 `LD_PRELOAD` 桩，test_package 在真机原生跑通。
2. **§6 的跨进程 `/proc/<pid>/mem` 风险已在真机排除**——t4/t5/t6 依赖跨进程
   内存读取，test_package 通过即证明真机 OHOS 允许该访问（见下节）。
3. **test_package 不是空壳**——L1 门禁（测试执行验证）含 L1e 破坏性负向测试，
   它通过说明 `build()` 确实硬依赖打包产物（拆走 `bin/`+`lib/`+`include/`
   就会链接失败）。

> 计数口径说明：平台 CI 评论只给通过/不通过结论，**不含**逐条计数器；
> 上表 8/8、10/10 的具体计数取自本地实测（§4、§5.6）。
> 真机原始计数以 CI 完整日志为准，本报告不代为推断。

---

## 6. 风险提示（留给 CI 验证）—— 已在真机验证通过

上游 10 条用例和本包 t4/t5/t6 都需要 scanmem 读取**另一个进程**的
`/proc/<pid>/mem`。若真机 OHOS 的访问控制拒绝跨进程内存读取，
这些用例会一起失败。配方选择**如实变红**而不是把断言放水成永远通过
（`0 执行一律不可交付`；L1e 负向测试也会拆穿空壳测试）。
真机结果以 `HMBS_UPSTREAM_TEST_RESULT` 与 CI 日志为准。

> ✅ **结论：真机 OHOS 允许跨进程内存读取，风险已排除。**
> 平台 CI 构建 **#65258**（worker CI-039）判定 Conan test_package **通过**
> 且 L1 门禁（测试执行验证）**通过**；t4/t5/t6 恰好就是依赖跨进程读取的三条断言，
> 它们通过即证明该访问在真机被允许。详见 §5.8。
>
> 本节刻意保留原始风险陈述而不删改——它记录的是配方**当初的取舍**（选择如实变红、
> 不放水断言），这个取舍本身没有被推翻，只是其担忧的风险已被实测排除。
