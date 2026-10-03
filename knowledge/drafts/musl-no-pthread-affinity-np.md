# musl/OHOS 没有 `pthread_*_affinity_np` / `pthread_yield`，且 `cpu_set_t` 被 `_GNU_SOURCE` 圈住

> Draft: `DRAFT-MUSL-NO-PTHREAD-AFFINITY-NP`
> Stem: `musl-no-pthread-affinity-np` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-MUSL-NO-PTHREAD-AFFINITY-NP
- **严重度**: 1
- **类别**: portability|ohos-platform|libc
- **触发工具**: conan|clang|gcc|make|aclocal
- **阶段**: compilation

## 错误特征

绑定 CPU 的老代码在 OHOS 上会同时撞上两类报错：

```
src/rt-app.c:543: warning: call to undeclared function 'pthread_getaffinity_np';
                ISO C99 and later do not support implicit function declarations
src/rt-app.c:405: warning: call to undeclared function 'pthread_yield';
src/rt-app_types.h:145:2: error: unknown type name 'cpu_set_t'
                        cpu_set_t *cpuset;
```

第一类只是 **warning**（clang 默认不把隐式声明当错误），极易被忽略；第二类是硬错误。

## 根因

**一、GNU 扩展不存在。** OHOS 的 C 库是 musl 血统，sysroot 里根本没有这三个函数：

```bash
grep -rn "getaffinity_np\|setaffinity_np\|pthread_yield" $OHOS_SYSROOT/usr/include | wc -l
# -> 0
```

只有 POSIX 的 `sched_getaffinity` / `sched_setaffinity` / `sched_yield`。

**二、`cpu_set_t` 被 `_GNU_SOURCE` 圈住。** OHOS `sched.h` 的第 51–141 行是
`#ifdef _GNU_SOURCE` … `#endif`，`typedef struct cpu_set_t`（第 87 行）与
`CPU_ZERO/CPU_SET/CPU_ALLOC/CPU_ALLOC_SIZE/CPU_COUNT/CPU_EQUAL` 全在里面。
OHOS 的 `pthread.h` 只对 `struct cpu_set_t` 做**前置声明**，不提供 typedef。

因此"靠 `#include <pthread.h>` 顺带拿到 `cpu_set_t`"这个 glibc 传递包含习惯在 OHOS 上不成立，
而上游只有 `rt-app.c`、`rt-app_parse_config.c` 两个文件定义了 `_GNU_SOURCE`，
`rt-app_args.c`、`rt-app_utils.c` 因此报 `unknown type name 'cpu_set_t'`。

## 影响范围

- 任何用 `pthread_*_affinity_np` / `pthread_yield` / `cpu_set_t` 做 **CPU 绑核、亲和性管理、
  调度压测**的包（rt-app、schedutils 类、实时绑核压测工具）。
- 任何假定 `<pthread.h>` 会传递引入 `cpu_set_t` 的老代码。

## 推荐方案

**方法**: `replace-gnu-affinity-np-with-posix-sched-and-define-gnu-source-per-tu`

1. **换成 POSIX 同义函数**（语义完全一致，且在 glibc 上照样编过，不引入平台宏）：

   | glibc GNU 扩展 | POSIX 等价 | 说明 |
   |---|---|---|
   | `pthread_getaffinity_np(pthread_self(), sz, m)` | `sched_getaffinity(0, sz, m)` | Linux 上 `pid=0` 即"调用线程" |
   | `pthread_setaffinity_np(pthread_self(), sz, m)` | `sched_setaffinity(0, sz, m)` | 同上 |
   | `pthread_yield()` | `sched_yield()` | — |

   顺手把 `perror("pthread_get_affinity")` 之类字符串改成新函数名，避免误导排障。

2. **每个编译单元都要自己定义 `_GNU_SOURCE`**，且必须**在包含系统头之前**。
   只在公共头里加往往太晚——前面的 `<stdio.h>` 已经把 `features.h` 处理过了。
   正确做法是照上游既有写法，在缺 `_GNU_SOURCE` 的 `.c` 顶部加：

   ```c
   /* for cpu_set_t / CPU_* macros */
   #define _GNU_SOURCE
   ```

3. **补 `#include <sched.h>`**：确认用到 `cpu_set_t` 的头文件真的包含了 `<sched.h>`，
   musl 下没有从 `<pthread.h>` 出发的传递关系。

4. **验收要真跑一次绑核**，不能只验证能链接：调用 `sched_setaffinity(0, …, {CPU0})`
   之后读回并断言 `CPU_COUNT()==1 && CPU_ISSET(0,…)`，同时断言恢复原 mask 成功。
   这一条正好也构成"鸿蒙特有测试"。

## 验证命令

```bash
# 1) 确认这三个符号在 OHOS sysroot 中确实不存在
grep -rn "getaffinity_np\|setaffinity_np\|pthread_yield" \
     /mnt/c/Users/13909/ohos-sysroot/usr/include | wc -l        # -> 0

# 2) 确认 cpu_set_t 被 _GNU_SOURCE 守卫
sed -n '51,141p' "$OHOS_SYSROOT/usr/include/sched.h" | grep -n "cpu_set_t\|CPU_SET\|CPU_ALLOC"

# 3) 替换 + 每个 TU 定义 _GNU_SOURCE 后重建并实跑绑核
conan create . --name=rt-app --version=1.0 \
  -pr:h=ohos-aarch64-wsl -pr:b=ohos-aarch64-wsl --build=missing
```

实测（OHOS aarch64 / clang 15）：替换后
`sched_getaffinity` 返回 0、`CPU_COUNT` 得到 32、
`CPU_ALLOC`/`CPU_EQUAL`/`CPU_FREE` 与 `sched_yield` 全部编译、链接并运行通过。

## 取证记录

- 包: rt-app 1.0（`archives/r/rt-app/1.0`）
- 补丁: `patches/0002-enable-gnu-source-for-cpuset.patch`、
  `patches/0003-use-posix-sched-affinity-api.patch`
- 鸿蒙特有测试: `test_package/ohos_sched_test.c`（13 条断言全绿）
- 环境: OHOS aarch64，clang 15.0.4，profile `ohos-aarch64-wsl`