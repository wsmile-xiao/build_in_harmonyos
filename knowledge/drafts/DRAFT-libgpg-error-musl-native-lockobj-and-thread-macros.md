# DRAFT-libgpg-error-musl-native-lockobj-and-thread-macros — libgpg-error 在 musl 上：锁 ABI 尺寸须由 native 探针生成

> **Contributor**: ohpcd | **Status**: DRAFT | **Updated**: 2026-09-12
> **Severity**: 🟡 medium | **Category**: musl / ohos / threads / abi / autotools

## 相关既有条目（同族差异化定位）

| 既有条目 | 同族点 | 本 skill 的增量（差异化） |
|---------|--------|--------------------------|
| **`E321-draft-F987`**（已在 main）| 同批适配中**同时出现**的 gnulib 线程线索 | 该条主题为「gnulib weak-symbol 探测在 musl/OHOS 引用不存在的 `pthread_cancel`」，**已完整覆盖** `USE_POSIX_THREADS_WEAK` / `threadlib.m4` / `gl_cv_have_weak` 及其修法（patch `threadlib.m4` 强制 `gl_cv_have_weak=no`）。**本条不再重复该部分**，仅在其下「同批线索」一句指路 |
| **E404** / **`musl-glibc-developer-impact.md`** | 都提到 `aarch64-unknown-linux-musl` 这个 triplet | 两者**均不含 lock-obj 与 `--build==--host` 相关逻辑**（实测命中**各 0**），是不同主题。本条讲的是**锁 ABI 尺寸来源** |
| `umask 077`（49 命中）/ `TMPDIR 指向可写`（35）/ `dummy.c`（12）/ `unable to guess system type`（18）| 与本条同一次适配中出现 | 这些**已被既有条目覆盖** —— 本条仅作为**背景一句带过**，不重复其方案细节 |

> 查重（2026-09-12 复核更正）：`lock-obj` / `gen-posix-lock-obj` / `锁尺寸` 命中 **各 0**，确认为空白领域。
> ⚠️ **更正**：早期版本写「`USE_POSIX_THREADS_WEAK` / `threadlib.m4` 命中各 0」——该声明**有误**；实测二者在既有库中各有命中（`E321-draft-F987` 等），故本条**已删除**该线程宏章节，以避免与 E321 重复。

## Scope（何时用）

在 musl / OHOS 上构建 **libgpg-error**（或其下游 libgcrypt / gnupg / libassuan / libksba / pinentry）时。本条聚焦**一个**坑：

- **锁 ABI 尺寸选错来源** → **运行期**才暴露的锁行为异常（编译期无感）

> 同批适配中还会遇到 gnulib 线程宏误判（`USE_POSIX_THREADS_WEAK` → `pthread_cancel` 未声明，**编译期**报错）—— 见下方「同批线索」，该问题已由 `E321-draft-F987` 覆盖，本条不重复。

## 根因：锁 ABI 尺寸（lock-obj）必须由 native 探针生成

libgpg-error 把 pthread 锁的**尺寸**固化成平台相关头（`src/lock-obj-pub.*.h`，定义 `GPGRT_LOCK_T` / `_priv[N]`）。libgcrypt/gnupg 依赖它，**尺寸必须与目标 libc 的真实值一致**。

### configure 的判定逻辑（实测阅读 1.61 源码）

```
force_use_syscfg=no                       # 默认
· w32 系统                → force_use_syscfg=yes
· threads=no              → 直接生成
· cross_compiling=yes 时再看 host 与 OBJDUMP：
    host 匹配 gnu / linux-gnu / linux-musl / emscripten
      且 find 到 OBJDUMP  → 也生成（用 host objdump 读尺寸）
    否则（无 objdump，或 host 不匹配） → force_use_syscfg=yes
```

`force_use_syscfg=yes` 时，`src/Makefile.am` 用 `mkheader_opts = --cross` → **套用 `src/syscfg/` 里的预置头**。

### 致命点：`syscfg` 里没有 aarch64+musl 的预置头

```bash
$ ls src/syscfg/ | grep musl
lock-obj-pub.x86_64-unknown-linux-musl.h        # ← musl 只有 x86_64

$ ls src/syscfg/ | grep aarch64
lock-obj-pub.aarch64-apple-darwin.h
lock-obj-pub.aarch64-unknown-linux-androideabi.h
lock-obj-pub.aarch64-unknown-linux-gnu.h        # ← 会被拿来顶替！
lock-obj-pub.aarch64-unknown-linux-gnu_ilp32.h
```

### 实测尺寸差异（同一 aarch64 目标）

| 来源 | `_priv` | 文件大小 |
|------|---------|---------|
| **native 生成**（真实 musl）| **`_priv[40]`** | 622 B |
| syscfg 预置（**glibc**）| **`_priv[48]`** | 676 B |

```c
/* native（musl） */
typedef struct { long _vers; union { volatile char _priv[40]; ...
/* 预置（glibc） */
typedef struct { long _vers; union { volatile char _priv[48]; ...
```

→ 用 glibc 头顶替，**编译能过**，但下游 gnupg/libgcrypt 会在**运行期**因锁尺寸不匹配出现**难以排查**的故障（错在 ABI 尺寸，而非逻辑）。

### 对策：让构建走 native 路径

显式传 `--build=<triplet> --host=<同一 triplet>`：

```bash
--build=aarch64-unknown-linux-musl --host=aarch64-unknown-linux-musl
```

`build == host` → autoconf 不置 `cross_compiling` → 跳过 `force_use_syscfg` → 运行 `gen-posix-lock-obj` 探针生成 `lock-obj-pub.native.h`（按**本机真实 musl** 尺寸）。

**副作用（正面）**：该显式参数**同时**解决了 `config.guess` 在 HMDFS 上写探针失败的问题（既有条目已覆盖细节，此处不展开）。

> ⚠️ **不要**只依赖「有 objdump 就能 cross 生成」这条路径 —— 它要求 host triplet 匹配 **且** 工具可用，条件更多、更脆。

## 同批线索：gnulib 线程宏误判（已由 E321 覆盖，此处不重复）

同一次适配中，libgpg-error 的 `gl/`（内嵌 gnulib）在 musl 下会把 pthread 误判为「需外部 pthread」，定义 `USE_POSIX_THREADS_WEAK`，致 `pthread_cancel` 未声明而编译失败。

→ 该线索的**机制与修法**（patch `gl/m4/threadlib.m4` 强制 `gl_cv_have_weak=no`）**已由 `E321-draft-F987` 完整覆盖**，本条不再重复。

## 收尾自检

1. 确认 `lock-obj-pub.native.h` **存在**，且 `_priv` 尺寸与目标 libc 相符

## 记录口径（重要）

把「为何必须 `build == host`」写进配方注释 —— 否则后续维护者很容易**"顺手"改回 cross**，从而重新引入**运行期**才暴露的锁尺寸问题。

## 备选（fallback）

若确实无法 native 构建（必须 cross）且目标 libc 在 `src/syscfg/` 无预置头：自行提供**与该 libc 真实尺寸一致**的 `lock-obj-pub.<triplet>.h`（可在同架构同 libc 设备上用 `gen-lock-obj.sh` 生成一次后固化）。

> 风险：尺寸一旦抄错就变成**运行期**故障，故必须标注来源与生成方式，并在升级 libc 时复核。

## 禁止

- ❌ **"lock-obj 随便用预置头就行"/"尺寸应该一样"** —— 尺寸随 libc 实现变化（实测 musl 40 vs glibc 48），且 `syscfg` 里可能没有目标组合（aarch64+musl 实测 **0 个**）→ **运行期**锁异常，极难排查
- ❌ **「syscfg 里没有预置头」就直接拿任意 glibc 头改名顶上** —— 预置头的 `_priv[N]` 是按**该 libc 的真实尺寸**写死的，改名不改尺寸；编译可能通过，但下游运行期锁行为异常，且因"看起来已提供头文件"而更难怀疑到尺寸问题
- ❌ **"顺手"改回 cross** —— `build != host` 会重新触发 `force_use_syscfg`，让锁尺寸来源退回预置头，把「编译期可见」的问题退化为「运行期不可见」

## 实证

- **libgpg-error/1.61（PR #9612）**：
  - 阅读 `configure.ac` 的 `force_use_syscfg` 判定逻辑（w32 / threads=no / cross 且有 OBJDUMP 才生成，否则套用 syscfg）
  - 确认 `src/syscfg/` 下 **aarch64+musl 预置头不存在**（musl 仅 x86_64）
  - 实测 native 生成 `_priv[40]`（622 B） vs glibc 预置 `_priv[48]`（676 B）
  - 修法：`--build == --host`（native）→ **`conan create` EXIT=0**，test_package `dlopen` + `dlsym("gpg_strerror")` PASS
  - 同批出现的 gnulib 线程宏误判（`USE_POSIX_THREADS_WEAK`）→ 已由 `E321-draft-F987` 覆盖，本条不重复
