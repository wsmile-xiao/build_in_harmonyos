# DRAFT-inputlirc-34-hardcoded-usr-include-uapi-path — 内核 UAPI 头被写成绝对 `/usr/include`：参数化 + 问编译器反解 sysroot

> Contributor: 主理-32 / Status: **DRAFT** / Updated: 2026-09-25 / Severity: 2 (medium)
> Prospect ID: `DRAFT-inputlirc-34-hardcoded-usr-include-uapi-path-resolved-via-clang-M`（正式编号由主编 `graph promote` 分配）
> 来源实证：`archives/i/inputlirc/34`（HarmonyOS PC aarch64，B 机，HongMeng Kernel 1.12.0，clang 15 + OHOS SDK 26.0.0.18 sysroot）

## 一句话机制

上游把**内核 UAPI 头**写成 `/usr/include` 绝对路径，而且写在**两个层面**——
`Makefile` 的**前置条件**与源码的**尖括号绝对包含**；本机 `/usr/include` 整棵不存在（头在 SDK
sysroot，路径含 SDK 版本号）⇒ 配方引入可覆盖变量 `KERNELINC ?= /usr/include`，并用
`clang -M` **问编译器**要真实目录，**不写死 SDK 版本、不读裸 shell 的 `CC`**（R33）。

## 相关既有条目 / 同族前例（差异化定位，硬要求）

**引用口径**：`knowledge/drafts/` 里 **E 编号被复用**，故本条一律**按文件名**引用，不写 E 号。

| 前例（按名引用） | 它的机制层面 | 症状签名 | 与本文的差别 |
|---|---|---|---|
| `bridge-utils/1.5`（`archives/**/notes.md:13`） | 把 `<sysroot>/usr/include` 交给 configure 选项 `--with-linux-headers=` | configure 期"找不到内核头" | 有 configure 可传目录；本包**无 configure**，且路径同时是 **make 前置条件** |
| `bird/3.1.6:36-37`、`bird2:47` | `-I$SYSROOT/usr/include` 追加进 `CPPFLAGS` | 预处理 `file not found` | 只解决 include 搜索路径；`make` 的前置条件**不认 `CPPFLAGS`**，照旧断链 |
| `aliki/0.3.0:30`、`audtty/0.1.12:23` | 补丁**删掉**源码里硬编码的 `/usr/include` | 预处理 `file not found` | 只动源码一处；本包必须同时动 `Makefile` 的前置条件与生成器参数 |
| `DRAFT-ohos-musl-glibc-specific-symbols`（草稿） | musl 不提供 glibc 特有**符号** | `use of undeclared identifier` | libc 符号层，与"头的位置"无关（该草稿覆盖的是本包补丁 0003 的 `GLOB_NOMAGIC`） |
| `raul-2.0.0-af-unix-bind-blocked-meson-skip`（草稿） | AF_UNIX `bind()` 被平台策略拒 | 运行期 `EPERM` | 运行期能力墙，与本条编译期断链不同层 |

⇒ 判 `create` 的依据（手册/03 第 4 范围逐条读过）：**6 个同族前例都在"头目录可作为编译选项增删"
的层面，症状只有 `file not found`**；本条多一条 **`make: *** No rule to make target
'/usr/include/linux/input-event-codes.h', needed by 'names.h'`** 的前置条件断链，
解法是**参数化 + 编译器反解**，未被上述任何一条覆盖。同族前例 ≥6 包 ⇒ 跨库可复用，
不属"单库临时补丁"。

## Scope（何时用）

- 手写 `Makefile`、**没有** configure/pkg-config 的上游；
- 且 `/usr/include/...` 出现在 **make 依赖关系**里（前置条件 / 生成器参数），
  或源码里有 `#include </usr/include/...>` 这种**尖括号包绝对路径**；
- 构建机 `/usr/include` 不存在或内容不完整（OHOS PC 本机属前者）。

## Symptom（实测原文，未加工）

```console
make: *** No rule to make target '/usr/include/linux/input-event-codes.h', needed by 'names.h'.  Stop.
inputlircd.c:43:10: fatal error: '/usr/include/linux/input.h' file not found
```

两条**层级不同**：第一条是 make 图断裂（与 `CC`/`CFLAGS` 无关），第二条才是预处理找不到头。
只修第二条会仍然卡第一条——这是本条最容易踩的坑。

## Root Cause

HarmonyOS PC 本机 `/usr/include` 整棵不存在（`ls -d /usr/include` →
`No such file or directory`）。内核 UAPI 头实际在 SDK sysroot 内，且**路径含 SDK 版本号**：
`/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot/usr/include/linux/`。
clang 的默认搜索路径**已经**含它，所以相对尖括号包含是通的——缺的从来不是头，
是"头一定在 `/usr/include`"这个上游假设。

## Recommended Solution（三件套，同一 PR 内落地）

1. **`Makefile` 参数化**：`KERNELINC ?= /usr/include`，两处绝对路径改
   `$(KERNELINC)/linux/…`（**前置条件与生成器参数都要改**）。默认值保持 `/usr/include` ⇒
   在正常 Linux 上行为不变。
2. **源码去绝对路径**：`#include </usr/include/linux/input.h>` → `#include <linux/input.h>`。
3. **配方问编译器要目录**（核心增量）：

```python
save(self, stub, "#include <linux/input-event-codes.h>\n")
out = subprocess.run([self._cc, "-M", stub], capture_output=True,
                     text=True, cwd=self.build_folder).stdout
for tok in out.replace("\\\n", " ").split():      # 规整续行
    if tok.endswith(os.path.join("linux", "input-event-codes.h")):
        kernelinc = tok.split("/linux/")[0]
self.run("make -j1 all KERNELINC=%s" % kernelinc)
```

`self._cc` 取 `self.conf_info["tools.build:compiler_executables"]["c"]`（**R33**，
不读裸 shell `CC`）。反解在装有内核头的 Linux CI 上自然回到 `/usr/include` ⇒
**不需要任何平台分支、不需要 `#ifdef`（R8）**。

⚠ 两个必踩细节：
- `make install` 的前置条件同样指向 `$(KERNELINC)/linux/*.h` ⇒ **install 时要把 `KERNELINC` 再传一次**；
- 解析失败**不得**静默回落 `/usr/include`（回落方向正是本机制绕开的路径）。要么
  `os.path.isdir()` 判过再用，要么直接 `raise`，把失败暴露在 build 期而不是 make 期。

## 回退方案

`-M` 不可用（编译器不能被调用、输出被包装脚本污染）时，在 SDK sysroot 池里
`find */sysroot/usr/include/linux/input-event-codes.h` 取**唯一命中**；
0 命中或多命中即停下报环境错，不猜。

## 禁止做法

- ❌ 把 `ohos-sdk_26.0.0.18` 之类版本路径写死进配方 —— 换 SDK/换 CI 机即失效（R33）；
- ❌ `os.symlink` 造一个 `/usr/include` —— 要 root 且污染共享系统前缀（R49 三禁止）；
- ❌ 只往 `CPPFLAGS` 追加 `-I<sysroot>/usr/include` —— 治不了 **make 前置条件**那一处；
- ❌ 用 `-E` 的预处理输出去喂码表生成器 —— `#define` 全被消掉，生成物变空表，
  症状从编译错变成运行期"未知按键名"。

## 实测证据（inputlirc 34，2026-09-25，B 机）

| 项 | 结果 |
|---|---|
| `/usr/include` 是否存在 | **不存在**（`ls -d /usr/include` → No such file or directory） |
| 相对包含可否编译 | `printf '#include <linux/input.h>…' > htest.c; clang -c htest.c` → **RC=0** |
| `clang -M` 反解 | 依赖行给出 sysroot 内真实路径（含 `ohos-sdk_26.0.0.18` 版本号） |
| 修复后 | `make names.h KERNELINC=<sysroot>/usr/include` rc=0；`conan create` 通过，8 条产物断言全过 |
| 补丁形态 | `0001-uapi-headers-not-under-usr-include.patch`（`patch_type: portability`，无平台宏） |

**`reused-from-w4r1`**（下列读数是 W4 r1 审计独立复算，本条引用不重跑）：
补丁新增行平台宏命中 **0**；三枚补丁顺序应用 1→2→3 rc=0、逆序 `-R` 还原 rc=0、
`diff -r` 与未触碰解包全等；`names.h` 的 20 条 `-Winitializer-overrides` 是本机制打通后
才第一次可见（属上游自身缺陷，另记 notes §6）。
