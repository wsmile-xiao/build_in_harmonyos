# recoverdm 0.20 适配记录

## 概述

recoverdm 是 Debian 归档里的**纯用户态**磁盘元数据/坏道抢救工具（作者 Folkert van
Heusden，2003-2004，上游主页 <https://www.vanheusden.com/recoverdm>）。两个可执行文件：

- `recoverdm` —— 逐扇区读取坏盘/坏镜像，坏道多次重试，输出可用数据 + 坏扇区清单
- `mergebad` —— 把同一介质多轮读取出的多份镜像按"坏块表"合并成坏道最少的一份

规模与资质：orig tarball 共 15 个文件，其中 6 个 `.c` + 5 个 `.h` = **1486 行 C**，
`Makefile` 29 行；**零第三方依赖**（只用系统 libc），构建系统是**裸 Makefile**
（无 configure、无 autotools、无 CMake）。

## 源与完整性核验

| 项 | 值 |
|---|---|
| 分发 URL | `https://deb.debian.org/debian/pool/main/r/recoverdm/recoverdm_0.20.orig.tar.gz`（Debian 官方 pool，pristine upstream orig，未重打包） |
| 大小 | 9946 字节 |
| SHA-256 | `0fd4bc3ce4360a12f69c1440bc31ffd29f0e88f38b9279fb4a783a173d4f6f4c` |
| 设备侧复核 | B 机 2026-09-25 02:11 `~/tmp/uc2/z34-recoverdm/recoverdm_0.20.orig.tar.gz`，HTTP 200、9946B、`sha256sum` 与 Debian 索引 `Checksums-Sha256` 逐字符一致 |
| 解压根目录 | `recoverdm-0.20/` ⇒ `source()` 用 `strip_root=True` |

## 构建要点（M18 两臂对照，先复现后修）

上游 `Makefile`（29 行，全文已在设备上逐行核读）关键结构：

```make
VERSION=0.20
CFLAGS=-Wall -Wshadow -Wconversion -Wwrite-strings -Winline -O2 -DVERSION=\"$(VERSION)\"
LDFLAGS=
...
recoverdm: $(OBJSr)
	$(CC) -Wall -W $(OBJSr) $(LDFLAGS) -o recoverdm
install:
	cp recoverdm mergebad /usr/local/bin
```

⇒ 三个适配点：**① Makefile 从不给 `CC` 赋值**（GNU make 落到内建默认 `cc`）；
**② `CFLAGS` 是裸 `=` 赋值且内含 `-DVERSION`**（命令行覆写＝整体替换）；
**③ `install` 目标 `cp` 到烧死的 `/usr/local/bin`**，无 `PREFIX`/`DESTDIR`/`INSTALL` 变量。

### 臂 P1 —— 原样 `make`（复现首错，逐字存档）

命令（B 机 `~/tmp/uc2/z34-recoverdm/armP1`，`PATH=$HOME/usr/local/bin:$HOME/.local/bin:$PATH`）：

```
$ make -j1
cc -Wall -Wshadow -Wconversion -Wwrite-strings -Winline -O2 -DVERSION=\"0.20\"   -c -o recoverdm.o recoverdm.c
make: cc: No such file or directory
make: *** [<builtin>: recoverdm.o] Error 127
RC=2
```

日志：`~/tmp/uc2/z34-recoverdm/armP1-make.log`。旁证：`command -v cc` 在设备上无输出
（OHOS 无 `cc` 别名）；`make --version` = GNU Make 4.4.1 / aarch64-unknown-linux-gnu。

**这正是 B 池件 M18（`suckless-baked-paths-makevar-override`）第一层签名的逐字复现。**

### 臂 P2 —— 按 M18 修法：只在 make 命令行覆写 `CC`

```
$ make -j1 CC=clang
...
clang -Wall -W mergebad.o io.o utils.o error.o  -o mergebad
RC=0
-rwxr-x--- 35200 armP2/recoverdm
-rwxr-x--- 31104 armP2/mergebad
```

日志：`~/tmp/uc2/z34-recoverdm/armP2-make.log`（34 条上游 `-Wconversion` 类告警，
上游未加 `-Werror` ⇒ 不阻塞）。**零补丁、零源码改动即通过。**

M18 的第二层（`X11INC=/usr/X11R6/include` 之类烧死路径 ⇒ 覆写聚合变量 `INCS/LIBS`）
**本包不存在**：recoverdm 零第三方依赖，没有任何 `-I/usr/...`，故配方只覆写 `CC` 一项。

### 本包特有危险面（臂 P3，实测）—— 覆写 `CFLAGS` 会打掉 `-DVERSION`

```
$ make -j1 CC=clang CFLAGS="-Wall -O2"
clang -Wall -O2   -c -o recoverdm.o recoverdm.c
recoverdm.c:22:23: error: expected ')'
        printf("recoverdm v" VERSION ", (c) 2003-2004 by folkert@vanheusden.com\n\n");
                             ^
RC=2
```

日志：`~/tmp/uc2/z34-recoverdm/armP3-make.log`。
⇒ 结论写进配方注释并**刻意不覆写 `CFLAGS`**（R1 参数最少化）；版本宏由上游自带。
`-DVERSION` 是否注入正确，由消费者测试里 `recoverdm -V` / `mergebad -h` 的横幅断言间接可证。

### 其余适配决定

- `basic_layout` + `self.folders.build = "."`（上游 in-source 构建），`make` 于 `source_folder`，`-j1`（R9）
- `CC` 取值：`self.conf.get("tools.build:compiler_executables")["c"]`（R33，**不读裸 shell `${CC}`**）
- **不调用 `make install`**：`package()` 直接把 `recoverdm`/`mergebad` copy 进 `bin/`，`license.txt` 进 `licenses/`
- 上游 `recoverdm.1` 在 0.20 orig tarball 里是 **0 字节空文件**（`wc -c` = 0）⇒ 不安装手册页（安装空文件是噪音）
- `validate()` 用 `self.settings.os not in ("Linux", "OHOS")`（R32）
- `package_type = "application"`，`cpp_info.libs/includedirs/libdirs` 置空、`bindirs = ["bin"]`
- 补丁 0 个（`patches_applied: []`）

## 测试五维账本（R51 上游测试三步法）

**① 上游静态清点（0，附证据）**：tarball 15 个文件无任何测试程序（无 `tests/`、无
`*test*.[csh]`、无 ctest/pytest 注册项）；`Makefile` 目标只有
`all / recoverdm / mergebad / install / clean / package` ⇒ 无 `test`/`check` 目标。
`test_package/MANIFEST.yml` 记 `upstream_tests: []`、`upstream_test_in_build: false`。
**上游自动化测试：无。**

**② 上游可运行性**：不适用（无可运行测试项）。

**③ 消费者断言范围**（`test_package/test.sh`，真实执行打包二进制，R34）：
两枚二进制从 conanrun 的 `bin/` 解析且可执行（4 条）；`recoverdm -V` rc=0 + 上游横幅
含版本 0.20（2 条）；`recoverdm -h` rc=0 + stderr 用法行（2 条）；无参数 rc=255（1 条）；
**真实恢复一遍** `-t 1`（FILE 类型，普通文件）rc=0、产物 4096B、`cmp` 与输入逐字节一致、
日志含上游 `Done`（4 条）；`mergebad -h` rc=0 + 横幅（2 条）、无参数 rc=10 + 守卫消息（2 条）；
**真实合并一遍**双镜像 + 坏块表 rc=0、产物 4096B、`[0:1024)` 全取镜像 A、`[1024:4096)` 全取
镜像 B（4 条）；工作目录清理（1 条）。断言总数由脚本末行实跑读数给出（本文件与
manifest/MANIFEST/PR 正文一律照该读数回填，不另造数字）。

**④ 未覆盖面与原因**：裸盘/分区/CD/DVD/软盘读取路径（`-t 10..19`、`-r` RAW 重试、`-s` 转速）
与 `-l` 坏扇区清单的真实产出，需要**真坏道介质或 root 的 loop 设备**，HarmonyOS PC 构建主机
不具备；且伪造"读失败"输入等于伪造测试，故不做。已如实写进 `MANIFEST.yml` 的 `not_covered`。

**⑤ 判定口径**：包内二进制可执行 + 版本/用法输出可识别 + 普通文件与坏块表合并两条
**真实功能路径**结果正确。所有期望值（rc=0/255/10、4096B、A/B 取块区间）都先在同机
对上游同一代码路径实测过（`~/tmp/uc2/z34-recoverdm/mb/` 三轮重复稳定），非推断。

**⑥ 实跑读数（数字与证据同源）**：`test.sh` 末行打印
`recoverdm 0.20 consumer test: 25/25 assertions PASSED`
（`archives/r/recoverdm/0.20/reports/conan-create.log:121`，W3 `conan create` 内的
test_package 真实执行；干跑同一读数 `~/tmp/uc2/z34-recoverdm/tp-dryrun/`）。
⇒ MANIFEST `assertion_count`、本包 `manifest.yaml test_results`、PR 正文三处均取 **25**。
调试中改的两处**测试脚本自身**问题（非包缺陷）：上游恢复日志的进度值以裸 CR 分隔
（`od -c` 实测尾部 `...4096\rDone\n`），故 `Done` 断言先 `tr '\r' '\n'` 再匹配。

## 本仓 conan 2.29.1 API 实测约束（写配方时踩到，逐条实测）

1. `conan.tools.files.copy()` **不接受 `keep_permissions` 关键字** ⇒ G2 在 `package()`
   抛 `TypeError: copy() got an unexpected keyword argument 'keep_permissions'`
   （首轮报错的 create 日志已被后续 W3 轮次覆盖，复现记录见 conanfile.py package() 内注释）。配方去掉该参数。
2. `conan.tools.build.can_run()` **必须传 conanfile** ⇒ test_package 裸调 `can_run()`
   抛 `TypeError: can_run() missing 1 required positional argument: 'conanfile'`。
   改为 `can_run(self)`。


## A/B/C 判定

- **路径 A**（普通基础适配）：零依赖、1486 行 C、裸 Makefile、无平台相关代码改动、0 补丁。
- **路径 B 判定 = `hit`**（2026-09-25 按 W4 审计复算改判；原判 `create` 的查全面漏了
  `knowledge/drafts/`，该面在仓内不被 `draft-review` 覆盖，须手工 grep）：本包双臂（P1/P2）的
  症状与修法**整体命中**仓内既有条目 `knowledge/drafts/DRAFT-ohos-makefile-explicit-toolchain-and-install-vars.{kv,md}`
  （skiplist 0.9.0 引入、基线提交 `5b5505ce6a`）⇒ **本 PR 不带新草稿、不占知识位、不建 Issue**；
  原成对草稿 `DRAFT-recoverdm-0.20-suckless-baked-paths-makevar-override.{kv,md}` 已由本提交从 PR 移除（两枚文件在 `origin/main` 上原本不存在
  ⇒ PR diff 中不再出现；备份在执行机 `~/tmp/uc2/z34-recoverdm/w4fix/removed-drafts/`）。
- **逐字段行号对齐表（判 `hit` 的依据；左=在池条目行号，右=本包实测）**：

| 字段 | 在池条目 | 在池原文要点 | 本包对应 | 裁定 |
|---|---|---|---|---|
| error_signature | `.kv:8` | `make: cc: No such file or directory`（并列 `install: No such file or directory`） | 臂 P1 首错逐字同签名：`armP1-make.log:2`、`:3`（附 `[<builtin>: recoverdm.o] Error 127`） | 同一层 |
| root_cause | `.kv:11`、`.md:5` | "Portable Makefiles often **default to** host command names such as cc" / "上游 Makefile **默认使用** `cc` 和 `install`" | Makefile 全文 29 行、`CC=` 赋值 0 处 ⇒ `$(CC)`（`:12`、`:15`）落 GNU make 内建默认 `cc`；`command -v cc` 两态无输出 | 同一层（"默认"已含"未赋值"情形，条目未主张必须有显式 `CC=cc` 行） |
| rec_approach | `.kv:15` | "read tools.build:compiler_executables, pass CC/CXX to make, and use Conan copy() for package layout" | `conanfile.py:97` 从 conf 取 c 编译器、`make -j1 CC=...`；`conanfile.py:106-113` 用 `copy()` 建立 `bin/` | 同一层 |
| rec_command | `.kv:17` | `make CC=<conf 的 c> test`（**命令行**覆写，非 env、非补丁） | 臂 P2 `make -j1 CC=clang` ⇒ `RC=0`、两枚产出（`armP2-make.log:333-334`） | 同一层 |
| verification_cmd | `.kv:13` | "test_package must link and execute a real API consumer" | `test_package/test.sh` 25 条消费者硬断言、runenv 内真实执行两枚包内二进制 | 同一层 |
| affected_scope | `.kv:12` | "C/C++ **libraries** built by Makefile ... minimal host utilities" | 本包是 CLI application（`package_type = "application"`） | 措辞差异，非新增机理，不升 create |
| 本包新现象一 | 条目无 | 覆写裸 `=` 赋值的 `CFLAGS` ⇒ **整体替换**打掉上游 `-DVERSION` ⇒ `recoverdm.c:22:23: error: ')'`（臂 P3） | 本包实测 | **不升 create**：同一 GNU make 语义已由同目录 `DRAFT-heatshrink-0.4.1-make-cflags-commandline-override.kv:19-21`（"命令行变量优先级高于 Makefile 内一切普通赋值……上游 CFLAGS 被**整体抑制**"）与 `:24-25`（适用面含"宏开关"）、`DRAFT-hoedown-3.0.7-makefile-cflags-override.kv:26-31`、`:44` 覆盖 |
| 本包新现象二 | 条目无 | `prescan_pattern`/`prescan_globs` 字段 | 本包草稿曾主张 | 字段缺失属**表单完备性**问题，不构成新机理；且条目 `.kv:9` `match_keywords` 已含 `CC=cc` 线索 |
| X11 烧死路径（池件 M18 第二层） | 条目未涉及 | `X11INC`/`X11LIB`/`FREETYPEINC` ⇒ 覆写聚合变量 `INCS`/`LIBS` | **本包不存在**（零第三方依赖、无 `-I/usr/...`）⇒ 无本包实测支撑 | 按"成套配送禁止空走"不主张 |

- 判重面（本次补齐，四范围）：① `knowledge/drafts/`（1469 份 `.kv` 全树正则 `make: cc: No such file`
  命中 4 个既有文件，其中 `DRAFT-ohos-makefile-explicit-toolchain-and-install-vars` 同签名同修法）；② `knowledge/graph/E*.kv`（542 份，同签名 0 命中）；
  ③ `knowledge/graph/index.tsv`（766 行，无同签名）；④ `draft-review` 实跑（上一轮 HEAD 下对本包草稿签名）
  TOP1 `E169` 相似度 **0.44** = 灰区 `review-similar`，次高 E217 0.37、E174 0.21。
- **路径 C** 不适用（无任何平台底层改动）。

### 3+2 声明

- **适配路径**：A（基础适配，零补丁）+ 路径 B 判定 `hit`
- **使用知识库**：本仓 `SKILL.md`（openharmony-compile-agent v12.22）+ 仓内既有条目
  `knowledge/drafts/DRAFT-ohos-makefile-explicit-toolchain-and-install-vars.{kv,md}`（复用其 `.kv:15`/`.kv:17` 的"从
  `tools.build:compiler_executables` 取 CC、在 make 命令行传入"修法与 `.kv:13` 的消费者验证口径；
  逐字段对齐行号见上表）+ B 草稿池件 M18（机制叙述同源，本包未据此占知识位）
- **知识库扩展**：无新增（判 `hit`）——本包症状与解法均被 `DRAFT-ohos-makefile-explicit-toolchain-and-install-vars` 覆盖，本 PR 提供的是该条目的
  **第二次独立复现**（recoverdm 0.20：裸 Makefile 无 `CC=` 赋值 ⇒ GNU make 内建 `cc` ⇒ `[<builtin>]` Error 127），
  故不占知识位、不随 PR 提交草稿
- **关联 Issue**：无（判 `hit` 不建 Issue；主窗先前登记的 #3358 不再对应本 PR 的知识条目，由主窗处置）

## 剩余风险

1. `recoverdm`/`mergebad` 的**核心价值面（真坏道介质恢复）在本环境不可证**，只能证普通
   文件路径与合并取块逻辑；审查员若要求介质级证据，需带 root 的 loop 设备环境（未覆盖面
   已在 MANIFEST 与本文写明，不假装覆盖）。
2. 上游 2004 年停更，源码存在 `-Wconversion` 类告警 34 条（上游无 `-Werror`）；未来工具链
   收紧可能变硬错误。
3. `read_mapfile()` 用 `while(!feof(fh)) fscanf(...)` 且循环内**不检查 fscanf 返回值**，
   会为每个 map 文件多追加一条未初始化项；实测（臂 F，3 轮稳定）该尾项 size=0 不影响取块，
   但这是上游缺陷，非适配引入 ⇒ 消费者测试的 map 文件按"边界值"写法给出（见上）。
4. Debian pool 作为分发源：`.orig.tar.gz` 是 pristine upstream（Debian 不改动），若审查要求
   作者官网直链，上游 `www.vanheusden.com` 无稳定 releases API，需人工定夺。

---

**适配开始**: 2026-09-25 02:05（B 机）
**门禁链**: preflight → build/verify（W3）→ finish → graph validate，判决原文见 `reports/`
---

**编译结束**: 2026-09-25 02:58
**最终状态**: built
