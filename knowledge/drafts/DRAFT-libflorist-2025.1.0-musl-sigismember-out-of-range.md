# musl 的 sigismember() 越界返回 0，信号区间推导误判并产出非法 Ada

- **日期**: 2026-09-27
- **软件**: libflorist 2025.1.0（AdaCore/florist，HEAD `d28d09a6`）/ gcc-ada 9.5.0
- **门禁**: `conan create` → `build()` → 运行 `c-posix` / `c-posix-signals` 生成器
- **状态**: DRAFT（同 stem 配对 `DRAFT-libflorist-2025.1.0-musl-sigismember-out-of-range.kv`）

## 现象

构建期生成器在 OHOS 上产出非法 Ada 源码：

```
posix-implementation-ok_signals.ads:11:04: "Default_Is_Ignore" is undefined
posix-signals.adb:200:12: dynamic or empty choice in aggregate must be the only choice
posix-signals.adb:1148:12: choice given in case statement is not static
posix-signals.adb:1148:12: expression raises exception, cannot be static (RM 4.9(34))
```

根因是生成的规格里信号总数为负：

```ada
NSIGS : constant := -2;
...
OK : constant array (0 .. -2) of Boolean := (...)
```

## 根因

Florist 的两个生成器用同一套启发式推导信号区间（`c-posix.c` 与 `c-posix-signals.c` 的
`guess_nsigs` 同型）：

```c
#define BADSIG (-1)          /* 假定越界返回 -1 —— glibc 语义 */
sigfillset (&set);
for (sig = 0; sig < 1024; sig++) {
   result = sigismember (&set, sig);
   if (result == 1) last_good = sig;
   else if ((result == BADSIG) && (first_bad == -1)) first_bad = sig;
}
...
if (first_bad < last_good) {          /* 缺陷行 */
   last_good = first_bad - 1;
}
```

**musl 对越界信号返回 `0`（不是 `-1`）**，于是 `first_bad` 恒保持 `-1`，
末段守卫被误判为成立，把 `last_good` 从 64 压到 `-2`。

实测（本机 OHOS aarch64）：

```
$ ./ns2
_NSIG=65 NSIG=65 last_good=64 SIGRTMIN=35 SIGRTMAX=64
```

## 处置（已验证）

两处守卫各改一行，改为显式要求 `first_bad` 有效：

```c
- if (first_bad < last_good) {
+ if ((first_bad >= 0) && (first_bad < last_good)) {
     last_good = first_bad - 1;
  }
```

固化补丁：`archives/l/libflorist/2025.1.0/patches/0001-musl-signal-range.patch`

修复效果：

```
$ grep -n "NSIGS : constant" gensrc/posix-c.ads
291:   NSIGS : constant := 64;
```

`posix-signals.ads` 编译通过。

**要点**：不要判断"是不是 musl"再做分支——应修正启发式本身的前提错误。
`sigismember()` 的返回值只需区分「属于该集合(=1)」与「不属于(0 或 -1)」，
`first_bad` 只应在**确实观测到负数**时才参与收紧上界。该修复对 glibc 亦无副作用
（glibc 下 `first_bad` 本就 `>= 0`，行为不变）。用 POSIX 兼容写法，不引入平台宏
（符合 R8；PF5 平台宏闸无命中）。

## 验证命令

```sh
# ①最小复现
cat > ns.c <<'EOF'
#include <signal.h>
#include <stdio.h>
int main(void){ sigset_t s; int n=0,i; sigfillset(&s);
  for(i=0;i<1024;i++) if(sigismember(&s,i)==1) n=i;
  printf("_NSIG=%d last_good=%d\n", _NSIG, n); return 0; }
EOF
gcc -static -o ns ns.c && binary-sign-tool sign -inFile ns -outFile ns -selfSign 1 && ./ns
# OHOS: _NSIG=65 last_good=64

# ②库侧
grep -n 'NSIGS : constant' <build>/gensrc/posix-c.ads   # 缺陷态 -2，修复后 64

# ③源码侧
grep -n 'BADSIG\|first_bad' <源码>/c-posix*.c
```

## 禁止事项

| 禁止 | 原因 |
|---|---|
| 把生成的 `NSIGS` 或 `posix-implementation-ok_signals.ads` 手工改成合法值后继续构建 | 生成物会被下次构建覆盖（R6：禁止改生成文件），且掩盖生成器真实缺陷，下一台机器原样复现 |
| 在补丁里用 `#ifdef __OHOS__` 走特殊分支 | R8 明确补丁中默认禁止平台宏（PF5 fail-closed）；该差异属 glibc/musl 标准符合性差异，POSIX 兼容写法即可修复 |

## 相关条目

- `E534` —— musl 缺失 GNU/BSD 扩展（`sigisemptyset` 等）
- `E634-draft-62B2` —— 4.2BSD 信号接口 `sigvec`/`sigblock` 在 musl 缺失
- `knowledge/musl-glibc-full-comparison-iso-posix.md`

## 溯源

task libflorist 2025.1.0 适配（分支 `feat/libflorist-2025.1.0`），2026-09-27 真机实测；
修复前后 `NSIGS` 由 `-2` → `64` 为直接证据。
