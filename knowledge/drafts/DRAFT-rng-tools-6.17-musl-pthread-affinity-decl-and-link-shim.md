# DRAFT-rng-tools-6.17-musl-pthread-affinity-decl-and-link-shim — OHOS musl 缺 `pthread_(attr_)setaffinity_np`，autotools 包在 configure 期就硬中止；用配方级"声明 + 符号"两层垫片非侵入过关（两层缺一即失败）

> **设备实测已闭环**（2026-09-23 四态分层对照 S1–S4）。`error_signature` /
> `verification_cmd` / `source_commit` 三处均为设备实跑的逐字读数。

## 一句话机制

上游 `configure.ac:117-121` 做的是**嵌套双探测 + 硬错误**：

```
AC_CHECK_DECL(pthread_attr_setaffinity_np, [定义 HAVE_PTHREAD_ATTR_SETAFFINITY],
  [ AC_CHECK_DECL(pthread_setaffinity_np, [定义 HAVE_PTHREAD_SETAFFINITY],
      [AC_MSG_ERROR([Neither pthread_setaffinity_np nor pthread_attr_setaffinity_np found])],
      [[#include <pthread.h>]]) ], [[#include <pthread.h>]])
```

这两个 `_np` 函数是 **glibc 扩展**，OHOS 的 musl 既**不声明**也**不导出符号** ⇒ 两轮都失败 ⇒
`AC_MSG_ERROR` 让包**连 configure 都过不去**（构建一行代码都没编译就止步）。

解法两层都在配方里，上游零改动：

1. **声明层**：`build()` 生成 `rngtools_np_affinity.h`（内含 `#define _GNU_SOURCE`、
   `#include <pthread.h>`/`<sched.h>`，**只声明 plain 变体**），经 `CPPFLAGS` 前置
   `-include <绝对路径>` 强制注入 ⇒ `AC_CHECK_DECL` 的**编译**探测转绿，
   `rng-tools-config.h` 落 `#define HAVE_PTHREAD_SETAFFINITY 1`（attr 变体保持 `#undef`）。
2. **符号层**：同目录生成 `rngtools_np_affinity.c`，实现**真转发**
   `sched_setaffinity(0, cpusetsize, mask)`，用 `tools.build:compiler_executables` 取到的
   `$CC` 编成 `.o`，再 `llvm-ar rcs librngnpcompat.a` 打成归档，经
   **`LDFLAGS=-L<该目录>` + `LIBS=-lrngnpcompat`** 进最终链接。
   ⚠ 把 `.o` 的绝对路径直接塞进 `LDFLAGS` 与 `-L 目录 + -l 名字` **语义不同**，只有后者能被
   configure 的 conftest 与生成的 Makefile 稳定解析。

**故意不声明 attr 变体**是本条最有复用价值的技巧——两层都声明会让 configure 走
`HAVE_PTHREAD_ATTR_SETAFFINITY` 分支，而那个分支需要的正是 musl 更不可能提供的另一个符号。

## 症状指纹（设备逐字）

未加垫片时（同一源码副本、同一依赖与参数，`../src/configure
--build=aarch64-unknown-linux-ohos --without-nistbeacon --without-qrypt
--without-pkcs11 --without-rtlsdr`）：

```
checking whether pthread_attr_setaffinity_np is declared... no
checking whether pthread_setaffinity_np is declared... no
configure: error: Neither pthread_setaffinity_np nor pthread_attr_setaffinity_np found
```

止步 configure（`rc=1`），`make` 一行未跑。

### 四态分层对照（2026-09-23 设备实跑，`~/tmp/uc2/主理-2-rng/no-shim/logs2/`）

| 态 | 注入 | configure | make | `rng-tools-config.h` |
|---|---|---|---|---|
| S1 全裸 | 无 | **rc=1**，第 67 行 `AC_MSG_ERROR` | 未跑 | 未产出 |
| S2 仅 `-D_GNU_SOURCE` | `CPPFLAGS=-D_GNU_SOURCE` | **rc=1**，同一行同一错 | 未跑 | 未产出 |
| S3 仅声明层 | `-include shim.h` | rc=0 | **rc=2**，首错 `ld.lld: error: undefined symbol: pthread_setaffinity_np` | `#undef HAVE_PTHREAD_ATTR_SETAFFINITY` + `#define HAVE_PTHREAD_SETAFFINITY 1` |
| S4 声明层 + 符号层 | 再加 `LDFLAGS=-L<compat>`、`LIBS=-lrngnpcompat` | rc=0 | **rc=0**，`rngd` + `rngtest` 双产物齐 | 同 S3 |

**S1 与 S2 的 configure 日志逐字节相同（sha256 一致、同为 3759 字节）** ⇒
`-D_GNU_SOURCE` 对本案两个 `_np` 接口**零效果**。它不是修复手段，且与上游 10 个 TU 自带的
`#define _GNU_SOURCE` 冲突刷一片 `-Wmacro-redefined` 告警。

S3 的 `undefined symbol` 引用点是 `rngd_jitter.c` 的 `thread_entropy_task`（`:290`）与
`rngd_notime_start`（`:86`）——**这正是"只补声明层"必然掉进去的失败面**，故符号层不可省。

使用点只有三处，都在**可选**的 CPU jitter 熵源里（不影响 rngd/rngtest 主干）：
`rngd_jitter.c:79`（`pthread_attr_setaffinity_np`）、`:86` 与 `:290`（`pthread_setaffinity_np`）。

## 适用范围与反例

- 适用：把 glibc-only `_np` 线程接口（亲和、线程名、barrier 等）写成 configure 硬错误的 autotools 包；
  指纹是"止步 configure + 报错点名两个函数名"。
- 不适用：musl 有符号只是没声明（补声明即可，别造符号）；探测是 `AC_CHECK_LIB`/软失败（本就有 fallback）；
  **绑核本身就是被测语义**的包（退化会让测试失去意义）。

## 必须申报的行为差异

实发方案是**真转发** `sched_setaffinity(0, …)`，不是 no-op（no-op 分支未采用；
"本平台是否有 `sched_setaffinity(2)`"的悬念已由 `nm` 与 S4 链接关闭）。但垫片**丢弃
`thread` 形参**，因此——

- `rngd_jitter.c:290` 传 `pthread_self()`，语义不变；
- `rngd_jitter.c:86` 在 `rngd_notime_start` 里传的是 `notime_thread_id`（**另一个线程**），
  那一处退化为给**调用线程**设亲和。因掩码是 `CPU_SET` 全核，只影响性能不影响正确性。

⇒ "rngd 仅对自身线程设亲和"这个说法对 `:86` **不成立**，PR「已知限制」必须写明，
不得只字不提当"完全等价"。

## 查重状态（本窗在设备 worktree 独立复核）

- `E211`（`pthread_get/setaffinity_np` undeclared）——**同符号但不同 phase、不同解法**
  （sed 改源码换成 `sched_*`），draft-review 实测相似度 **0.22**（2026-09-23 本窗复测）。
- `E094`（`pthread_attr_setaffinity_np` implicit declaration）——attr 变体 +
  `#ifdef __OHOS__` 源码补丁；其 `forbid_1` 恰是"声明了但 musl 无符号 ⇒ 链接炸"，
  **也就是本条 S3 实测复现的失败面**。本条是它的安全版（不补丁上游 + 补符号层）。
- `E147`（`cpu_set_t`/`CPU_*` undeclared）——**不适用**，sysroot `sched.h` 的类型与宏全在
  （探针未见缺类型症状）。
- `msquic` 草稿——依赖上游自带的反向守卫，本包无任何平台守卫，形态不同。
- 通用池 `DRAFT-ohos-musl-glibc-specific-symbols`——其 `forbid_2` 与本探针互证；
  其 rec 含"配方侧编译 compat TU"，是**最近先例但签名不同族**。
- 本地 `经验文档/B草稿库/` 22 条 grep `affinity/亲和` → **0 命中**。
- **判 hit 的四条件不支持 hit**：症状签名不重合——既有条目全部落在 compile/link 期，
  本包止步于 configure 硬错误。

**本窗复测读数**（）
——质量预检 `signature=✅ root_cause=✅ rec=✅`，相似正式条目 TOP3 为
**E211 0.22**（sig 0.27 / kw 0.06 / cat 0.4）、**E094 0.19**（sig 0.18 / kw 0.1 / cat 0.5）、
**E147 0.16**（sig 0.09 / kw 0.05 / cat 0.6），三项均低于灰区阈值 `_REVIEW_TH = 0.30`
（出处 `scripts/ohc/draft_review.py:30`）⇒ 三态建议 **create**（疑似新知）。
注：`draft-review` 不拦未回填的 TODO 占位，三个 ✅ 不等于可交付，落盘闸门另把。

## 房内先例

`archives/o/openssh/10.0p1/conanfile.py` 用同一形态解决 libc 缺符号：`build()` 里写出桩码
→ `$CC -c` → 把实现注进链接项，并在注释里写明「**不是补丁**（refresh-patch 处理不了
新增文件形态）」。本条与之的差别是**探测发生在 configure 期且是硬错误**，所以必须额外补
**声明层**（`-include`），只补符号层过不了 `AC_CHECK_DECL`；且链接项用 `-L 目录 + -l 名字`
而不是裸 `.o` 路径。
