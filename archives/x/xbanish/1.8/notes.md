# xbanish 1.8 适配笔记

## 编译环境
- 构建系统: makefile（上游单文件 `xbanish.c` + 手写 Makefile）
- 记录日期: 2026-09-23
- 编译器: clang（OHOS SDK，profile `ci/conan/profiles/ohos-aarch64`）
- 状态: built —— 草案轮如实记 draft（当时确未编译）；**构建验证轮已完成实编**：
  `conan-verify` G0–G4 全 PASS，`finish` 的 W3 本地 CI 模拟通过
  （`archives/x/xbanish/1.8/.ci-result.json` → `exit_code=0` / `step=W3_local_ci`）。
  逐档证据见文末「构建验证轮」。

## 语言与构建系统形态（R47 实测）

```bash
python3 scripts/ohc-run.py lang-preflight xbanish 1.8 \
  --src /storage/Users/currentUser/tmp/uc2/xbanish/src/xbanish-1.8 --lang c
```
输出 `✅ 语言匹配: task=c, detected=c — 继续适配主流程`，
`language_evidence = {build_system: make, manifest: 顶层 Makefile（无更强 manifest）,
source_stats: 源文件 1 个（c:1），主体占比 100%}`，milestone=lang_checked。
⇒ **未触发 env_unsupported，无语言冲突**，按正常 C/Makefile 路径继续。

## 上游形态（源码坐实，不采信备注）

上游 tag v1.8 归档共 6 个文件：`.gitignore LICENSE Makefile README.md xbanish.1 xbanish.c`
（`find . -type f` 全量列举，13717 字节 C 源 + 760 字节 Makefile）。

`xbanish.c` 的 include 与调用（grep 实测）：

| 项 | 证据 |
|---|---|
| `#include` | `err.h signal.h stdlib.h stdio.h string.h unistd.h`、`X11/X.h`、`X11/Xlib.h`、`X11/Intrinsic.h`、`X11/extensions/sync.h`、`X11/extensions/Xfixes.h`、`X11/extensions/XInput.h`、`X11/extensions/XInput2.h` |
| Makefile 链接行 | `LIBS += -lX11 -lXfixes -lXi -lXext`（**无 `-lXt`**） |
| Makefile 前缀 | `X11BASE ?= /usr/X11R6`，`INCLUDES ?= -I$(X11BASE)/include`，`LDPATH ?= -L$(X11BASE)/lib` |
| XFixes 调用 | `XFixesHideCursor`(L363)、`XFixesShowCursor`(L385) —— 共 2 处 |
| `XQueryPointer` | 1 处（L309） |
| 全部 X 调用（38 个去重符号） | libX11 / libXext(Sync) / libXi(XInput) 三家分担，见下表 |

⇒ 备注所称「依赖 X11 栈」实际低估：真依赖是 **libx11 + libxfixes + libxi + libxext**（外加协议头 xorgproto），
`libXi`（XInput2 热路径）与 `libXext`（XSync 超时告警）是硬链接依赖，不可裁剪。

## ★ X11 两条版本线与选型（本包核心适配点）

制品仓同时存在两条互斥的 X11 版本线（读归档 `requirements()` 坐实）：

| 配方 | 钉住的 libx11 |
|---|---|
| `libx11/6.4.0` 线：`libxfixes/6.1.0`、`libxi/6.1.0`、`libxi/1.8.3`、`libxext/6.4.0`、`libxext/6.4.0.1` | **libx11/6.4.0** |
| `libx11/1.8.13` 线：`libxfixes/6.0.1`、`libxfixes/6.0.2`、`libxt/1.3.1`、`libXext/1.3.7` | **libx11/1.8.13** |

冲突实测（`conan install --build=never -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=同一 profile`）：

```
conan install --requires=libxt/1.3.1 --requires=libxi/6.1.0 --build=never
RC=1
ERROR: Version conflict: Conflict between libx11/6.4.0 and libx11/1.8.13 in the graph.
Conflict originates from libxi/6.1.0
```

选型判定：**只能走 libx11/6.4.0 线**，因为 **`libXi` 两个归档版本（1.8.3 与 6.1.0）都钉 libx11/6.4.0**，
而 `-lXi` 是硬链接依赖 ⇒ 1.8.13 线根本无法满足 xbanish。

线 A 组图实测通过（本包依赖集，一次解出 9 个 OHOS 二进制）：
```
conan install --requires=libxi/6.1.0 --requires=libxfixes/6.1.0 \
              --requires=libxext/6.4.0 --requires=libx11/6.4.0 --build=never
GRAPH_A_RC=0
Downloading binary packages in 20 parallel threads
  libxau/1.0.11  libxcb/1.16  libxdmcp/1.1.5  xtrans/1.6.0  libx11/6.4.0
  libxext/6.4.0  libxfixes/6.1.0  libxi/6.1.0  xorgproto/2025.1   → 全部 Package installed
Install finished successfully
```

### 唯一障碍：`X11/Intrinsic.h`

线 A 无 `libXt`（引入它即回到冲突）。实测线 A 已装包的头文件覆盖情况：

```
X11/Xlib.h                  -> libx11/6.4.0        ✅
X11/X.h                     -> xorgproto/2025.1    ✅
X11/extensions/Xfixes.h     -> libxfixes/6.1.0     ✅
X11/extensions/XInput.h     -> libxi/6.1.0         ✅
X11/extensions/XInput2.h    -> libxi/6.1.0         ✅
X11/extensions/sync.h       -> libxext/6.4.0       ✅
X11/Intrinsic.h             -> find 全树 0 命中    ❌
```

且该 include 是**死 include**：
- `grep -c "XtApp\|XtInitialize\|XtToolkitError\|XtMalloc\|Widget" xbanish.c` → **0**
- 源文件引用的屏幕宏/函数 `XWidthOfScreen`、`XHeightOfScreen`、`DefaultScreenOfDisplay`
  在打包的 `X11/Xlib.h` 中 grep 命中数分别为 1 / 1 / 2 ⇒ 全部由 libX11 提供，不需要 Xt。

⇒ **补丁 0001 删除该行**（纯删除、无新增行，不含任何平台宏，R8/PF5 安全）。
删除后文件内 `grep -c "Intrinsic\|Xt[A-Z]"` → 0。

## 符号可得性复核（nm -D --defined-only，备注点名的 B 素材不是平台缺口）

| 库（线 A 实装 .so） | 符号 | 命中 |
|---|---|---|
| `libX11.so.6.4.0` | XQueryPointer / XWarpPointer / XQueryTree / XOpenDisplay / XSetErrorHandler / XNextEvent / **XGetEventData** / **XFreeEventData** / XDisplayOfScreen | 各 1 |
| `libXfixes.so.3.1.0` | XFixesHideCursor / XFixesShowCursor | 各 1 |
| `libXi.so.6.1.0` | XIQueryVersion / XISelectEvents / XOpenDevice / XCloseDevice / XListInputDevices / XSelectExtensionEvent | 各 1 |
| `libXi.so.6.1.0` | XGetEventData / XFreeEventData | 0 —— **属 libX11 符号**，已在 `libX11.so.6.4.0` 命中 1，非缺失 |
| `libXext.so.6.4.0` | XSyncInitialize / XSyncQueryExtension / XSyncListSystemCounters / XSyncCreateAlarm / XSyncDestroyAlarm / XSyncFreeSystemCounterList | 各 1 |

⇒ 备注点名的 `XFixes 光标隐藏` / `XQueryPointer` **均为平台已具备能力，不构成 OHOS 缺口**，
按路径 A 正常适配（B 判定交主理，本文只给事实）。
`<err.h>`（`warnx` / `errx` / `err`）由 OHOS sysroot 提供：
`/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot/usr/include/err.h` 存在。

## ★ 上游测试分母（R51 三步法第一步，四类口径逐个实测，全部 0）

大小写不敏感（`-i`）逐个宏/口径分别数，工作目录 = 解包后的 `src/xbanish-1.8/`：

| 口径 | 命令 | 结果 |
|---|---|---|
| `test*` 目录数 | `find . -iname "test*" -type d \| wc -l` | **0**（列目录也空） |
| 任何含 test 的文件/目录 | `find . -iname "*test*" \| wc -l` | **0** |
| gtest `TEST(` | `grep -ric "TEST(" .` 求和 | **0** |
| gtest `TEST_F(` | `grep -ric "TEST_F(" .` 求和 | **0** |
| gtest `TEST_P(` | `grep -ric "TEST_P(" .` 求和 | **0** |
| `ASSERT_*` | `grep -ric "ASSERT_" .` 求和 | **0** |
| `EXPECT_*` | `grep -ric "EXPECT_" .` 求和 | **0** |
| check/小c 断言 `tcase\|ck_assert\|assert(` | `grep -ric "tcase\|ck_assert\|assert(" .` 求和 | **0** |
| `res/` 语料条目 | `find . -type d -iname res \| wc -l`；`ls ./res ./tests/res ./test/res` | **0**（三者均 No such file） |
| `*RUNTEST*` 脚本 | `find . -iname "*runtest*" \| wc -l`；`grep -ric runtest .` | **0** / **0** |
| examples/demo 源文件 | `find . -type d \( -iname example* -o -iname demo* \) \| wc -l` | **0** |
| Makefile `test:` / `check:` 目标 | `grep -n "^test:\|^check:\|^[a-z]*test[a-z]*:" Makefile` | **RC=1 无命中**；`.PHONY: all install clean` 仅 3 目标 |

分母结论：**上游 0 测试**（N=0，N′=0），且这是"确无"而非"未找"——整棵源码树只有 6 个文件，
Makefile 只注册 `all`/`install`/`clean`，无任何测试目标可跑。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 与 `libxt/1.3.1` 同图必冲突 | libXi 只有钉 libx11/6.4.0 的版本，而 libXt 钉 1.8.13（版本线互斥） | 按"0 个 Xt 符号 + 宏全在 Xlib.h"证据删除死 include（补丁 0001），整包落线 A |
| 2 | 上游 Makefile 硬编码 `X11BASE=/usr/X11R6` | CI/设备无宿主 X11 开发树（R36） | 不跑上游 Makefile，按 clipnotify/1.0.2 先例直编 `xbanish.c`，include/lib 全部取自 conan 依赖包目录（R49：不注入共享前缀） |
| 4 | **补丁 0001 单独不充分：`error: use of undeclared identifier FALSE`（xbanish.c:532）** | `Intrinsic.h` 除 Xt 函数外还传递性提供了 `FALSE`/`TRUE` 两个 Xt 宏；全文 `grep -c "Xt[A-Z]"` 为 0（无 Xt 函数调用），但 `FALSE` 字面量有 1 处命中 —— 只查函数符号会漏掉宏，**必须实编才知道** | 补丁 0002 把 `== FALSE` 改为 Xlib 的 `== False`（两者都是 0，`X11/X.h` 已提供 `False`，且同文件另一处 X 返回值判断 L160 本就用小写 `True`，改后风格一致）；纯语义等价替换，无平台宏 |
| 3 | 设备无 X server，守护进程不可运行 | OHOS 无 X 服务 | 消费者测试断言确定性无 X 错误路径（`xbanish.c` L144-145 `errx(1, "can't open display %s", ...)`）+ ELF DT_NEEDED 记录四家 X 库 |

## 依赖版本

`libx11/6.4.0`、`libxfixes/6.1.0`、`libxi/6.1.0`、`libxext/6.4.0`、`xorgproto/2025.1`
（闭包经 W0 实测：`libxau/1.0.11`、`libxcb/1.16`、`libxdmcp/1.1.5`、`xtrans/1.6.0` 均"配方+OHOS 二进制"双全）

## 验证结果

```bash
# 本实际跑的（只读/下载探测，无任何编译）
bash ci/scripts/preflight_check.sh xbanish/1.8                 # RC=0（无 conanfile 阶段，正常）
bash ci/scripts/preflight_check.sh xbanish/1.8 --deps "libx11/6.4.0 libxfixes/6.1.0 \
  libxi/6.1.0 libxext/6.4.0 libxau/1.0.11 xorgproto/2025.1 xtrans/1.6.0 libxcb/1.16"
#   → 8 个依赖全 [OK] 已发布；[OK] 版本号未被占用: xbanish/1.8；TRUE_RC=0
python3 scripts/ohc-run.py recipe-search xbanish               # RC=0，无相似配方（语料 6173 条）
conan download zlib/1.3.1 -r=ohpcd --only-recipe               # POS_TRUE_RC=0（正对照）
conan download nonexistent-pkg-xyzzy/9.9.9 -r=ohpcd --only-recipe
#                                                              # NEG_TRUE_RC=1，文案 system acceleration policy not enabled
conan download xbanish/1.8 -r=ohpcd --only-recipe              # XBANISH_RC=1（全新包，与负对照同文案）
```

## 交付物

尚无产物（未编译）。构建后应产出 `bin/xbanish`、`share/man/man1/xbanish.1`、`licenses/LICENSE`。

## 注意事项

- **本包尚未编译**：W3（`conan create`）与 test_package 执行必须在拿到构建设备槽后进行；
  补丁 0001 的"可编译性"目前只有**头文件/符号级证据**，缺**实编证据**，不得当作已通过。
  **⇒ 2026-09-23 20:40 构建验证轮已覆盖本条**：见文末「构建验证轮」——实编探针暴露补丁 0001 不充分（`FALSE` 是 Xt 宏），已补补丁 0002，此后单 TU 实编 `CC_RC=0`。
- 消费者测试**不会**验证 xbanish 的实际隐藏光标行为（需 X server）；只能证明 ELF 可加载、
  四个 X 库链接正确、无 X 时走确定性错误路径。PR 正文与汇报须如实写明。
- 上游 `xbanish.c` 的 `hide_cursor()` 里 `XSyncCreateAlarm` 等仅在 `-t timeout` 路径使用，
  但 `-lXext` 是链接期硬需求，不可省。


---

# 构建验证轮（2026-09-23 20:30 起，本包首次实编）

> 本节之前全部内容属「草案轮」（静态与符号级取证，未实编）。
> 本节记录探针实测、补丁 0002 的由来，以及 W3 实况。

## 环境（本轮实跑的确切值）

| 项 | 值 |
|---|---|
| worktree | `/storage/Users/currentUser/qzy/主理-9-xbanish-1.8`（分支 `feat/xbanish-1.8`） |
| CONAN_HOME | `/storage/Users/currentUser/tmp/ch/home-主理-9-xbanish` |
| profile | `ci/conan/profiles/ohos-aarch64`（`-pr:h` 与 `-pr:b` 同值） |
| CC | `/data/service/hnp/bin/clang`（由 `conanbuild.sh` → `conanautotoolstoolchain.sh` 提供，本轮 echo 实测确认） |
| SSL_CERT_FILE | `/storage/Users/currentUser/usr/local/ssl/cert.pem` |
| OHC_RESULT_OUT | `/storage/Users/currentUser/tmp/uc2/xbanish/result.json` |

依赖图预检（非编译，`conan install <配方目录> --build=never`）：`PROBE_INSTALL_RC=0` +
`Install finished successfully`；`conan graph info --format=json` 亦 `GI_RC=0`，
host 侧解出 libx11/6.4.0 · xorgproto/2025.1 · xtrans/1.6.0 · libxcb/1.16 · libxau/1.0.11 ·
libxdmcp/1.1.5 · libxfixes/6.1.0 · libxext/6.4.0 · libxi/6.1.0（另有 `check/0.15.2` 为上游 X 包带来的传递项，非本包 requires）。
⇒ 配方自身可组图，W0 结论在「从 conanfile.py 解析」口径下再次复现。

## ⓓ 资源探针（最小构建）与结论

探针命令行 = **配方 `build()` 那条命令原样**，作用在打完两片补丁的单个 TU 上：

```
$CC -O2 -Wall <dep -I ...> probe/src/xbanish.c -o probe/xbanish_probe <dep -L ...> -lX11 -lXfixes -lXi -lXext
```

- 依赖 `-I/-L` 由 `$CONAN_HOME/p/*/p/{include,lib}` 枚举。
  **坑**：本机 conan 2.29 缓存布局是 `p/<名+hash>/p/`，**不是** `p/b/<...>/p/`；
  首次探针 glob 写成 `p/b/*/p` ⇒ 取到 0 个目录 ⇒ 假报 `fatal error: X11/X.h not found`。
  那是**探针的错，不是配方的错**，纠正后重跑（此坑值得记：探针失败先查探针自己）。
- `conanbuild.sh` 提供 `$CC`；配方命令行**不含 `$CFLAGS`**（`self.run` 只经 `env="conanbuild"` 取 CC），
  故探针同样不带 `-O3`，与真实构建逐字一致。

```
MEMCAP[probe] peak=83MB budget=0MB rc=0 用时1.4s
```

⇒ **`max_rss_mb: 83`**（已写入 `manifest.yaml` 与 `test_package/MANIFEST.yml`）。
预算档取 `--mb 1000`（对实测峰值 ~12x 余量，覆盖 conan 自身 python 与 test_package 阶段），
配 `--avail-factor 1.2 --slow`；外层仍套 `build-slot.sh` 取槽。
**ⓥ 口径照旧**：`--slow` 真正生效的是「并发降到 1 + 超预算硬止损」，慢速本身不省内存。

探针产物 ELF 自查（`/data/service/hnp/bin/readelf -d`）：

```
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)
NEEDED  libX11.so.6   libXfixes.so.3   libXi.so.6   libXext.so.6   libc.so
```

⇒ test_package 断言 2 的四项 X 依赖在**实编产物**里逐项坐实；libc 为 musl（`-lc` 隐式），
与 test_nox.sh 依赖的 `errx` 路径一致。

## 补丁 0002（本轮唯一配方级改动，由实编逼出）

草案轮 §8 的 `patch --dry-run` + `grep -c Intrinsic == 0` 只证明「补丁能打上、Xt 函数为 0」，
**没有证明能编译**。实编第一条真实错误：

```
probe/src/xbanish.c:532:61: error: use of undeclared identifier FALSE
        if (XQueryTree(dpy, win, &root, &parent, &kids, &nkids) == FALSE) {
1 error generated.
CC_RC=1
```

根因：`X11/Intrinsic.h` 除 Xt 函数外还**传递性提供 `FALSE`/`TRUE` 宏**（Xt 定义）。
本包全文 `grep -c "Xt[A-Z]"` = 0（无任何 Xt 函数），所以草案的符号级论证方向正确，
但**宏不在符号表里，grep 函数符号抓不到**。

取证：`grep -n "FALSE\|TRUE"` → 全文仅 532 行 1 处 `FALSE`、0 处 `TRUE`；
同文件 L160 另一处 X 返回值判断用的是 Xlib 小写 `!= True` ⇒ 上游本就混用，
532 行的 `FALSE` 纯粹靠 Intrinsic.h 侥幸编得过。

处置：补丁 0002 `== FALSE` → `== False`。
`False` 由 `X11/X.h` 提供且值为 0，与 Xt `FALSE` 值相同 ⇒ **纯语义等价替换、无平台宏、无新增依赖**，
R8/PF5 安全（实测 `__OHOS__` 0 命中）。改后 `grep -c FALSE` → 0，重跑探针 `CC_RC=0`。

⇒ 上游侧这是**真实可报的健壮性缺陷**（依赖 Xt 头的宏传递），已作为本包第二片 portability 补丁归档。

## 未执行与 SKIP 项口径

- 禁 `ohc-run.py build`（Step9 会把 `test_package/` 重刷成空壳造出假 G2）⇒ 走 `conan-verify` + `finish`。
- `finish` Step3 的 `G0: configure 失败 exit 127` 属 `clean_verify.py` 硬编码 `CONFIG_SHELL ./configure`
  对纯 Makefile 包入口不适用（经验库 12b:105）⇒ 只留证据，**不伪造 configure**。
- W4 独立审计不在本轮范围；`ohc-run.py review` 恒不全绿（基线 418 个 tracked E*-draft 撞 index.tsv）且不生成 `audit-result.json`。
- PF9 与 R38/PF8 对软件级 `commands.json` 互斥 ⇒ 按已合入先例 `archives/c/clipnotify/commands.json` 显式跳过并留判据，不为变绿挪进版本目录。
---

**编译结束**: 2026-09-23 21:04
**最终状态**: built


## conan-verify 与 W3 实况（逐轮实测证据）

### 队列 / 预算档位 / MEMCAP 末行

| 轮次 | 命令 | MEMCAP 末行（原文） | 结论 |
|---|---|---|---|
| ⓓ probe | 单 TU 直编（与配方 `build()` 同命令行） | `MEMCAP[probe] peak=83MB budget=0MB rc=0 用时1.4s` | 得 `max_rss_mb=83` |
| 预热 | `conan create`（官方 URL，非 harness） | `MEMCAP[run] peak=125MB budget=1000MB rc=0 用时5.8s` | WARM_RC=0 |
| verify#1 | `ohc-run.py conan-verify xbanish 1.8` | `MEMCAP[run] peak=88MB budget=1000MB rc=1 用时300.1s` | G2 FAIL（镜像超时） |
| verify#2 | 同上 | `MEMCAP[run] peak=61MB budget=1000MB rc=1 用时4.9s` | G2 FAIL（file:// 无适配器） |
| **verify#3** | 同上（根因已修） | `MEMCAP[run] peak=190MB budget=1000MB rc=0 用时15.9s` | **VERIFY_RC=0 全绿** |
| **finish** | `ohc-run.py finish xbanish 1.8 built` | `MEMCAP[run] peak=95MB budget=1000MB rc=1 用时181.2s` | **W3 通过**；FINISH_RC=2 源于 step5b/step8 |

- 档位：probe 83MB ⇒ 预算 `--mb 1000`（~12x 余量），配 `--avail-factor 1.2 --slow --interval 0.5`；
  外层 `build-slot.sh --wait 300 --mem 1200`（**小值、不拿 6000 死等**）。
  全程未出现 `rc=90`（超预算止损）/`rc=91`（可用内存拒启动）。
- 槽位实录：verify#3 `本机在用 2/2 → 排队 → SLOT_OK 21:01:18`；finish `1/2 → SLOT_OK 21:04:05`。

### G0–G4 逐档原文（verify#3；finish Step4 复现同一结果）

```
G1: 配方完整性检查...            G1: PASS
G0: 预构建风险评估 (知识图谱)...  G0: PASS
G2: conan create (干净构建)...    G2: PASS
G3: 系统同名库隔离验证 (R26)...   G3: PASS
G4: 产物完整性检查...             （含 L2 平台功能矩阵 / L4 静态安全扫描 / L5 产物基线对比）
✅ 配方验证通过: xbanish 1.8        result.json milestone=conan_verify_passed
```

### W3（阻塞门禁）判据与原文

`archives/x/xbanish/1.8/.ci-result.json`：`exit_code=0`、`step="W3_local_ci"`、
`integrity_hash=5ac5ff09577b0124`、`log_sha256=9dadc2737de101476f8f3efcbab804ec0a6841a275ada3a22c00f44ad5294663`。

`reports/w3-local-ci.log`（340 行）逐级原文：

```
L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed
L2_RESULT=skip: xbanish version/help failed
L4_RESULT=pass: patches clean
L5_RESULT=pass: bin/ has content
[ok] L1a: test_package was executed by conan create
[ok] L1b: Test execution evidence found in log
[ok] L1e: Negative test confirmed — test genuinely depends on xbanish   （[sabotage] bin/ moved away）
Total: 1  Success: 1  Failed: 0  Pass rate: 100.0% (1/1)
[step] All packages built and tested successfully
```

test_package 真实执行原文（同一日志）：

```
NEEDED OK: libX11/libXfixes/libXi/libXext all linked
xbanish exit rc=1
xbanish: can't open display
xbanish no-X error path OK (ELF runnable + X11 linkage resolved)
```

⇒ 运行时「隐藏光标」行为**未计入通过项**（平台无 X server），`L2` 按 `skip` 如实记账，
未从分母静默删除、未写成"测试通过"。

### G2 连败两次的阻塞根因（基础设施，非配方缺陷）

第一条真实错误（verify#1，`reports/conan-create.log`）：

```
Calling source() in .../p/xbanib4c88155d1378/s
WARN: network: Error downloading file https://ghfast.top/https://github.com/jcs/xbanish/archive/refs/tags/v1.8.tar.gz:
      (ConnectTimeoutError ... Connection to ghfast.top timed out. (connect timeout=30))
ERROR: Error in source() method, line 70
```

定位到 `scripts/ohc/conan_verify.py:571-576`：本地 harness 对**任何含 `github.com` 的
`conandata.yml` 无条件字符串替换**成 `ghfast.top/...`（无探活、无回退列表）。实测
`curl ghfast.top → HTTP=000`（镜像已死）、`curl 官方 → HTTP=302`（可达），
故**此刻所有 GitHub 源配方的本地 G2 都会红**，与本包无关。

conan 侧机理（`internal/rest/caching_file_downloader.py:56-66`）：本地下载缓存里
`<sha256>` 文件**已存在**时，还要比对 sidecar 记录的 URL 集合；注入后的镜像 URL 不在其中
⇒ `need_download=True` ⇒ 又去撞死镜像。第二次尝试改设 `core.sources:download_urls` 指向
`file://` 本地目录，被 conan 的 requests 下载器拒为 `No connection adapters were found for file://...`
⇒ 该路不通（并确认 `file://` 不能作 backup origin）。

**最终处置**（只动本任务自有的 `~/tmp/ch/dlcache`，不改仓、不改 harness）：
清掉被我 kill 掉的运行留下的 `.dirty` 标记，用**已核验 sha256 一致**的官方 tarball 复原
`s/e753d6a9…`，并把 sidecar `references` 记为「官方 URL + 镜像 URL」两条 ⇒
`recorded_urls.intersection(urls_set)` 命中 ⇒ conan 打印
`Source https://ghfast.top/… retrieved from local download cache`（create.log:122）
⇒ 全程不走网络、G2 转绿。tarball 内容由 `sha256` 强校验，与 conandata 官方值一致，**未放宽任何校验**。

### 提交态洁净度（镜像污染与恢复）

`build_and_test.sh` 的 EXIT trap 打印了「conandata.yml 已还原为官方 URL」，但它还原的是
**自己备份的、已被 mirror-fallback 改写过的那份** ⇒ 工作树里 `sources.url` 残留成
`gh-proxy.com` 镜像列表。已按规矩用 `git show HEAD:<path> > <path>` 恢复为官方单 URL
（**未用 `git checkout -- 路径`**），并复核：
**提交态洁净度复核（按可承载 URL 的文件逐个查）**：

```
git grep -n "file://|gh-proxy|ghfast" HEAD -- 1.8/conandata.yml 1.8/manifest.yaml                                             1.8/conanfile.py commands.json
→ RC=1（0 命中，干净）
git grep -n "github.com/jcs/xbanish" HEAD -- 1.8/conandata.yml → 官方 URL 在位
```

（注：`archives/x/xbanish` 整目录再 grep 会命中**本 notes.md 记事故的文字**，
那是叙述而非配方字段，不构成污染；判洁净须限定到承载 URL 的四个文件。）

### finish 的 FINISH_RC=2 归因（不影响 W3 判据）

- `step5b` 知识图谱完整性：基线 **1396 个草稿待审** + `E219/E253/E305.kv` 的 `root_cause` 为空
  —— 全仓基线噪声，非本包引入（`graph validate` 本身 ✅ 通过、doc↔kv 540 对完整）。
- `step8` `gen_summary 失败: str object has no attribute append` —— 框架内 bug，与包无关。
- `Step3 G0: 找不到原始 tarball`（`clean_verify` 独立入口，与 conan 的 dlcache 不同路径）：
  属**告警非阻塞**；conan-verify 的 G0 是 PASS 的。留证据，不伪造。
  与既有教训一致：`conan remove -c` 前须先验 dlcache，否则 finish 的 G0 找不到 tarball。
- `Step10 submit 就绪预检` 三项未就绪（`reports/test-report.md`、`packaging/`、`.staging-verified`）
  属**交付阶段**待办，本轮不建 PR/不提审，未擅自补造。
