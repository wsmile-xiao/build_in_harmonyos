# pd-osc 0.3.1 适配笔记

## 上游构成

`pd-osc` 是 Pure Data 发行版里的 OpenSoundControl 外部对象集合，源码是上游官方
GitHub tag 归档 `pd-externals/osc` 的 `v0.3.1`（commit `c2c73e7`）：

```
https://codeload.github.com/pd-externals/osc/tar.gz/refs/tags/v0.3.1
HTTP 200, 52675 B
sha256 = a9a4287d0f665fa6108e58564611054079b0bc0be39cbe11b51875d532ee2f79
```

它从老的 `pd-mrpeach` 项目独立而来，只负责 OSC 消息的打包/解包，传输层另说。
构建用上游自带的 `pd-lib-builder`（`Makefile` + `pd-lib-builder/Makefile.pdlibbuilder`）。

### 关键坑：`lib.name = osc` **不**产生合并的 `osc.pd_linux`

上游 Makefile 这么写：

```make
lib.name = osc
class.sources = pipelist.c routeOSC.c
packOSC.class.sources   = packOSC.c   OSC_timeTag.c
unpackOSC.class.sources = unpackOSC.c OSC_timeTag.c
```

直觉上 `class.sources`（无类名）会生成一个名为 `osc` 的库 blob，把
[pipelist] 与 [routeOSC] 合进去 —— **不对**。`Makefile.pdlibbuilder` 第 717 行附近有

```make
$(notdir $(basename $v)).class.sources += $v
```

它把裸 `class.sources` **按源文件名重写成每个文件一个 `<basename>.class.sources`**，
于是实际产物是 **4 个** 独立 `.pd_linux`：

| 产物 | 来源 |
|------|------|
| `packOSC.pd_linux` | `packOSC.class.sources` |
| `unpackOSC.pd_linux` | `unpackOSC.class.sources` |
| `routeOSC.pd_linux` | 裸 `class.sources` 拆分 |
| `pipelist.pd_linux` | 裸 `class.sources` 拆分 |

第一版配方按“3 个产物 + `[declare -lib osc]`”写，被 build() 里的产物名断言当场
拦下（`pd-lib-builder did not produce osc.pd_linux (got packOSC.pd_linux,
pipelist.pd_linux, routeOSC.pd_linux, unpackOSC.pd_linux)`）—— 这就是为什么配方断言
的是**具体文件名**而不是个数。好消息：四个类都按类名自动加载，补丁里**不需要**
`[declare -lib osc]`。

## 构建

- **Pd API 头**：制品仓的 `puredata/0.54.1` 是 *application*，只装 `pd` 与数据目录，
  **不装** `m_pd.h`。配方在 `source()` 里额外拉取同一上游版本 `pure-data 0.54-1`
  的源码树（`codeload.github.com`，sha256 与 `puredata/0.54.1` 配方里钉的同一个
  `19a0e2bf…f31353`），把 `PDINCLUDEDIR` 指向其 `src`。
- `pd-lib-builder` 用 `$(CC) -dumpmachine` 判断目标系统；OHOS clang 报
  `aarch64-...-linux-ohos` → 选中 Linux 分支与 `pd_linux` 扩展名。`CC` 由配方的
  `tools.build:compiler_executables` 显式传入。
- 纯 C99，只 include 公开的 `m_pd.h`，**不碰** Pd 内部头（`m_imp.h`/`s_stuff.h`），
  `patches: []` 为空。
- 命令：`make -j1 CC=<ohos clang> PDINCLUDEDIR=<pd-api>/src`，链接行只带
  `-rdynamic -shared -fPIC -Wl,-rpath,"$ORIGIN",--enable-new-dtags … -lc -lm`。
- 无三方依赖。

## 关键坑：`package()` 里 `copy("*.pd")` 会把整个 pure-data 打进包

`source()` 把 pure-data 源码树解在 `<source>/pd-api/`，而 conan 的 `copy()` 对 glob
**是递归的**。所以

```python
copy(self, "*.pd", self.source_folder, ext)      # ← 打包了 373 个 Pd 自带文档补丁
```

第一版配方实测出来的包是 **390 个文件**，`lib/pd-externals/pd-api/doc/…`、
`lib/pd-externals/pd-api/extra/…` 全是 Pd 自己的 example / help 补丁。

修法：`package()` 改成用 `os.listdir()`（**非递归**）逐个拷顶层文件，并显式列出
`EXPECTED_BLOBS` 做产物校验。修完之后 `Packaged 4 '.pd_linux' files` +
`Packaged 9 '.pd' files` + `LICENSE.txt` + `README.md` = **15 个文件**，
`conanmanifest.txt` 里 `pd-api` 命中数 0。

> 注意：conan 2 在 `package()` 前**不会**清空复用中的 package 目录。改配方重打包时，
> 上一版遗留的文件会留在磁盘上并被写进 `conanmanifest.txt`。验证打包是否干净要
> **先删掉旧的 package 目录再重跑**，否则会误判。

## 产物

| 路径 | 说明 |
|------|------|
| `lib/pd-externals/*.pd_linux` | 4 个外部对象（30776 / 16208 / 21896 / 21608 B） |
| `lib/pd-externals/*.pd` | `osc-meta.pd` + 6 个帮助补丁 + 2 个 stream 抽象补丁 |
| `licenses/LICENSE.txt` | GPL-2.0-or-later |
| `share/doc/osc/README.md` | 上游 README |

产物校验：`file(1)` 四个都是 `ELF 64-bit LSB shared object, ARM aarch64`；
`readelf -d` 每个 `NEEDED = [libc.so]`、`RUNPATH = [$ORIGIN]`、**TEXTREL 0**；
每个 blob 引用 **0 个** glibc FORTIFY `__*_chk` 符号（所以不存在 `puredata`
那个 `__fd_chk` 类的重定位坑）；`nm -D` 各导出自己的 `*_setup`
（Pd 加载外部对象的入口）。

## 测试

上游无自动化测试套件（只有 6 个帮助补丁 + 2 个 stream 抽象补丁 + `osc-meta.pd`）
→ 上游 N=0。

消费者测试 `test_package/test_pd_osc.sh`（4 项断言）用**真机 OHOS 的 `pd`**
无头加载安装后的外部对象，把一条 OSC 消息走完整往返：

- `[packOSC]`：`/ping 1 2` → 字节列表
  `47 112 105 110 103 0 0 0 44 105 105 0 0 0 0 1 0 0 0 2`
  （`/ping` 补齐到 8 字节 + typetag `,ii` + 两个大端 int32）—— 逐字节对齐期望值，
  不是只看“有输出”。
- `[unpackOSC]`：字节列表 → `/ping 1 2`（精确往返）。
- `[routeOSC]`：未注册 method，`/ping 1 2` 整条落到 catch-all outlet。
- 反证：pd 输出里不允许出现 `couldn't create` / `couldn't find`。

写补丁时踩到的两个 Pd 细节（都靠本地跑真 pd 发现，不是猜的）：

1. 消息框（`msg`）连上去**不会**自己触发，必须 `[loadbang]` → 消息框 inlet。
   一开始漏了 loadbang，packOSC 收到的是初始化用的 bang，报
   `error: packOSC: bad path: 'bang'`。
2. 分流要用 `[t l l]`（list）而不是 `[t b b]`（bang）—— `t b b` 会把字节列表变成
   一个 `bang` 符号，导致 print 打出 `PDOSC_BYTES: bang`。

qemu 真机验证（aarch64 OHOS `pd` + `/opt/ohos-guest` musl runtime + 预先编好的
`libchkfcnshim.so` 预加载，解决 `puredata/0.54.1` 自带的 `__fd_chk` 缺失）：
`PDOSC_CHECK_SUMMARY fails=0`，脚本 rc=0，4/4 通过。
## 2026-10-10 复审记录
- PR 标题与描述已按模板补全（【积分赛】前缀 + 5 字段 + 统计表 + 验证结果），
  本提交用于触发平台 Septest 对最新状态重新审查（此前裁决读到的仍是旧元数据）。
- CI 构建通过，test_package 4/4 通过（PDOSC_CHECK_SUMMARY fails=0）。

## 2026-10-12 整改轮：CI #84846「编译失败」是 worker fork EAGAIN，不是配方缺陷

### 先记两条取证纪律（本轮都踩了）

1. **PR head 只能取 API 的 `head.sha`**。上游组织仓
   `OpenHarmonyPCDeveloper/build_in_harmonyos` 里也有一个同名分支
   `feat/pd-osc-0.3.1`，但它指向 `11eb127e`，而 **PR head 实际是 fork 仓的
   `a0ae9bd4`** —— 两者从 `c182ef81` 就分叉了。只查上游那侧会把「CI 构建了哪个
   SHA」整个判反。已登记为 T480。
2. **worktree 的仓库级身份会被上个会话留下别人的值**。本轮开工时
   `git config --local user.name` 是 `lxx0329` / `2028594439@qq.com`，
   与 PR 作者 `lkyz` 不符。提交前必须核对并改回 `lkyz`
   （T130/T461；本轮 push 前已改，并实测 `ssh -T atomgit-acc1` → `Welcome to
   GitCode, lkyz`）。

### 裁决与真正的问题

管理员裁决（PR !14861，评论 `193184317`，2026-10-11T11:42）rule6/rule7 双 FAIL，
两者都只是**时序**：最新提交晚于最新 AI 检视 / 最新 CI 结论。按 T010/T444，
这两条**不为它们改代码**。但 2026-10-11T21:31 出现了真正的红灯：

```
o/bin/sh: can't fork - try again
opd-lib-builder//Makefile.pdlibbuilder:823: Where is Pd API m_pd.h? Do 'make help' for info.
o/data/service/hnp/bin/clang ... -o routeOSC.pd_linux.o -c routeOSC.c
o/bin/sh: can't fork - try again
omake: *** [pd-lib-builder//Makefile.pdlibbuilder:978: routeOSC.pd_linux.o] Error 1
```

机器人把它归类成「编译失败 (make/gcc) → 可能需要为 OHOS/bionic 添加 patch」，
**这个诊断是错的**（对照 T021「机器人失败标签可能是错的」）：

1. `Where is Pd API m_pd.h?` 是 `$(warning)`，由 `$(shell ls "$(PDINCLUDEDIR)/m_pd.h")`
   触发。它出现 = **那次 `ls` fork 失败**，不等于 Pd API 头不存在。T321 已把这条
   记成「fork EAGAIN 伪装成编译失败」的判别式。
2. 整份 CI 日志里**没有一条编译器 `error:` 诊断**（只有 conan 自己的
   `ERROR: ... Error in build() method` 两行壳），`undefined reference` = 0。
3. **同一 head `a0ae9bd4` 在 1.5 小时前刚绿过**：构建 `#84770`
   （worker `OpenHarmonyPCDeveloper-CI-006`，19:52:53）CI 校验通过；
   `#84846`（worker `CI-030`，21:31:45）失败。同 SHA、同 profile、同包路径，
   只换 worker 就翻红 → 结论落在平台侧，不在配方侧。

判定：**B 类平台故障（worker fork 资源耗尽）**。按 T177/T307/T316，处置是
**重排构建，不改配方**（T141：同一 SHA 的 `/rebuild` 会排到新构建）。

### 补强证据：三次构建一绿两红 + 横向取证

后续又落一次构建，同一 head `a0ae9bd4`，**日志逐字同签名**：

| 构建 | 起止 | Worker | 结论 |
|---|---|---|---|
| #84770 | 2026-10-11T19:47 → 19:52 | OpenHarmonyPCDeveloper-CI-006 | ✅ 通过 |
| #84846 | 2026-10-11T21:19 → 21:31 | OpenHarmonyPCDeveloper-CI-030 | ❌ 失败（fork EAGAIN） |
| #84994 | 2026-10-12T00:06 → 00:10 | OpenHarmonyPCDeveloper-CI-016 | ❌ 失败（fork EAGAIN，逐字同签名） |

横向取证（T321 §5「同期其它 PR 是否也在报 EAGAIN」）：扫 2026-10-12 前后
14 个活跃 PR 的最近一次 `CI 校验失败`，**PR !14786**（构建 `#85013`，
worker `OpenHarmonyPCDeveloper-CI-016`，00:16:35，机器人同样标成「编译失败」）
带**同一个 fork EAGAIN 签名**。同期其余 12 个 PR 的失败类别是
网络问题 / 测试失败 / 未知，**只有这 2 个 PR 命中 fork EAGAIN**。

即：同一签名跨 PR、跨 worker 同时出现 → 平台侧车道问题，与本配方无关。

### 本轮真正要修的：把本机验证 shim 从配方里拿掉

上一个提交（`a0ae9bd4`）在 `test_package/conanfile.py` 里加了一段 LD_PRELOAD 注入，
把本机 qemu 验证环境的 shim 绝对路径（`<guest sysroot>/lib/libfdchkshim.so`）
硬编码进了配方（原文已随本提交删除，不在此复贴代码块）。

这与本文件上面「shim 只存在于本机验证环境，不进包、不进 test_package」以及
PR 描述里的同一句承诺**自相矛盾**，且：

- `if os.path.isfile(...)` 让它在 CI 上**静默变成空操作** —— 零 CI 收益；
- 在提交进仓库的文件里硬编码绝对宿主路径，是 rule6 的 P0 类命中项（T024）；
- 属于「为了绿而往包里塞 shim」那一类，踩 T010/T177 的红线。

**修法**：整块删掉。qemu + shim 改由**本机验证环境**提供，不进配方、不进
`test_package`（见下方验证口径）。除此之外本轮对配方**零改动**。

### 本地同源验证证据（WSL ext4，Conan 2.29.1）

先 `conan remove "pd-osc/0.3.1:*" -c` 并删掉残留 package 目录（见上文「conan 2
复用 package 目录」那条），确保是真编译：

```
++++ info: using Pd API /root/.conan2/p/b/pd-os0a2cbfe10b670/b/pd-api/src/m_pd.h
pd-osc/0.3.1: built 4 Pd externals: packOSC.pd_linux, pipelist.pd_linux, routeOSC.pd_linux, unpackOSC.pd_linux
pd-osc/0.3.1: package(): Packaged 4 '.pd_linux' files
pd-osc/0.3.1: package(): Packaged 9 '.pd' files
pd-osc/0.3.1: package(): Packaged 1 '.txt' file: LICENSE.txt
pd-osc/0.3.1: package(): Packaged 1 '.md' file: README.md
error: = 0    EAGAIN/fork = 0    undefined reference = 0    Where is Pd API = 0
```

`using Pd API ...` 正常命中、`Where is Pd API` 警告为 0 —— 这正是 T321 §4 要求的
判别式：CI 那条警告的唯一解释就是 worker fork 失败。

`conan create` 的 test_package 阶段在本机仍报 `__fd_chk: symbol not found`
（本机 qemu musl sysroot 缺口，**不是本包缺陷**，真机 CI 无此问题；
详见 T473）。为避免 shim 泄漏到编译步骤，拆成两步闭环：

- `conan create`（**完全不带 shim**）→ 证明配方自身自洽，build/package 全绿；
- `conan test`（shim 只经**环境变量** `LD_PRELOAD` 注入，不进配方）→
  消费者测试 4/4 通过：

```
PDOSC_BYTES: 47 112 105 110 103 0 0 0 44 105 105 0 0 0 0 1 0 0 0 2
PDOSC_RT: /ping 1 2
PDOSC_ROUTED: /ping 1 2
PASS: pd-osc [packOSC] packs /ping 1 2 as an OSC message
PASS: pd-osc [unpackOSC] decodes it back to the original Pd message
PASS: pd-osc [routeOSC] hands the unmatched message to its catch-all outlet
PASS: every class in the patch was created by Pd
PDOSC_CHECK_SUMMARY fails=0
TEST_RC=0
HMBS_TEST_PACKAGE_RESULT={"executed": true, "passed": true, "consumer_passed": 4, "consumer_total": 4}
```

> 副作用（无害，已核实）：`LD_PRELOAD` 是进程级的，会漏给宿主 x86 进程，宿主
> `ld.so` 会打一行 `object '…/libchkfcnshim.so' … cannot be preloaded: ignored`。
> 客机 `pd` 正常拿到 shim，断言 4/4 不受影响（T400 同类噪音）。

### 取证坑：`conan list` 取 package_folder 的两种失败姿势

> 已登记为 T478。

1. `conan list -p "<ref>" -f json` 的输出顶层是 `{"Local Cache": {...}}`，
   **不是** `{"graph": {"nodes": ...}}`。按 nodes 解析会静默取到空值，
   进而 `EXT_DIR=/lib/pd-externals` 报「externals dir missing」。
2. **磁盘上不能按 `pd-osc*` / `puredata*` 做 glob**：conan 缓存目录名是截断前缀 +
   哈希，本包实际落在 `/root/.conan2/p/b/pd-os0a2cbfe10b670/p`（前缀 `pd-os`
   **不是** `pd-osc`）。要用「目录里有没有特征文件」来认领
   （`lib/pd-externals/`、`bin/pd`），不要按名字猜。

### 平台侧动作记录

- 行级评论：PR 上两条 `diff_comment`（`193105150` / `193184323`，
  「test_package 需复核」）**原本就已是 `resolved: true`**，本轮无需再动，
  回读确认 `unresolved diff comments = 0`。
- 裁决评论 `193184317` 是 `comment_type=pr_comment`，对其 `discussion_id`
  发 `PUT .../comments/41d2fc73…{resolved:true}` 返回
  `400 UN_KNOW "This type of note can not be resolved."` ——
  顶层裁决类评论**平台不允许 resolve**（T162/T363/T430 一致）。处置改为
  **在其下逐条回执 + 不删改原评论**。


## 2026-10-12（次日）收尾轮：rule6/7 时序缺口补齐 + 本地同源复验

### 根因（与上轮一致，本轮复核确认）
裁决 `193184317`（10-11 11:42）rule6/rule7 双 FAIL 是纯时序问题：最新提交
`a0ae9bd4`（10-11 09:55:44）晚于最新 AI 检视（10-10 12:38:14）与最新 CI 结论
（10-10 15:04:25）。非配方缺陷，不为它改代码（T010/T444）。分支上轮已落地
`86503cbc`（10-12 00:16，唯一实质修复：test_package 移除硬编码本机验证 shim）与
`53665ecd`（10-12 00:21，补记取证）。

### CI 现状（截至 10-12 01:20）

| 构建 | 时间 | Worker | 结论 |
|---|---|---|---|
| #85040 | 00:24:51 → 00:29:56 | CI-022 | ✅ 通过（test_package / L0 / L1） |
| #85143 | 01:15:35 → 01:20:40 | CI-011 | ✅ 通过（test_package / L0 / L1） |

两者均覆盖 head `53665ecd`（评论 `193218350`「构建触发中 SHA 53665ecd」+ 两次结论
时间均晚于提交时间 00:21:45）。#84846 / #84994 维持 B 类平台故障判定
（worker fork EAGAIN，见上轮三次构建对照与横向取证）。

### rule6 缺口：AI 检视在途无结论
10-12 00:17 的 `/ai review`（评论 `193216894`）只有「正在进行中」回执
（`193216895`），此后无检视结论评论。按 T483：在途任务屏蔽再触发（重发
`/ai review` 会被拒「已有 AI 任务正在处理中」），rule6 只认**时间晚于最新提交**
的检视结论评论（P0/P1=0）。
处置：其余闭环（本轮本地门禁复跑、本 notes.md 回写、CI `/rebuild`）全部做完，
让检视结论**一落地整个 PR 即合规**；回执标注「AI 检视在途、结论待回填」。
若数小时仍无结论 → 按平台故障报 CI 维护者（T483 §4），不伪造、不催改检视时间。

### 本地同源复验（WSL ext4，Conan 2.29.1，HEAD=`53665ecd`）

协议：先 `conan remove "pd-osc/0.3.1:*" -c` 并清残留 package 目录（T426/T478：
不按 `pd-osc*` glob 定位），再跑**仓内 CI 管线同源**：

```
CI_PACKAGES="archives/p/pd-osc/0.3.1" CI_BRANCH="feat/pd-osc-0.3.1" CI_PR_NUMBER="14861" \
CONAN_PROFILE=ohos-aarch64-wsl JUNK_PR_DIFF=<全新 git diff b95978a4 HEAD，9 文件> \
LD_PRELOAD=/opt/ohos-guest/lib/libchkfcnshim.so    # 只注入测试阶段，不进配方
zsh ci/conan/build_and_test.sh
```

关键输出（滤宿主侧 `cannot be preloaded: ignored` 噪音，T392/T400）：

```
G0_RESULT=pass (542 entries) / G0e: Root directory whitelist passed
[ok] L0: All quality gate checks passed   # L0j 版本未占用 / L0k / L0m / L0n 分支名一致
KC_RESULT=pass  KC_ERRORS=0
JC_RESULT=pass  Junk Files: 0             # JC6: 9 文件全在 archives/p/pd-osc/（T308 喂真实 PR diff）
++++ info: using Pd API /root/.conan2/p/b/pd-os5f6bae25d0863/b/pd-api/src/m_pd.h
pd-osc/0.3.1: built 4 Pd externals: packOSC.pd_linux, pipelist.pd_linux, routeOSC.pd_linux, unpackOSC.pd_linux
package(): Packaged 4 '.pd_linux' + 9 '.pd' + LICENSE.txt + README.md
PDOSC_BYTES: 47 112 105 110 103 0 0 0 44 105 105 0 0 0 0 1 0 0 0 2
PDOSC_RT: /ping 1 2 / PDOSC_ROUTED: /ping 1 2 / PDOSC_CHECK_SUMMARY fails=0
HMBS_TEST_PACKAGE_RESULT={"executed": true, "passed": true, "consumer_passed": 4, "consumer_total": 4}
L1e: [sabotage] lib/ moved away → Negative test confirmed（R34 反向破坏，管线自跑）
L0_RESULT=pass / L1_RESULT=pass / L2_RESULT=skip: no bin/ dir（库包无 bin/）/ L4_RESULT=pass: no patches / L5_RESULT=pass
Build Summary: Total 1 / Success 1 / Failed 0 / Pass rate 100.0% (1/1) / GATE_RC=0
```

计数（create 日志 `.ci_logs/conan_build_pd-osc_0.3.1.log`，233 行）：
`error: = 0`、`EAGAIN/fork = 0`、`undefined reference = 0`、`Where is Pd API = 0`、
`using Pd API = 1` —— 与 86503cbc 轮同签名，仅 package folder 哈希不同
（本轮 `pd-os5f6bae25d0863`）。

### 本轮改动范围
仅 1 个文件：`archives/p/pd-osc/0.3.1/notes.md`（本章节回写）。
配方 / 补丁 / test_package 零改动；PR 描述结论与本文件一致（本轮 body 未动）。

### 交接（给下一会话）
1. 本提交推送后已发 `/rebuild` + `/ai review`；若 /ai review 被回
   「已有 AI 任务正在处理中」，不要刷屏，等原在途任务回填（T483）。
2. 检视结论评论落地后：结论时间晚于最新提交且 P0/P1=0 → rule6 清除，
   届时编辑回执 `193216855` 补最终证据；行级评论两条本就是 resolved=true，回读确认即可。
3. 若在途任务数小时无结论 → 按平台故障报 CI 维护者 / 任务池反馈，不伪造。
