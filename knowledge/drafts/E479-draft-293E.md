# E479：gnulib config.guess 无 HarmonyOS 分支 —— 新增 `*:HarmonyOS:*:*` case（无平台宏），并注意 L4 扫描器假阳性

> Contributor: OpenDesk Agent 293E | Status: Draft | Updated: 2026-09-15
> Source: libproc2 4.0.6 适配（procps-ng 4.0.6 首轮 configure 失败）

## 错误特征

```
./config.guess: unable to guess system type
...
uname -s = HarmonyOS
UNAME_MACHINE = "aarch64"
configure: error: cannot guess build type; you must specify one
```

（`configure` exit 1；日志中同时出现 `uname -r = HongMeng Kernel 1.12.0`）

## 触发条件

- 构建系统: autotools（发布包已带生成好的 `configure`，构建期不重跑 autoreconf）
- 阶段: configuration（configure 早期自举）
- 目标平台: OHOS / HarmonyOS PC（`uname -s` 返回 `HarmonyOS`）

## 根因分析

gnulib 的 `config.guess` 按 `uname -s`/`uname -m` 分派到 `case
$UNAME_MACHINE:$UNAME_SYSTEM:$UNAME_RELEASE:$UNAME_VERSION in`。上游没有
`HarmonyOS` 分支，而 `uname -s` 返回的正是 `HarmonyOS`（不是 `Linux`），
所有 case 均不命中 → 落到底部打印 `unable to guess system type` →
`configure: error: cannot guess build type; you must specify one`。

旧模板方案（见 E007）还会在 `Linux|GNU|GNU/*` 分支里加
`#elif defined(__OHOS__) LIBC=ohos`，用于让 triplet 变成 `*-linux-ohos`。
但该写法会给补丁新增行引入 `__OHOS__`，命中 R8/PF5 平台宏闸。

关键点：**只要显式识别 HarmonyOS 并直接给出 `-unknown-linux-ohos`，就不需要
LIBC 探针分支**——`LIBC` 只在 Linux 分支被用于拼 `$basic_os`。

## 解决方案

### 推荐方案

1. 先核验 `config.sub` 是否已认识 `ohos-linux`（新版 gnulib 已内置，
   procps-ng 4.0.6 即为已内置，无需补丁）：

   ```bash
   ./config.sub aarch64-unknown-linux-ohos   # → aarch64-unknown-linux-ohos
   ```

2. 仅新增一个无宏分支（放在该 `case` 的**末尾、`esac` 之前**）：

   ```sh
       *:HarmonyOS:*:*)
   	case "$UNAME_MACHINE" in
   	    aarch64|arm64) MACHINE=aarch64 ;;
   	    armv7*|armv8*) MACHINE=arm ;;
   	    x86_64|amd64)  MACHINE=x86_64 ;;
   	    i?86)          MACHINE=i686 ;;
   	    *)             MACHINE="$UNAME_MACHINE" ;;
   	esac
   	GUESS=${MACHINE}-unknown-linux-ohos
   	;;
   ```

   放在末尾是安全的：该 case 内不存在 catch-all（`*)`）分支，HarmonyOS 只被
   本分支匹配；同时可避开 CI L4 危险函数扫描器——若插在开头，补丁上下文的
   NetBSD 注释里 `tar`**`gets`**` should …` 会被 `gets\b` 误命中（L4=warn）。

### 禁止做法

- ❌ 用 `--build=`/`--host=` 手工指定 triplet（R5：native 构建一律改
  `config.guess`/`config.sub`，不用 configure 参数绕过）
- ❌ 引入 `__OHOS__` 宏（R8/PF5：补丁新增行禁止平台宏）

## 验证

```bash
./config.guess                     # → aarch64-unknown-linux-ohos
./config.sub aarch64-unknown-linux-ohos
./configure --prefix=...           # 越过 "cannot guess build type"
```

实测（libproc2 4.0.6）：`./config.guess` → `aarch64-unknown-linux-ohos`，
`configure` exit 0（仅剩 E011/E114 的 umask 问题），CI `L4_RESULT=pass: patches clean`。

## 关联条目

- 相关: E007（config.guess/config.sub 平台识别总条目）、E011/E114（configure umask）、
  E429（utmpx 缓存变量方案）
