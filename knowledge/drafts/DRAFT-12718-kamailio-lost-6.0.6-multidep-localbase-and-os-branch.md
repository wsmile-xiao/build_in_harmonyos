# DRAFT-12718-kamailio-lost-6.0.6-multidep-localbase-and-os-branch — 单值兜底变量 `$(LOCALBASE)` 在多依赖模块上结构性失配 + `$(OS)` 由 `uname` 推导致平台条件分支静默失效

> **Contributor**: Yukinoshitaqwq | **Status**: DRAFT | **Updated**: 2026-09-28
> **Severity**: 🔴 blocking | **Category**: build-system / cross-compile / ohos / toolchain / linking
> **Source**: 平台任务 12718 — `kamailio-lost` 6.0.6 适配 HarmonyOS PC（A 配方 + B 知识，同一 PR）
> **对应**: `knowledge/drafts/DRAFT-12718-kamailio-lost-6.0.6-multidep-localbase-and-os-branch.kv`
> **证据来源**: kamailio 6.0.6 官方源码包（源码级事实）+ HarmonyOS PC 真机（OHOS clang 15.0.4 / aarch64，Conan 2.29.1）

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本条目增量（差异化） |
|---|---|---|---|
| **E090** | 正式 | meson `host_machine`/`host_system` 把 HarmonyOS 判为非 linux → 平台判决失效（症状 `undefined symbol: _g_fd_is_journal`） | 同属「平台名未枚举 → 平台判决静默失效」，但载体是 **Makefile `$(OS) := $(shell uname -s …)`** 而非 meson 主机三元组；E090 不含「单值兜底变量承载多依赖」机制 |
| **E355** | 正式 | OHOS meson 适配三步法（harmonyos 平台映射 + `.pc` 的 `prefix=/` 修正 + boost 裁剪补全） | 同属「平台名映射 + 依赖前缀修正」；**没有**「单个变量承载 ≥2 个依赖包目录」这一结构性失配，也不涉及两阶段构建把 `OS/C_DEFS` 烘进 `config.mak` |
| **E468** | 正式 | `PkgConfigDeps` 写出 `.pc` 但没把 generators 目录加入 `PKG_CONFIG_PATH` | 与本条**回退方案**同向（把依赖元数据目录纳入探测搜索路径）；但对象是 Conan 生成物目录，本条对象是上游 Makefile 的兜底变量语义与 `$(OS)` 分支，且**主方案根本不经过 pkg-config**（实测依赖 `.pc` 不可用） |
| kamailio 同族先例 `tls`/`slack`/`snmpstats`/`debugger` 的 `manifest.yaml#knowledge_gained` | 已随各自 A PR 记载 | 分别写有「`make cfg` 是前置」「`X_BUILDER=` 置空 + `LOCALBASE=<单依赖包目录>`」「`OS=harmonyos` → 用 `extra_defs` 逐宏注入」 | 四个先例全是**单依赖**模块，所以 `LOCALBASE` 手法在它们身上恰好成立；本条给出「依赖数 ≥ 2 时该手法结构性不成立」的判据与正解，并说明逐宏注入属症状级修补（11 个宏里只有 1 个会硬失败，其余静默） |

> **查重（2026-09-28）**：`kamailio` / `loadmodule` / `sr_module` / `find_export` / `mod_init` / `Makefile.defs` / `LOCALBASE` 在 `knowledge/graph/E*.kv` + `knowledge/drafts/**` + `knowledge/doc/**` 全文检索命中 **0** —— 本主题此前无任何条目。
> ⚠️ 如主编认为本条应与上述任一近邻合并，**接受并入近邻、证据归并而本条不重复计分**；本条核心交付是「单值兜底变量在多依赖模块上的结构性失配」这一机制，以及它附带的两阶段烘焙陷阱。

## Scope（何时用）

**适用**
- kamailio 经典 Makefile 体系里**依赖数 ≥ 2** 的模块（lost / nghttp2 / rabbitmq / websocket / db_mysql …）；
- 更一般地：任何「用单一 `LOCALBASE` 类变量做多依赖兜底」+「用 `uname`/枚举表做平台探测」的经典 Makefile 工程。

**不适用（反例）**
- 单依赖模块（`kamailio-tls` / `slack` / `snmpstats`）——`LOCALBASE` 兜底仍然有效，不要据此改动它们；本条只约束「依赖数 ≥ 2」。
- kamailio 的 CMake 构建路径（`modules/lost/CMakeLists.txt` + `find_package`）不走这套探测/兜底逻辑。
- 依赖确实没装（`L0i`/R36 层面）——本条的前提是「依赖已发布、包目录确实存在」，此时才轮到兜底变量语义背锅。
- `ARCH=aarch64` 下 `use_fast_lock=yes` 会无条件加 `-DFAST_LOCK` 并置 `found_lock_method`，故 `core/lock_ops.h` 的 `no locking method selected` 在该平台**不会**触发——本条不覆盖该现象。

## 现象与稳定错误签名

给一个多依赖模块编 `.so` 时会连续出现互不相干的三类报错，且**没有一条指向上游真正的问题**：

| # | 报错（原文） | 暴露阶段 | 真实原因 |
|---|---|---|---|
| 1 | `No rule to make target 'cfg-defs'` | 配置 | 直接跑 `make modules` 而没先 `make cfg`（kamailio 是两阶段构建） |
| 2 | `core/resolve.h:290:2: error: neither gethostbyname2 or getipnodebyname present` | 编译 | `$(OS)=harmonyos` 不匹配任何 OS 分支 → 平台能力宏整体缺失 |
| 3 | `cannot find -lxml2` / `cannot find -lcurl`，或误命中宿主同库 | 链接 | 单个 `$(LOCALBASE)` 无法同时指向两个依赖包目录 |

```text
error_signature: neither gethostbyname2 or getipnodebyname present|cannot find -lxml2|cannot find -lcurl|undefined reference to .sctp_sendmsg|No rule to make target .cfg-defs.
```

触发实例：`kamailio 6.0.6` 的 `src/modules/lost`（LoST / HELD 协议）——该源码树里**首个同时依赖两个第三方原生库**的模块：PIDF/HELD XML 走 `libxml2`，出站 HTTP 走 `http_client` 模块 API（模块 Makefile 仍链接 `-lcurl`）。

## 根因与最小复现

两个机制都是**静默退化**：配置期不报警，错误在两三跳之后以「缺头文件 / 缺宏 / 缺 -l」的形式出现，极易被误判成「依赖没装好」。

### 机制一：单值兜底变量承载不了 N 个依赖

`src/modules/lost/Makefile` 上游原文（关键结构）：

```make
ifeq ($(CROSS_COMPILE),)          # ← 整段探测只在「非交叉编译」时才启用
XML2CFG=$(shell which xml2-config)
ifeq ($(XML2CFG),)
XML2CFG=$(shell if pkg-config --exists libxml-2.0; then echo 'pkg-config libxml-2.0'; fi)
endif
CURL_BUILDER=$(shell if pkg-config --exists libcurl; then echo 'pkg-config libcurl'; else which curl-config; fi)
endif

ifneq ($(XML2CFG),)
	DEFS += $(shell $(XML2CFG) --cflags )
	LIBS += $(shell $(XML2CFG) --libs)
else
	DEFS+=-I$(LOCALBASE)/include/libxml2 -I$(LOCALBASE)/include
	LIBS+=-L$(LOCALBASE)/lib -lxml2            # ← 兜底：指 $(LOCALBASE)
endif

ifneq ($(CURL_BUILDER),)
	DEFS += $(shell $(CURL_BUILDER) --cflags )
	LIBS += $(shell $(CURL_BUILDER) --libs)
else
	DEFS+=-I$(LOCALBASE)/include
	LIBS+=-L$(LOCALBASE)/lib -lcurl            # ← 兜底：同一个 $(LOCALBASE)
endif
```

三个可核查的事实叠在一起就构成结构性失配：

1. **交叉编译时上游自己就跳过探测**。两个探测变量的赋值整段包在 `ifeq ($(CROSS_COMPILE),)` 内；交叉编译时它们保持为空 ⇒ 两个 `ifneq` 都取 `else` ⇒ **两个依赖都只能走兜底分支**。
2. **两个兜底分支共用同一个 `$(LOCALBASE)`**（libxml2 段与 curl 段的 `else` 里都是 `-L$(LOCALBASE)/lib`）。
3. **`$(LOCALBASE)` 是单值标量**：`src/Makefile.defs` 里按 OS 各赋一个值（`:483/490/497/504` → `/usr/local`；`:511/518` → `/usr/pkg`；`:527` → `/usr/local`；`:529` → `/opt/local`；`:533` 最终 `?= /usr/local`）。

而 Conan 2 的天性正相反：**每个依赖一个独立包目录**，`libxml2` 与 `curl` 不共享前缀 ⇒「两个 `-lX` 共用一个前缀」在结构上不可满足。**这不是配置写错，而是该兜底变量只覆盖「恰好一个依赖」的模块。**

最小复现（真机，HarmonyOS PC）：

```sh
tar xzf kamailio-6.0.6_src.tar.gz && cd kamailio-6.0.6
make cfg include_modules=lost            # 故意不传 OS=linux
make modules modules=modules/lost -j1 OS=linux
# → core/resolve.h:290:2: error: neither gethostbyname2 or getipnodebyname present
```

### 机制二：`$(OS)` 由构建机 `uname -s` 推导

```make
# src/Makefile.defs:125
OS := $(shell uname -s | sed -e s/SunOS/solaris/ -e s/CYGWIN.*/cygwin/ | tr "[A-Z]" "[a-z]" | tr "/" "_")
```

- 设备 `uname -s` 返回 `HarmonyOS` → `OS=harmonyos`；
- kamailio 6.0.6 源码树里 `harmonyos` 出现 **0 次**，全树 20 处 `ifeq ($(OS), …)` 列举的只有 `linux / gnu_kfreebsd / freebsd / openbsd / netbsd / dragonfly / solaris / darwin`；
- 于是**所有 OS 判决为假**，三处后果同时发生：

| 失效点 | 位置 | 后果 |
|---|---|---|
| 平台能力宏集 | `Makefile.defs:1844-1849`（linux 分支） | `-DHAVE_GETHOSTBYNAME2` 等全缺 → `core/resolve.h:290` 直接 `#error` 硬失败 |
| 模块级条件链接 | 如 `sctp/Makefile` 的 `ifeq ($(OS), linux) LIBS+=-lsctp endif` | 标志被静默丢弃，问题推迟到链接期（`undefined reference to sctp_sendmsg`） |
| 安装目录布局 | `Makefile.defs:479` 段 | `doc_dir/man_dir/data_dir` 停在 `doc/...` 而非 `share/doc/...` |

真机实测的宏集差异（同一棵树、同一工具链，只改 `make cfg` 的 `OS` 值）：

```text
== delta（linux 相对 harmonyos 多出的宏，共 11 个）==
-DHAVE_ALLOCA_H  -DHAVE_GETHOSTBYNAME2  -DHAVE_IP_MREQN  -DHAVE_MSGHDR_MSG_CONTROL
-DHAVE_MSG_NOSIGNAL  -DHAVE_SCHED_SETSCHEDULER  -DHAVE_SCHED_YIELD  -DHAVE_SELECT
-DHAVE_TIMEGM  -DHAVE_UNION_SEMUN  -DUSE_RAW_SOCKS
== harmonyos 独有宏：无 ==
== LIBS 差异：无（两分支均为 -ldl -lresolv -lm）==
```

11 个宏里只有 `-DHAVE_GETHOSTBYNAME2` 会硬失败，其余是**静默**变化——这正是「按报错逐个补宏」必然漏项的原因。

### 两阶段构建把变量烘焙进 `config.mak`

`make cfg` 生成 `src/config.mak`，其中含 `OS=` 与 `C_DEFS=`（真机实测 `grep "^OS=" src/config.mak` → `OS= harmonyos`）；模块 Makefile 经 `src/Makefile.defs:41` 的 `include $(COREPATH)/config.mak` 读取它，而 `config.mak` 里是普通赋值，会盖掉 `Makefile.defs` 内的重新计算 ⇒ **只在 `make modules` 传 `OS=linux` 无效**。

## 已尝试方案与结果（受控实验：同树、同工具链、同依赖，只改变量）

| 组 | 变量设置 | 结果 |
|---|---|---|
| **A** | `LOCALBASE=<curl 包目录> XML2CFG= CURL_BUILDER=`（= 把 slack 先例手法直接推广到多依赖模块） | ❌ `pidf.c:58:10: fatal error: 'libxml/parser.h' file not found` —— `-I$(LOCALBASE)/include` 指进了 curl 包的 include，那里没有 libxml |
| **B1** | 逐依赖注入 `CPATH`/`LIBRARY_PATH`，`OS` 用默认值（`harmonyos`） | ❌ `core/resolve.h:290:2: error: neither gethostbyname2 or getipnodebyname present` |
| **B2** | `make cfg`（默认 `OS`）→ `make modules OS=linux` + 逐依赖注入 | ❌ 仍失败（`config.mak` 里烘焙的宏集未被覆盖） |
| **C** | `make cfg OS=linux` → `make modules OS=linux` + 逐依赖注入（两侧探测变量置空、`LOCALBASE` 指向不存在的目录） | ✅ 通过，产出 `lost.so`（715136 B） |
| 回退路线 | `PKG_CONFIG_PATH` 聚合两个依赖包的 `lib/pkgconfig` | ❌ 本任务不可用：`libcurl.pc` 带 `Requires.private: openssl,zlib` → `pkg-config libcurl --cflags` 直接 `rc=1`（`Package openssl was not found`）；`libxml-2.0.pc` 的 `prefix=/usr/local` 也需 `--define-variable=prefix=` 修正 |

A 组与 C 组的对比就是判别性证据：**「失配」出现在依赖维度（单值 vs 多值），「通过」出现在把两个维度都补齐之后**。

## 最终方案

1. **不沿用 `$(LOCALBASE)` 兜底**，改为逐依赖注入搜索路径：
   - 命令行把两侧探测变量显式置空（`XML2CFG= CURL_BUILDER=`）。这与上游自己的交叉编译语义一致（上游在 `CROSS_COMPILE` 非空时同样跳过探测），因此**不是「绕过系统检测」**，而是把不可靠的宿主探测换成显式的依赖注入；
   - `LOCALBASE` 指向一个**不存在的目录**，使兜底分支产生的 `-I/-L` 全部落空；
   - 用 `CPATH` / `LIBRARY_PATH` 按依赖逐个列出各自的 `include` / `lib` ⇒ 每个 `-lxml2` / `-lcurl` 只可能解析到自己那个包。
2. **平台条件一次性覆盖**：`make cfg` 与 `make modules` **两阶段都传 `OS=linux`**（两阶段同值）。OHOS 的编译器三元组本身就是 `aarch64-unknown-linux-ohos`、内核为 Linux，`__OS_linux` 分支用到的都是 Linux socket 选项，故该映射是语义正确的降级，而非绕过。

```sh
export CPATH=<libxml2>/include/libxml2:<libxml2>/include:<curl>/include
export LIBRARY_PATH=<libxml2>/lib:<curl>/lib
M="OS=linux LOCALBASE=$PWD/no-single-localbase-retired XML2CFG= CURL_BUILDER="
make cfg     include_modules=lost $M
make modules modules=modules/lost -j1 $M
```

**降级一**：`PKG_CONFIG_PATH` 目录聚合（仅当每个依赖的 `.pc` 自洽时可用，本任务实测不可用，原因见上表）。
**降级二**：造 `joint/{include,lib}` 联合前缀（符号链接分别指向两个依赖包），把单个 `$(LOCALBASE)` 指向它——不改上游、不用 `CPATH`，代价是每加一个依赖就要补链（**本任务未走该路线，未实测**）。

**禁止（均有实测支撑）**

| 禁止 | 原因 | 后果 |
|---|---|---|
| 单个 `LOCALBASE` 指向某一个依赖包目录 | 指望另一依赖靠系统路径命中 | 另一侧 `-lX` 链接期找不到或误命宿主同库（A 组实测：`'libxml/parser.h' file not found`） |
| 按报错逐个复刻 `-DHAVE_*` 宏 | 症状级修补（11 宏里仅 1 个硬失败） | 其他平台宏与**模块级** OS 条件仍缺失，每适配一个新模块重新试错 |
| 只在 `make modules` 传 `OS=linux` | `config.mak` 已把 `OS/C_DEFS` 烘死 | 与完全不传等价（B2 组实测），白跑一轮 |

## 适用范围、反例、解除条件

- **适用**：见 Scope 段。
- **反例**：见 Scope 段（单依赖模块 / CMake 路径 / 依赖未装 / `lock_ops.h` 不触发）。
- **解除条件**（上游或环境变更后本方案何时失效）：
  1. 上游把探测块移出 `ifeq ($(CROSS_COMPILE),)`，或把 `$(LOCALBASE)` 换成多值/列表语义（如 `LOCALBASES`）——机制一的触发面会变化；
  2. 上游 `Makefile.defs` 把 `harmonyos`/`ohos` 纳入 OS 枚举表，或改用 `uname -m`+`--target` 等更可靠探测——机制二消失；
  3. Conan 侧若改为「所有依赖共享一个前缀」（如 `cpp_info.set_property("cmake_..."` 之外的统一 install prefix），单值兜底会重新变得可用；
  4. 环境若开始提供自洽的 `libxml-2.0.pc`/`libcurl.pc`（后者不带 `Requires.private`），降级一即可替代主方案。

## 真实验证

- **平台**：HarmonyOS PC，OHOS clang 15.0.4（`aarch64-unknown-linux-ohos`），Conan 2.29.1（OHOS 适配版），profile `ohos-aarch64`（`os=OHOS os.version=6.0 arch=armv8 build_type=Release`）。
- **构建**：真机 `conan create` 两次独立运行，两层断言全绿：

```text
== 层 1 产物结构 ==  15 passed, 0 failed, 0 skipped
== 层 2 消费者 E2E == 45 passed, 0 failed, 0 skipped
== 合计 == 60 passed, 0 failed      → ALL CHECKS PASSED
```

（run#2 用 `--build=kamailio-lost/*` 强制重建包本体，日志见 `create5.log`：`Package 'fb3d1258…' built` / `Created package revision f548256b…`）

- **产物指纹**（`lib/kamailio/modules/lost.so`，打包在 `lib/kamailio/modules/`）：

```text
大小    : 715136 B（两次独立构建一致）
sha256  : b2869b304994d5514839406cf4f013be1f8a5249f7b47492f3d7fb7fea479270  （run#2）
sha256  : 3360fe9efc8e7d672fa3f57e3104e7305d229848c4c220694ca5b192a220b985  （run#1）
DT_NEEDED: libxml2.so.16, libcurl.so, libc.so
RPATH/RUNPATH: 无
⚠️ sha256 不可跨构建目录比对：lost.so 内含编译期源码绝对路径字符串（含 Conan build folder 编号），
   两次构建仅在这 86 字节上不同（cmp -l 实测），其余完全一致。本配方的 LOCALBASE=<不存在路径>
   未泄漏进产物（strings | grep -c no-single-localbase-retired 实测 0）。
```

- **上游测试真实执行**：官方源码包内唯一自包含、无需运行中 kamailio 实例与外部网络的上游测试 `utils/kamctl/dbtextdb/dbtextdb_test.py`（上游自带 unittest 入口，3 个用例）在构建阶段实跑通过；`lost` 模块自身源码目录内无测试源、无 `check`/`ctest` 目标注册（已在配方 `notes.md` 如实登记）。
- **消费者 E2E**（层 2，45 条）真跑了 `lost_held_dereference()` 的五条分支：`LocByVal=202`、`LocByRef=201`、非法根元素 `400`、HTTP `404→400`、空响应体 `400`，并断言 `Content-Type: application/held+xml;charset=utf-8`、`Accept` 含 `application/pidf+xml`、POST 正文 `locationRequest`（held 命名空间 + `responseTime="5"` + `>geodetic locationURI</locationType>`）与 pidf/err 两个 pv 的回写。
- **口径说明**：15（层 1 结构断言）/ 45（层 2 消费者断言）/ 3（上游用例）分别计数，**不相加冒充用例数**。

## 交付关联

- 适配 PR：`feat/kamailio-lost-6.0.6`（A 配方 + B 知识同一 PR）
- 任务：平台任务 12718（kamailio-lost / 6.0.6）
- 知识草稿：`knowledge/drafts/DRAFT-12718-kamailio-lost-6.0.6-multidep-localbase-and-os-branch.{kv,md}`
- 完整受控实验台账与 11 宏差异表：`archives/k/kamailio-lost/6.0.6/notes.md`

## 附：为什么「不重复」这个结论不是判重工具给的

`ohc draft-review` 的相似度只有四个通道：`error_signature` 字面量（权重 0.55）、`match_keywords` Jaccard（0.30）、`category`（0.10）、`phase`（0.05），**只做字面比字面**：

- 跨构建系统的**同一机制**（meson 平台映射 ↔ Makefile `$(OS)` 推导）在 `error_signature` 通道恒为 0，总分上限只有 0.45 —— 工具结构性地看不见这类「机制相同、字面不同」的重复；
- 反之，字面重合但根因不同（各类 `xxx.h file not found`）会被判成高分近邻，形成假重复。

所以本条的差异化定位由上面「相关既有条目」表逐条人工比对得出；工具分数（本次 `create`，top 近邻 0.12 / 0.12 / 0.09，位列全部 1484 份草稿 top-score 的第 25 百分位）只作粗筛参考。
